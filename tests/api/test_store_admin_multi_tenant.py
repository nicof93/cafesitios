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
    Base,
    Producto,
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


if __name__ == "__main__":
    unittest.main()
