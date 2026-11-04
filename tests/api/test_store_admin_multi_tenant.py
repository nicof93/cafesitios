import unittest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from core.security_store_admin import (
    anti_brute_force,
    create_store_admin_token,
    decode_store_admin_token,
    get_current_store_admin,
    hash_store_password,
    verify_store_password,
    StoreAdminContext,
)
from db.database import (
    AuditoriaAccionesTienda,
    InteraccionClic,
    Base,
    NotaCata,
    Producto,
    ProductoNotaCata,
    Tienda,
    UsuarioTienda,
    Variante,
)
from api.admin_tienda import (
    create_store_product,
    list_store_products,
    list_store_audit_logs,
    store_admin_login,
    sync_own_store,
    update_store_product,
    StoreAdminLoginRequest,
    StoreProductInput,
    StoreProductVariantInput,
)


class DummyRequest:
    def __init__(self, headers=None, client_host="192.168.1.50"):
        self.headers = headers or {}
        self.client = type("Client", (), {"host": client_host})()


class TestStoreAdminMultiTenant(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        # Tienda A
        self.tienda_a = Tienda(
            nombre="Tostaduría A",
            url_base="https://tienda-a.cl",
            plataforma="woocommerce",
            activo=True,
        )
        # Tienda B
        self.tienda_b = Tienda(
            nombre="Tostaduría B",
            url_base="https://tienda-b.cl",
            plataforma="shopify",
            activo=True,
        )
        self.session.add_all([self.tienda_a, self.tienda_b])
        self.session.commit()

        # Usuario Admin Tienda A
        self.user_admin_a = UsuarioTienda(
            usuario_id="user-uuid-tienda-a",
            tienda_id=self.tienda_a.id,
            rol="STORE_ADMIN",
        )
        # Usuario Admin Tienda B
        self.user_admin_b = UsuarioTienda(
            usuario_id="user-uuid-tienda-b",
            tienda_id=self.tienda_b.id,
            rol="STORE_ADMIN",
        )
        self.session.add_all([self.user_admin_a, self.user_admin_b])
        self.session.commit()

        # Producto perteneciente a Tienda B
        self.prod_tienda_b = Producto(
            tienda_id=self.tienda_b.id,
            nombre="Café Secreto Tienda B",
            url_detalle="https://tienda-b.cl/producto/secreto",
            activo=True,
        )
        self.session.add(self.prod_tienda_b)
        self.session.commit()

        # Contexto de Store Admin para Tienda A
        self.ctx_a = StoreAdminContext(
            usuario_id=self.user_admin_a.usuario_id,
            tienda_id=self.tienda_a.id,
            rol=self.user_admin_a.rol,
            tienda=self.tienda_a,
            ip_origen="192.168.1.50",
        )

        # Contexto de Store Admin para Tienda B
        self.ctx_b = StoreAdminContext(
            usuario_id=self.user_admin_b.usuario_id,
            tienda_id=self.tienda_b.id,
            rol=self.user_admin_b.rol,
            tienda=self.tienda_b,
            ip_origen="192.168.1.51",
        )

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_jwt_token_generation_and_decoding(self):
        token = create_store_admin_token(
            usuario_id="test-user-123",
            tienda_id=42,
            rol="STORE_ADMIN",
            expires_in_seconds=3600,
        )
        payload = decode_store_admin_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], "test-user-123")
        self.assertEqual(payload["tienda_id"], 42)
        self.assertEqual(payload["rol"], "STORE_ADMIN")

    def test_multi_tenant_isolation_update_forbidden(self):
        # Admin de Tienda A intenta modificar el producto de Tienda B -> DEBE fallar con 403 Forbidden
        payload_update = StoreProductInput(
            nombre="Hackeo de Nombre",
            activo=True,
            oculto_catalogo=False,
        )

        with self.assertRaises(HTTPException) as cm:
            update_store_product(
                product_id=self.prod_tienda_b.id,
                payload=payload_update,
                ctx=self.ctx_a,  # Admin de Tienda A
                db_session=self.session,
            )
        self.assertEqual(cm.exception.status_code, 403)
        self.assertIn("Acceso denegado: este producto pertenece a otra tostaduría", cm.exception.detail)

    def test_multi_tenant_product_creation_and_scoping(self):
        # Admin de Tienda A crea un producto
        new_prod_payload = StoreProductInput(
            nombre="Café Catuai Lavado 250g",
            descripcion="Café aromático de prueba",
            origen="Costa Rica",
            variantes=[
                StoreProductVariantInput(
                    opcion="250g",
                    formato_gramos=250,
                    precio_clp=8990,
                )
            ],
        )

        created = create_store_product(
            payload=new_prod_payload,
            ctx=self.ctx_a,
            db_session=self.session,
        )
        self.assertEqual(created.tienda_id, self.tienda_a.id)
        self.assertEqual(created.nombre, "Café Catuai Lavado 250g")

        # Verificar auditoría
        audit_entry = self.session.query(AuditoriaAccionesTienda).filter(
            AuditoriaAccionesTienda.accion == "CREAR_PRODUCTO",
            AuditoriaAccionesTienda.tienda_id == self.tienda_a.id,
        ).first()
        self.assertIsNotNone(audit_entry)
        self.assertEqual(audit_entry.usuario_id, self.ctx_a.usuario_id)

        # Admin de Tienda A lista productos: solo ve su producto
        prods_a = list_store_products(ctx=self.ctx_a, db_session=self.session)
        self.assertEqual(prods_a.total, 1)
        self.assertEqual(prods_a.productos[0].id, created.id)

        # Admin de Tienda B lista productos: no ve el producto de Tienda A
        prods_b = list_store_products(ctx=self.ctx_b, db_session=self.session)
        self.assertEqual(prods_b.total, 1)
        self.assertEqual(prods_b.productos[0].id, self.prod_tienda_b.id)

    def test_anti_brute_force_lockout_after_5_failures(self):
        test_ip = "10.0.0.99"
        test_email = "malicious@attacker.com"

        # Simular 4 intentos fallidos
        for _ in range(4):
            req = DummyRequest(client_host=test_ip)
            with self.assertRaises(HTTPException) as cm:
                store_admin_login(
                    payload=StoreAdminLoginRequest(email=test_email, password="wrong"),
                    request=req,
                    db_session=self.session,
                )
            self.assertEqual(cm.exception.status_code, 401)

        # Quinto intento fallido activa el bloqueo
        req = DummyRequest(client_host=test_ip)
        with self.assertRaises(HTTPException) as cm:
            store_admin_login(
                payload=StoreAdminLoginRequest(email=test_email, password="wrong"),
                request=req,
                db_session=self.session,
            )
        self.assertEqual(cm.exception.status_code, 401)

        # Sexto intento: DEBE retornar HTTP 429 Too Many Requests
        with self.assertRaises(HTTPException) as cm:
            store_admin_login(
                payload=StoreAdminLoginRequest(email=test_email, password="wrong"),
                request=req,
                db_session=self.session,
            )
        self.assertEqual(cm.exception.status_code, 429)
        self.assertIn("Cuenta bloqueada temporalmente", cm.exception.detail)

    def test_sync_own_store_with_cooldown(self):
        mock_sync_result = {
            "tienda_id": self.tienda_a.id,
            "nombre": self.tienda_a.nombre,
            "exito": True,
            "total_productos": 10,
            "productos_nuevos": 2,
            "productos_actualizados": 8,
            "duracion_segundos": 1.1,
            "error": None,
        }

        # Primera sincronización debe ser exitosa (200 OK)
        with patch("api.admin_tienda.sincronizar_tienda", return_value=mock_sync_result):
            res = sync_own_store(ctx=self.ctx_a, db_session=self.session)
            self.assertTrue(res.exito)
            self.assertEqual(res.tienda_id, self.tienda_a.id)
            self.assertEqual(res.productos_nuevos, 2)

        # Segunda sincronización inmediata: DEBE ser bloqueada por Cooldown de 30 min (HTTP 429)
        with self.assertRaises(HTTPException) as cm:
            sync_own_store(ctx=self.ctx_a, db_session=self.session)
        self.assertEqual(cm.exception.status_code, 429)
        self.assertIn("período de enfriamiento (cooldown)", cm.exception.detail)

        # Comprobar que quedó registrado en auditoría
        audit = list_store_audit_logs(ctx=self.ctx_a, db_session=self.session)
        sync_audits = [a for a in audit.registros if a.accion == "INICIAR_SYNC"]
        self.assertTrue(len(sync_audits) >= 1)
        self.assertEqual(sync_audits[0].tienda_id, self.tienda_a.id)

    def test_password_hashing_and_verification(self):
        pw = "SuperClaveSecreta123!"
        hashed = hash_store_password(pw)
        self.assertTrue(hashed.startswith("pbkdf2:sha256:100000$"))
        self.assertTrue(verify_store_password(pw, hashed))
        self.assertFalse(verify_store_password("clave_errada", hashed))
        self.assertFalse(verify_store_password(pw, None))

    def test_login_with_password_hash_and_flag(self):
        # Asignar password hasheado al usuario de Tienda A con debe_cambiar_password=True
        self.user_admin_a.password_hash = hash_store_password("ClaveTemporal2026")
        self.user_admin_a.debe_cambiar_password = True
        self.session.commit()

        req = DummyRequest(client_host="192.168.1.100")

        # 1. Login con password incorrecto -> 401
        with self.assertRaises(HTTPException) as cm:
            store_admin_login(
                payload=StoreAdminLoginRequest(email=self.user_admin_a.usuario_id, password="password_malo"),
                request=req,
                db_session=self.session,
            )
        self.assertEqual(cm.exception.status_code, 401)

        # 2. Login con password correcto -> 200 y debe_cambiar_password=True
        login_resp = store_admin_login(
            payload=StoreAdminLoginRequest(email=self.user_admin_a.usuario_id, password="ClaveTemporal2026"),
            request=req,
            db_session=self.session,
        )
        self.assertTrue(login_resp.debe_cambiar_password)
        self.assertEqual(login_resp.tienda_id, self.tienda_a.id)
        self.assertEqual(login_resp.usuario_id, self.user_admin_a.usuario_id)


    def test_platform_superadmin_impersonation(self):
        from core.security_store_admin import get_current_store_admin
        from fastapi.security import HTTPAuthorizationCredentials
        from api.admin_tienda import get_store_profile, list_store_products
        from api.admin import impersonate_store_admin_endpoint

        # 1. Generar token de suplantación usando el endpoint de administración
        resp = impersonate_store_admin_endpoint(store_id=self.tienda_b.id, db_session=self.session)
        self.assertTrue(resp.success)
        self.assertEqual(resp.tienda_id, self.tienda_b.id)
        self.assertEqual(resp.tienda_nombre, self.tienda_b.nombre)
        self.assertIn("impersonate_token=", resp.redirect_url)
        self.assertIn(f"tienda_id={self.tienda_b.id}", resp.redirect_url)

        # 2. Verificar que una tienda inexistente retorne 404
        with self.assertRaises(HTTPException) as cm_404:
            impersonate_store_admin_endpoint(store_id=99999, db_session=self.session)
        self.assertEqual(cm_404.exception.status_code, 404)

        # 3. Validar resolución de contexto con el token de suplantación
        req = DummyRequest(client_host="127.0.0.1")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=resp.token)
        superadmin_ctx = get_current_store_admin(
            request=req,
            credentials=creds,
            db_session=self.session,
        )
        self.assertEqual(superadmin_ctx.tienda_id, self.tienda_b.id)
        self.assertEqual(superadmin_ctx.rol, "PLATFORM_SUPERADMIN")
        self.assertIn("superadmin@cafesitios.cl", superadmin_ctx.usuario_id)

        # 4. Probar que el contexto de superadmin puede consultar perfil y productos de Tienda B
        profile = get_store_profile(ctx=superadmin_ctx, db_session=self.session)
        self.assertEqual(profile.tienda_id, self.tienda_b.id)
        self.assertEqual(profile.tienda_nombre, "Tostaduría B")

        products_resp = list_store_products(
            page=1,
            per_page=10,
            q=None,
            oculto=None,
            ctx=superadmin_ctx,
            db_session=self.session,
        )
        self.assertEqual(products_resp.total, 1)
        self.assertEqual(products_resp.productos[0].nombre, "Café Secreto Tienda B")


    def test_store_profile_update(self):
        from api.admin_tienda import update_store_profile, StoreProfileUpdateRequest

        payload = StoreProfileUpdateRequest(
            direccion="Av. Providencia 1234",
            comuna="Providencia",
            telefono_whatsapp="+56912345678",
            logo_url="https://tienda-a.cl/logo.png",
        )
        updated_prof = update_store_profile(payload=payload, ctx=self.ctx_a, db_session=self.session)
        self.assertEqual(updated_prof.tienda_id, self.tienda_a.id)
        self.assertEqual(self.tienda_a.comuna, "Providencia")
        self.assertEqual(self.tienda_a.telefono_whatsapp, "+56912345678")

        # Verificar registro en auditoría
        audits = self.session.query(AuditoriaAccionesTienda).filter_by(accion="UPDATE_PERFIL").all()
        self.assertTrue(len(audits) >= 1)
        self.assertEqual(audits[-1].tienda_id, self.tienda_a.id)

    def test_store_catalogs_crud_and_isolation(self):
        from api.admin_tienda import (
            create_store_catalog,
            list_store_catalogs,
            delete_store_catalog,
            StoreCatalogCreateRequest,
        )

        # 1. Tienda A crea catálogo
        cat_req = StoreCatalogCreateRequest(url_catalogo="https://tienda-a.cl/cafe-especialidad", etiqueta="Línea Filtros")
        created = create_store_catalog(payload=cat_req, ctx=self.ctx_a, db_session=self.session)
        self.assertEqual(created.tienda_id, self.tienda_a.id)
        self.assertEqual(created.url_catalogo, "https://tienda-a.cl/cafe-especialidad")

        # 2. Tienda A lista catálogos
        cats = list_store_catalogs(ctx=self.ctx_a, db_session=self.session)
        self.assertEqual(len(cats), 1)
        self.assertEqual(cats[0].id, created.id)

        # 3. Tienda B lista catálogos (debe estar vacío para Tienda B)
        cats_b = list_store_catalogs(ctx=self.ctx_b, db_session=self.session)
        self.assertEqual(len(cats_b), 0)

        # 4. Tienda B intenta borrar catálogo de Tienda A -> 404
        with self.assertRaises(HTTPException) as cm_del:
            delete_store_catalog(catalogo_id=created.id, ctx=self.ctx_b, db_session=self.session)
        self.assertEqual(cm_del.exception.status_code, 404)

        # 5. Tienda A borra su catálogo -> 200
        del_resp = delete_store_catalog(catalogo_id=created.id, ctx=self.ctx_a, db_session=self.session)
        self.assertTrue(del_resp["exito"])

    def test_store_branches_crud_and_isolation(self):
        from api.admin_tienda import (
            create_store_branch,
            list_store_branches,
            update_store_branch,
            delete_store_branch,
            StoreBranchCreateUpdateRequest,
        )

        # 1. Tienda A crea sucursal
        b_req = StoreBranchCreateUpdateRequest(nombre="Cafetería Central", direccion="Merced 345", comuna="Santiago")
        created_b = create_store_branch(payload=b_req, ctx=self.ctx_a, db_session=self.session)
        self.assertEqual(created_b.tienda_id, self.tienda_a.id)
        self.assertEqual(created_b.comuna, "Santiago")

        # 2. Tienda A lista sucursales
        branches = list_store_branches(ctx=self.ctx_a, db_session=self.session)
        self.assertEqual(len(branches), 1)

        # 3. Tienda A actualiza sucursal
        up_req = StoreBranchCreateUpdateRequest(nombre="Cafetería Central Renombrada", comuna="Santiago Centro")
        updated_b = update_store_branch(sucursal_id=created_b.id, payload=up_req, ctx=self.ctx_a, db_session=self.session)
        self.assertEqual(updated_b.nombre, "Cafetería Central Renombrada")

        # 4. Tienda B intenta borrar sucursal de Tienda A -> 404
        with self.assertRaises(HTTPException) as cm_del_b:
            delete_store_branch(sucursal_id=created_b.id, ctx=self.ctx_b, db_session=self.session)
        self.assertEqual(cm_del_b.exception.status_code, 404)

        # 5. Tienda A borra su sucursal -> 200
        del_b_resp = delete_store_branch(sucursal_id=created_b.id, ctx=self.ctx_a, db_session=self.session)
        self.assertTrue(del_b_resp["exito"])


    def test_store_telemetry_summary(self):
        from api.admin_tienda import get_store_telemetry_summary

        # Simular interacciones de telemetría para Tienda B
        clic = InteraccionClic(
            producto_id=self.prod_tienda_b.id,
            tipo_evento="click_outbound_store",
            ip_hash="fakehash123",
        )
        fav = InteraccionClic(
            producto_id=self.prod_tienda_b.id,
            tipo_evento="favorite_add",
            ip_hash="fakehash123",
        )
        self.session.add_all([clic, fav])
        self.session.commit()

        telem = get_store_telemetry_summary(ctx=self.ctx_b, db_session=self.session)
        self.assertEqual(telem.tienda_id, self.tienda_b.id)
        self.assertEqual(telem.clics_salientes_totales, 1)
        self.assertEqual(telem.total_favoritos_guardados, 1)
        self.assertEqual(len(telem.top_cafes), 1)
        self.assertEqual(telem.top_cafes[0].nombre, self.prod_tienda_b.nombre)

    def test_store_profile_shipping_and_roast(self):
        from api.admin_tienda import update_store_profile, get_store_profile, StoreProfileUpdateRequest

        up_req = StoreProfileUpdateRequest(
            envio_gratis_monto=25000,
            retiro_en_tienda=True,
            dias_tueste="Lunes y Jueves",
            fecha_ultimo_tueste="2026-10-18",
        )
        profile = update_store_profile(payload=up_req, ctx=self.ctx_a, db_session=self.session)
        self.assertEqual(profile.envio_gratis_monto, 25000)
        self.assertTrue(profile.retiro_en_tienda)
        self.assertEqual(profile.dias_tueste, "Lunes y Jueves")
        self.assertEqual(profile.fecha_ultimo_tueste, "2026-10-18")

        # Verificar persistencia en GET
        fetched = get_store_profile(ctx=self.ctx_a, db_session=self.session)
        self.assertEqual(fetched.envio_gratis_monto, 25000)
        self.assertTrue(fetched.retiro_en_tienda)

    def test_store_inconsistencies_inbox(self):
        from api.admin_tienda import get_store_product_inconsistencies

        # Crear un producto inconsistente en Tienda A: precio 0 y sin imagen
        bad_prod = Producto(
            tienda_id=self.tienda_a.id,
            nombre="Café Raro Sin Imagen",
            url_detalle="https://tienda-a.com/raro",
            imagen=None,
            categoria="cafe",
            activo=True,
        )
        self.session.add(bad_prod)
        self.session.flush()

        bad_var = Variante(
            producto_id=bad_prod.id,
            id_variante_externo="bad-v1",
            opcion="250g",
            formato_gramos=0,
            precio_clp=0,
            precio_original_clp=0,
            precio_por_kilo=0.0,
            disponible=True,
        )
        self.session.add(bad_var)
        self.session.commit()

        inc_resp = get_store_product_inconsistencies(ctx=self.ctx_a, db_session=self.session)
        self.assertGreaterEqual(inc_resp.total_inconsistencias, 1)
        tipos = [i.tipo_inconsistencia for i in inc_resp.inconsistencias]
        self.assertIn("SIN_IMAGEN", tipos)
        self.assertIn("PRECIO_INVALIDO", tipos)

    def test_store_benchmark_and_demand(self):
        from api.admin_tienda import get_store_price_benchmark, get_store_unmet_demand

        prod_a = Producto(
            tienda_id=self.tienda_a.id,
            nombre="Café Colombia Tienda A",
            url_detalle="https://tienda-a.cl/colombia",
            pais_origen="Colombia",
            categoria="cafe",
            activo=True,
        )
        self.session.add(prod_a)
        self.session.flush()

        var_a = Variante(
            producto_id=prod_a.id,
            id_variante_externo="prod-a-v1",
            opcion="250g",
            formato_gramos=250,
            precio_clp=10000,
            precio_original_clp=10000,
            precio_por_kilo=40000.0,
            disponible=True,
        )
        self.session.add(var_a)
        self.session.commit()

        benchmark = get_store_price_benchmark(ctx=self.ctx_a, db_session=self.session)
        self.assertGreater(benchmark.precio_kilo_promedio_tienda, 0.0)
        self.assertGreater(benchmark.precio_kilo_promedio_mercado, 0.0)
        self.assertIn(benchmark.posicion_mercado, ["Muy Económico", "Competitivo", "Estándar de Mercado", "Segmento Premium"])

        demand = get_store_unmet_demand(ctx=self.ctx_a, db_session=self.session)
        self.assertIsInstance(demand.origenes_mas_buscados, list)
        self.assertIsInstance(demand.oportunidades_catalogo, list)


    def test_store_notes_moderation(self):
        from api.admin_tienda import (
            add_store_product_note,
            confirm_store_product_note,
            discard_store_product_note,
            get_store_product_notes,
            StoreNoteActionRequest,
            StoreNoteCreateRequest,
        )

        prod_a = Producto(
            tienda_id=self.tienda_a.id,
            nombre="Café Especial Tienda A",
            url_detalle="https://tienda-a.cl/producto/especial",
            activo=True,
        )
        self.session.add(prod_a)
        self.session.commit()

        # 1. Tienda A agrega manualmente una nota a su producto
        create_req = StoreNoteCreateRequest(nombre="Chancaca")
        add_resp = add_store_product_note(
            producto_id=prod_a.id,
            payload=create_req,
            ctx=self.ctx_a,
            db_session=self.session,
        )
        self.assertTrue(add_resp["exito"])
        nota_id = add_resp["nota_id"]
        self.assertEqual(add_resp["estado"], "confirmada")

        # 2. Listar notas del producto
        notes_resp = get_store_product_notes(
            producto_id=prod_a.id,
            ctx=self.ctx_a,
            db_session=self.session,
        )
        self.assertEqual(notes_resp.total_notas, 1)
        self.assertEqual(notes_resp.notas[0].nombre, "Chancaca")
        self.assertEqual(notes_resp.notas[0].estado, "confirmada")

        # 3. Crear una nota sugerida y confirmarla
        nota_sug = NotaCata(clave_normalizada="ciruela-pasa", nombre="Ciruela pasa")
        self.session.add(nota_sug)
        self.session.flush()
        rel_sug = ProductoNotaCata(
            producto_id=prod_a.id,
            nota_id=nota_sug.id,
            texto_origen="Con notas a ciruela pasa",
            confianza=0.75,
            version_extractor="test",
            estado="sugerida",
            es_fuera_de_rueda=False,
        )
        self.session.add(rel_sug)
        self.session.commit()

        # Confirmar nota sugerida
        conf_resp = confirm_store_product_note(
            producto_id=prod_a.id,
            payload=StoreNoteActionRequest(nota_id=nota_sug.id),
            ctx=self.ctx_a,
            db_session=self.session,
        )
        self.assertTrue(conf_resp["exito"])
        self.assertEqual(conf_resp["estado"], "confirmada")

        # 4. Descartar la primera nota
        disc_resp = discard_store_product_note(
            producto_id=prod_a.id,
            payload=StoreNoteActionRequest(nota_id=nota_id),
            ctx=self.ctx_a,
            db_session=self.session,
        )
        self.assertTrue(disc_resp["exito"])
        self.assertEqual(disc_resp["estado"], "descartada")

        # 5. Aislamiento Multi-Tenant: Tienda B no puede gestionar notas de Tienda A
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx_err:
            get_store_product_notes(
                producto_id=prod_a.id,
                ctx=self.ctx_b,
                db_session=self.session,
            )
        self.assertEqual(ctx_err.exception.status_code, 404)



    def test_login_and_access_inactive_scraping_store(self):
        """Verifica que una tienda con activo=False pueda autenticarse y consultar su perfil."""
        from api.admin_tienda import store_admin_login, get_store_profile, StoreAdminLoginRequest
        from core.security_store_admin import hash_store_password

        # Crear tienda inactiva en scraping
        tienda_inactiva = Tienda(
            nombre="Tostaduría Onboarding",
            url_base="https://onboarding-coffee.cl",
            plataforma="manual",
            activo=False,
            limite_almacenamiento_mb=250,
        )
        self.session.add(tienda_inactiva)
        self.session.flush()

        user_inactivo = UsuarioTienda(
            usuario_id="onboarding@tostaduria.cl",
            tienda_id=tienda_inactiva.id,
            rol="STORE_ADMIN",
            password_hash=hash_store_password("PasswordSeguro123!"),
        )
        self.session.add(user_inactivo)
        self.session.commit()

        # Login exitoso a pesar de estar inactiva en scraping
        req = DummyRequest()
        login_resp = store_admin_login(
            payload=StoreAdminLoginRequest(
                email="onboarding@tostaduria.cl",
                password="PasswordSeguro123!",
                turnstile_token="turnstile_bypass_test",
            ),
            request=req,
            db_session=self.session,
        )
        self.assertTrue(login_resp.token)
        self.assertFalse(login_resp.scraping_activo)

        # Contexto de tienda inactiva
        ctx_inactivo = StoreAdminContext(
            usuario_id=user_inactivo.usuario_id,
            tienda_id=tienda_inactiva.id,
            rol=user_inactivo.rol,
            tienda=tienda_inactiva,
            ip_origen="127.0.0.1",
        )
        perfil = get_store_profile(ctx=ctx_inactivo, db_session=self.session)
        self.assertEqual(perfil.tienda_nombre, "Tostaduría Onboarding")
        self.assertFalse(perfil.scraping_activo)
        self.assertEqual(perfil.limite_almacenamiento_mb, 250)

    def test_update_recipe(self):
        """Verifica la creación y posterior modificación de una receta (PUT /recetas/{id})."""
        from api.admin_tienda import create_store_recipe, update_store_recipe, StoreRecipeInput

        prod = Producto(
            tienda_id=self.tienda_a.id,
            nombre="Caturra Lavado A",
            url_detalle="https://tienda-a.cl/caturra",
            activo=True,
        )
        self.session.add(prod)
        self.session.commit()

        req = DummyRequest()
        # Crear receta inicial
        nueva_rec = create_store_recipe(
            payload=StoreRecipeInput(
                producto_id=prod.id,
                nombre_receta="V60 Inicial",
                metodo="V60",
                dosis_cafe_g=15.0,
                agua_ml=250.0,
                ratio="1:16.7",
                pasos=["Paso 1"],
            ),
            request=req,
            ctx=self.ctx_a,
            db_session=self.session,
        )
        self.assertEqual(nueva_rec.nombre_receta, "V60 Inicial")

        # Modificar receta
        rec_modificada = update_store_recipe(
            receta_id=nueva_rec.id,
            payload=StoreRecipeInput(
                producto_id=prod.id,
                nombre_receta="V60 Modificado Pro",
                metodo="V60",
                dosis_cafe_g=16.0,
                agua_ml=240.0,
                ratio="1:15",
                molino_usado="Comandante C40",
                grosor_molienda="24 clicks",
                temperatura_c=93,
                pasos=["Paso 1: Pre-infusión", "Paso 2: Vertido continuo"],
            ),
            request=req,
            ctx=self.ctx_a,
            db_session=self.session,
        )
        self.assertEqual(rec_modificada.nombre_receta, "V60 Modificado Pro")
        self.assertEqual(rec_modificada.dosis_cafe_g, 16.0)
        self.assertEqual(rec_modificada.molino_usado, "Comandante C40")
        self.assertEqual(len(rec_modificada.pasos), 2)

    def test_recipe_rejected_when_zero_products_or_invalid_product(self):
        """Verifica que no se permita crear receta sin asociar un café existente en la tienda."""
        from api.admin_tienda import create_store_recipe, StoreRecipeInput
        from fastapi import HTTPException

        req = DummyRequest()
        with self.assertRaises(HTTPException) as ctx_err:
            create_store_recipe(
                payload=StoreRecipeInput(
                    producto_id=999999,  # Producto inexistente
                    nombre_receta="Receta Huérfana",
                    metodo="Chemex",
                    dosis_cafe_g=20.0,
                    agua_ml=300.0,
                ),
                request=req,
                ctx=self.ctx_a,
                db_session=self.session,
            )
        self.assertEqual(ctx_err.exception.status_code, 400)
        self.assertIn("Debes seleccionar un café", ctx_err.exception.detail)

    def test_product_creation_syncs_tasting_notes(self):
        """Verifica que notas de cata pasadas en notas_cata se sincronicen en ProductoNotaCata."""
        from api.admin_tienda import create_store_product, StoreProductInput

        req = DummyRequest()
        prod_output = create_store_product(
            payload=StoreProductInput(
                nombre="Geisha Finca Vista Hermosa",
                notas_cata=["Jazmín", "Miel", "Mora silvestre"],
                activo=True,
            ),
            ctx=self.ctx_a,
            db_session=self.session,
        )
        self.assertTrue(prod_output.es_manual)
        self.assertEqual(len(prod_output.notas_cata), 3)

        # Verificar en base de datos la relación relacional
        from sqlalchemy import select
        notas_rel = self.session.scalars(
            select(ProductoNotaCata).where(ProductoNotaCata.producto_id == prod_output.id)
        ).all()
        self.assertEqual(len(notas_rel), 3)
        for r in notas_rel:
            self.assertEqual(r.estado, "confirmada")

    def test_manual_product_image_upload_and_security(self):
        """Verifica la subida de imagen en base64 para productos manuales y validación de cuota/tipo."""
        from api.admin_tienda import (
            upload_store_product_image,
            StoreProductImageUploadRequest,
            create_store_product,
            StoreProductInput,
        )
        from fastapi import HTTPException
        import base64

        req = DummyRequest()
        prod = create_store_product(
            payload=StoreProductInput(nombre="Café Con Imagen"),
            ctx=self.ctx_a,
            db_session=self.session,
        )

        # 1. Imagen PNG válida (1x1 transparente)
        png_1x1_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        upload_resp = upload_store_product_image(
            producto_id=prod.id,
            payload=StoreProductImageUploadRequest(imagen_base64=png_1x1_b64),
            ctx=self.ctx_a,
            db_session=self.session,
        )
        self.assertTrue(upload_resp.exito)
        self.assertTrue(upload_resp.imagen_url.startswith("/static/uploads/productos/"))

        # 2. Rechazo de formato inválido (texto simulado)
        invalid_b64 = base64.b64encode(b"Este no es un archivo de imagen").decode("utf-8")
        with self.assertRaises(HTTPException) as ctx_err:
            upload_store_product_image(
                producto_id=prod.id,
                payload=StoreProductImageUploadRequest(imagen_base64=invalid_b64),
                ctx=self.ctx_a,
                db_session=self.session,
            )
        self.assertEqual(ctx_err.exception.status_code, 400)
        self.assertIn("Formato de imagen no soportado", ctx_err.exception.detail)

    def test_update_product_preserves_uploaded_image_when_none_sent(self):
        """Verifica que al actualizar un producto sin especificar imagen, no se borre la foto subida previamente."""
        from api.admin_tienda import (
            upload_store_product_image,
            StoreProductImageUploadRequest,
            create_store_product,
            update_store_product,
            StoreProductInput,
        )

        prod = create_store_product(
            payload=StoreProductInput(nombre="Café Con Foto"),
            ctx=self.ctx_a,
            db_session=self.session,
        )

        png_1x1_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        upload_resp = upload_store_product_image(
            producto_id=prod.id,
            payload=StoreProductImageUploadRequest(imagen_base64=png_1x1_b64),
            ctx=self.ctx_a,
            db_session=self.session,
        )
        self.assertTrue(upload_resp.imagen_url.startswith("/static/uploads/productos/"))

        # Actualizar el producto enviando imagen=None (como cuando solo se edita el nombre o descripción)
        updated = update_store_product(
            product_id=prod.id,
            payload=StoreProductInput(nombre="Café Con Foto Renombrado", imagen=None),
            ctx=self.ctx_a,
            db_session=self.session,
        )
        self.assertEqual(updated.imagen, upload_resp.imagen_url)

        # Si explícitamente se envía string vacío, debe borrarse la imagen
        cleared = update_store_product(
            product_id=prod.id,
            payload=StoreProductInput(nombre="Café Sin Foto", imagen=""),
            ctx=self.ctx_a,
            db_session=self.session,
        )
        self.assertIsNone(cleared.imagen)

    def test_password_recovery_and_email_flow(self):
        """Verifica el flujo completo de recuperación de contraseña y envío de correos sin costo."""
        from core.email_service import EmailService
        from api.admin_tienda import (
            request_password_reset,
            reset_store_admin_password,
            store_admin_login,
            StoreForgotPasswordRequest,
            StoreResetPasswordRequest,
            StoreAdminLoginRequest,
        )
        from core.security_store_admin import decode_password_reset_token

        # 1. Probar servicio de correo nativo en modo mock
        welcome_ok = EmailService.send_welcome_email(
            to_email="test@tostaduria.cl",
            tienda_nombre="Tostaduría de Prueba",
        )
        self.assertTrue(welcome_ok)

        reset_email_ok = EmailService.send_password_reset_email(
            to_email="test@tostaduria.cl",
            tienda_nombre="Tostaduría de Prueba",
            reset_url="https://cafesitios.cl/admin-tienda/restablecer-password?token=mocktoken123",
        )
        self.assertTrue(reset_email_ok)

        # 2. Solicitar recuperación de contraseña para admin_a
        req = DummyRequest()
        res_req = request_password_reset(
            payload=StoreForgotPasswordRequest(email=self.user_admin_a.usuario_id),
            request=req,
            db_session=self.session,
        )
        self.assertTrue(res_req["exito"])
        self.assertIn("recibirás las instrucciones", res_req["mensaje"])

        # 3. Generar token de prueba y decodificarlo
        from core.security_store_admin import create_password_reset_token
        token = create_password_reset_token(usuario_id=self.user_admin_a.usuario_id, tienda_id=self.tienda_a.id)
        decoded = decode_password_reset_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["usuario_id"], self.user_admin_a.usuario_id)

        # 4. Restablecer la contraseña con nueva clave
        nueva_clave = "SuperPasswordSeguro2026!"
        res_reset = reset_store_admin_password(
            payload=StoreResetPasswordRequest(token=token, nueva_password=nueva_clave),
            request=req,
            db_session=self.session,
        )
        self.assertTrue(res_reset["exito"])

        # 5. Iniciar sesión exitosamente con la nueva clave restablecida
        login_resp = store_admin_login(
            payload=StoreAdminLoginRequest(
                email=self.user_admin_a.usuario_id,
                password=nueva_clave,
                turnstile_token="mock_valid",
            ),
            request=req,
            db_session=self.session,
        )
        self.assertIsNotNone(login_resp.token)
        self.assertEqual(login_resp.tienda_id, self.tienda_a.id)

if __name__ == "__main__":
    unittest.main()
