import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.admin import (
    BranchInput,
    CatalogTestRequest,
    StoreCreateUpdateRequest,
    VisibilityUpdateRequest,
    BulkVisibilityUpdateRequest,
    create_or_update_store,
    export_stores_and_branches,
    list_admin_stores,
    list_moderation_products,
    test_store_catalog,
    update_product_visibility,
    bulk_update_product_visibility,
    sync_single_store,
    sync_unsynced_stores,
    sync_all_stores,
)
from api.stores import extract_official_website
from core.normalizer import is_valid_tasting_note
from db.database import Base, Producto, SucursalTienda, Tienda, Variante, Sincronizacion


class TestAdminAndFeatures(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_extract_official_website_domain(self):
        # Must strip paths, collections, queries to just protocol + domain (cut at .cl, .com, etc.)
        self.assertEqual(
            extract_official_website("https://singularcoffee.cl/collections/cafe"),
            "https://singularcoffee.cl",
        )
        self.assertEqual(
            extract_official_website("https://cafecascanueces.cl/categoria-producto/linea-arabica-especialidad/"),
            "https://cafecascanueces.cl",
        )
        self.assertEqual(
            extract_official_website("artisanroast.cl/shop/coffee?sort=price"),
            "https://artisanroast.cl",
        )
        self.assertIsNone(extract_official_website(None))
        self.assertIsNone(extract_official_website(""))

    def test_invalid_tasting_notes_filtered(self):
        # "historia", "finca", "proceso", "origen", etc. must NOT be considered valid tasting notes
        self.assertFalse(is_valid_tasting_note("historia"))
        self.assertFalse(is_valid_tasting_note("Historia"))
        self.assertFalse(is_valid_tasting_note("finca"))
        self.assertFalse(is_valid_tasting_note("proceso"))
        self.assertFalse(is_valid_tasting_note("origen"))
        # Real sensory tasting notes must be valid
        self.assertTrue(is_valid_tasting_note("Chocolate"))
        self.assertTrue(is_valid_tasting_note("Jazmín"))
        self.assertTrue(is_valid_tasting_note("Frutos Rojos"))
        self.assertTrue(is_valid_tasting_note("Caramelo"))

    def test_create_store_with_branches_and_export(self):
        # 1. Register store with branches
        payload = StoreCreateUpdateRequest(
            nombre="Café El Grano",
            url_catalogo="https://elgrano.cl/shop/cafe",
            plataforma="woocommerce",
            direccion="Av. Providencia 1234",
            comuna="Providencia",
            latitud=-33.4314,
            longitud=-70.6093,
            activo=True,
            sucursales=[
                BranchInput(
                    nombre="Sucursal Providencia",
                    direccion="Av. Providencia 1234",
                    comuna="Providencia",
                    latitud=-33.4314,
                    longitud=-70.6093,
                    activo=True,
                ),
                BranchInput(
                    nombre="Sucursal Las Condes",
                    direccion="Av. Apoquindo 4500",
                    comuna="Las Condes",
                    latitud=-33.4117,
                    longitud=-70.5808,
                    activo=True,
                ),
            ],
        )

        res = create_or_update_store(payload=payload, db_session=self.session)
        self.assertEqual(res.nombre, "Café El Grano")
        self.assertEqual(res.sitio_oficial, "https://elgrano.cl")
        self.assertEqual(res.url_web, "https://elgrano.cl")
        self.assertEqual(res.url_catalogo, "https://elgrano.cl/shop/cafe")
        self.assertEqual(len(res.sucursales), 2)

        # 2. List stores in admin
        list_res = list_admin_stores(db_session=self.session)
        self.assertEqual(list_res.total_tiendas, 1)
        self.assertEqual(list_res.tiendas[0].sitio_oficial, "https://elgrano.cl")
        self.assertEqual(len(list_res.tiendas[0].sucursales), 2)

        # 3. Export to production JSON & SQL
        export_res = export_stores_and_branches(db_session=self.session)
        self.assertEqual(export_res.total_tiendas, 1)
        self.assertEqual(export_res.total_sucursales, 2)
        self.assertIn("INSERT INTO tiendas", export_res.sql_script)
        self.assertIn("INSERT INTO sucursales_tienda", export_res.sql_script)
        self.assertIn("Café El Grano", export_res.sql_script)

    def test_product_moderation_and_visibility(self):
        # Setup store and products (one coffee, one non-coffee accessory)
        store = Tienda(
            nombre="Tostaduría Test",
            url_base="https://tostaduria.cl",
            plataforma="shopify",
            activo=True,
        )
        self.session.add(store)
        self.session.flush()

        prod_coffee = Producto(
            tienda_id=store.id,
            id_externo="prod-1",
            nombre="Café Etiopía Guji Lavado 250g",
            descripcion="Notas a jazmín y durazno",
            url_detalle="https://tostaduria.cl/cafe-etiopia",
            activo=True,
            oculto_catalogo=False,
        )
        prod_polera = Producto(
            tienda_id=store.id,
            id_externo="prod-2",
            nombre="Polera Algodón Logo Tostaduría Talla L",
            descripcion="Merchandising 100% algodón",
            url_detalle="https://tostaduria.cl/polera-logo",
            activo=True,
            oculto_catalogo=False,
        )
        self.session.add_all([prod_coffee, prod_polera])
        self.session.flush()

        # Add variants
        v1 = Variante(
            producto_id=prod_coffee.id,
            id_variante_externo="v-1",
            opcion="250g",
            formato_gramos=250,
            precio_clp=12990,
            precio_original_clp=12990,
            precio_por_kilo=51960.0,
            disponible=True,
        )
        v2 = Variante(
            producto_id=prod_polera.id,
            id_variante_externo="v-2",
            opcion="Talla L",
            formato_gramos=250,
            precio_clp=15000,
            precio_original_clp=15000,
            precio_por_kilo=60000.0,
            disponible=True,
        )
        self.session.add_all([v1, v2])
        self.session.commit()

        # 1. Moderation list should detect the polera as suspected
        mod_res = list_moderation_products(
            mode="suspected",
            store_name=None,
            q=None,
            limit=50,
            db_session=self.session,
        )
        self.assertEqual(len(mod_res.items), 1)
        self.assertEqual(mod_res.items[0].nombre, "Polera Algodón Logo Tostaduría Talla L")
        self.assertTrue(mod_res.items[0].es_sospechoso)

        # 2. Hide the polera from general catalog
        patch_res = update_product_visibility(
            product_id=prod_polera.id,
            payload=VisibilityUpdateRequest(oculto_catalogo=True),
            db_session=self.session,
        )
        self.assertTrue(patch_res.oculto_catalogo)

        # 3. Refresh and check database state
        self.session.refresh(prod_polera)
        self.assertTrue(prod_polera.oculto_catalogo)

        # 4. Bulk update
        bulk_res = bulk_update_product_visibility(
            payload=BulkVisibilityUpdateRequest(
                product_ids=[prod_coffee.id],
                oculto_catalogo=False,
            ),
            db_session=self.session,
        )
        self.assertEqual(bulk_res.updated_count, 1)

    def test_catalog_test_with_mock_driver(self):
        # Test catalog legibility endpoint with mock driver returning products
        mock_product = {
            "id_externo": "1001",
            "nombre": "Café Colombia Supremo 250g",
            "url_detalle": "https://teststore.cl/cafe-colombia",
            "imagen": "https://teststore.cl/img.jpg",
            "descripcion": "Café de origen Colombia, proceso Lavado, notas a caramelo y chocolate",
            "variantes": [
                {
                    "id_externo": "1001-v1",
                    "formato_gramos": 250,
                    "precio_clp": 9990,
                    "precio_por_kilo": 39960.0,
                    "disponible": True,
                }
            ],
        }

        with patch("api.admin.WooCommerceDriver.consumir_productos", return_value=[mock_product]):
            req = CatalogTestRequest(
                nombre="Test Store",
                url_catalogo="https://teststore.cl/shop",
                plataforma="woocommerce",
            )
            res = test_store_catalog(payload=req)
            self.assertTrue(res.legible)
            self.assertEqual(res.plataforma_detectada, "woocommerce")
            self.assertEqual(res.total_productos_detectados, 1)
            self.assertIsNotNone(res.primer_producto)
            self.assertEqual(res.primer_producto.nombre, "Café Colombia Supremo 250g")
            self.assertEqual(res.primer_producto.precio_clp, 9990)

    def test_cors_preflight_for_astro_and_local_origins(self):
        import asyncio
        from main import app

        async def run_preflight(origin: str, path: str):
            scope = {
                "type": "http",
                "method": "OPTIONS",
                "path": path,
                "raw_path": path.encode("ascii"),
                "headers": [
                    (b"origin", origin.encode("ascii")),
                    (b"access-control-request-method", b"POST"),
                    (b"access-control-request-headers", b"content-type"),
                ],
                "query_string": b"",
                "client": ("127.0.0.1", 54321),
                "app": app,
            }
            messages = []

            async def receive():
                return {"type": "http.request"}

            async def send(msg):
                messages.append(msg)

            await app(scope, receive, send)
            start_msg = [m for m in messages if m.get("type") == "http.response.start"][0]
            headers = dict(start_msg.get("headers", []))
            return start_msg.get("status"), headers.get(b"access-control-allow-origin")

        for test_origin in ["http://localhost:4321", "http://127.0.0.1:4321", "http://localhost:3000"]:
            status_code, allow_origin = asyncio.run(
                run_preflight(test_origin, "/api/v1/admin/stores/test-catalog")
            )
            self.assertEqual(status_code, 200, f"Failed preflight for {test_origin}")
            self.assertEqual(
                allow_origin,
                test_origin.encode("ascii"),
                f"Missing or mismatched CORS header for {test_origin}",
            )

    def test_sync_single_store_endpoint(self):
        store = Tienda(
            nombre="Café Singular Test",
            url_base="https://singularcoffee.cl",
            plataforma="shopify",
            activo=True,
        )
        self.session.add(store)
        self.session.commit()

        mock_sync_result = {
            "tienda_id": store.id,
            "nombre": store.nombre,
            "exito": True,
            "total_productos": 15,
            "productos_nuevos": 5,
            "productos_actualizados": 10,
            "productos_eliminados": 0,
            "duracion_segundos": 1.25,
            "error": None,
        }

        with patch("api.admin.sincronizar_tienda", return_value=mock_sync_result):
            res = sync_single_store(store_id=store.id, db_session=self.session)
            self.assertEqual(res.tienda_id, store.id)
            self.assertEqual(res.nombre, "Café Singular Test")
            self.assertTrue(res.exito)
            self.assertEqual(res.total_productos, 15)
            self.assertEqual(res.productos_nuevos, 5)
            self.assertEqual(res.productos_actualizados, 10)
            self.assertIn("15 productos sincronizados", res.mensaje)

    def test_sync_unsynced_and_all_stores_endpoints(self):
        store = Tienda(
            nombre="Café Pendiente Test",
            url_base="https://pendiente.cl",
            plataforma="woocommerce",
            activo=True,
        )
        self.session.add(store)
        self.session.commit()

        mock_batch_result = {
            "total_tiendas": 1,
            "tiendas_exitosas": 1,
            "tiendas_fallidas": 0,
            "total_productos_sincronizados": 8,
            "total_productos_nuevos": 8,
            "total_productos_actualizados": 0,
            "duracion_segundos": 0.85,
            "detalles": [
                {
                    "tienda_id": store.id,
                    "nombre": store.nombre,
                    "exito": True,
                    "total_productos": 8,
                    "productos_nuevos": 8,
                    "productos_actualizados": 0,
                    "productos_eliminados": 0,
                    "duracion_segundos": 0.85,
                    "error": None,
                }
            ],
        }

        with patch("api.admin.DatabaseManager.listar_tiendas_no_sincronizadas", return_value=[{"id": store.id, "nombre": store.nombre, "url_base": store.url_base, "plataforma": store.plataforma}]):
            with patch("api.admin.sincronizar_multiples_tiendas", return_value=mock_batch_result):
                res_unsynced = sync_unsynced_stores(db_session=self.session)
                self.assertEqual(res_unsynced.tipo_sincronizacion, "pendientes")
                self.assertEqual(res_unsynced.total_tiendas, 1)
                self.assertEqual(res_unsynced.tiendas_exitosas, 1)
                self.assertEqual(res_unsynced.total_productos_nuevos, 8)
                self.assertEqual(len(res_unsynced.detalles), 1)

        with patch("api.admin.DatabaseManager.listar_tiendas_activas", return_value=[{"id": store.id, "nombre": store.nombre, "url_base": store.url_base, "plataforma": store.plataforma}]):
            with patch("api.admin.sincronizar_multiples_tiendas", return_value=mock_batch_result):
                res_all = sync_all_stores(db_session=self.session)
                self.assertEqual(res_all.tipo_sincronizacion, "masiva")
                self.assertEqual(res_all.total_tiendas, 1)
                self.assertEqual(res_all.tiendas_exitosas, 1)
                self.assertEqual(len(res_all.detalles), 1)

    def test_list_admin_stores_includes_sync_metadata(self):
        store1 = Tienda(
            nombre="Tienda Activa Con Productos",
            url_base="https://activa.cl/shop",
            plataforma="woocommerce",
            activo=True,
        )
        store2 = Tienda(
            nombre="Tienda Pendiente Sin Productos",
            url_base="https://sin-productos.cl/shop",
            plataforma="shopify",
            activo=True,
        )
        self.session.add_all([store1, store2])
        self.session.commit()

        # Add an active product to store1
        prod = Producto(
            tienda_id=store1.id,
            nombre="Café Geisha",
            url_detalle="https://activa.cl/geisha",
            activo=True,
            oculto_catalogo=False,
        )
        from datetime import datetime, timezone
        sync_log = Sincronizacion(
            tienda_id=store1.id,
            fecha_inicio=datetime.now(timezone.utc),
            resultado="exitoso",
            productos_agregados=1,
            productos_actualizados=0,
        )
        self.session.add_all([prod, sync_log])
        self.session.commit()

        res = list_admin_stores(db_session=self.session)
        self.assertEqual(res.total_tiendas, 2)
        self.assertEqual(res.total_sincronizadas, 1)
        self.assertEqual(res.total_pendientes, 1)

        store1_item = next(it for it in res.tiendas if it.id == store1.id)
        store2_item = next(it for it in res.tiendas if it.id == store2.id)

        self.assertFalse(store1_item.es_pendiente_sincronizacion)
        self.assertTrue(store2_item.es_pendiente_sincronizacion)

    def test_store_admin_email_assignment_and_export(self) -> None:
        """Verifica que registrar y actualizar el email del administrador crea UsuarioTienda y se exporta."""
        from api.admin import (
            StoreCreateUpdateRequest,
            create_or_update_store,
            export_stores_and_branches,
            list_admin_stores,
            update_store_by_id,
        )
        from db.database import UsuarioTienda

        # 1. Crear tienda con email de administrador
        req = StoreCreateUpdateRequest(
            nombre="Tostaduría Austral",
            url_catalogo="https://australcoffee.cl/tienda",
            plataforma="woocommerce",
            email_administrador="tostador@australcoffee.cl",
            sucursales=[],
        )
        created = create_or_update_store(payload=req, db_session=self.session)
        self.assertEqual(created.email_administrador, "tostador@australcoffee.cl")

        # Verificar que se creó en la tabla usuarios_tienda
        user_in_db = self.session.query(UsuarioTienda).filter_by(tienda_id=created.id).first()
        self.assertIsNotNone(user_in_db)
        self.assertEqual(user_in_db.usuario_id, "tostador@australcoffee.cl")
        self.assertEqual(user_in_db.rol, "STORE_ADMIN")

        # 2. Verificar que list_admin_stores retorna el email
        listing = list_admin_stores(db_session=self.session)
        store_item = next(it for it in listing.tiendas if it.id == created.id)
        self.assertEqual(store_item.email_administrador, "tostador@australcoffee.cl")

        # 3. Actualizar el email de administrador de la tienda
        update_req = StoreCreateUpdateRequest(
            nombre="Tostaduría Austral",
            url_catalogo="https://australcoffee.cl/tienda",
            plataforma="woocommerce",
            email_administrador="nuevo_admin@australcoffee.cl",
            sucursales=[],
        )
        updated = update_store_by_id(store_id=created.id, payload=update_req, db_session=self.session)
        self.assertEqual(updated.email_administrador, "nuevo_admin@australcoffee.cl")

        user_in_db_updated = self.session.query(UsuarioTienda).filter_by(tienda_id=created.id).first()
        self.assertEqual(user_in_db_updated.usuario_id, "nuevo_admin@australcoffee.cl")

        # 4. Verificar exportación SQL y JSON
        export_res = export_stores_and_branches(db_session=self.session)
        exported_store = next(s for s in export_res.tiendas if s["nombre"] == "Tostaduría Austral")
        self.assertEqual(exported_store["email_administrador"], "nuevo_admin@australcoffee.cl")
        self.assertIn("INSERT INTO usuarios_tienda", export_res.sql_script)
        self.assertIn("nuevo_admin@australcoffee.cl", export_res.sql_script)


if __name__ == "__main__":
    unittest.main()

