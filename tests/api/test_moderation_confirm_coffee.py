import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db_session
from db.database import Base, DatabaseManager, Producto, Tienda, Variante
from plataforma_backend import app


class TestModerationConfirmCoffee(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db_session] = override_get_db
        self.client = TestClient(app)

        self.tienda = Tienda(id=1, nombre="Tostaduría Test", url_base="https://test.cl", activo=True)
        self.db.add(self.tienda)
        self.db.commit()

        # Producto sospechoso (ej. "Pack Degustación Especial" o "Polera Barista")
        self.prod_suspect = Producto(
            id=101,
            tienda_id=1,
            nombre="Pack Tazas y Café Barista",
            categoria="no_cafe",
            url_detalle="https://test.cl/pack-barista",
            activo=True,
            oculto_catalogo=False,
            es_cafe_confirmado=False,
        )
        # Variante para el producto
        var = Variante(
            id=1001,
            producto_id=101,
            id_variante_externo="v1001",
            opcion="Default",
            precio_clp=15000,
            precio_original_clp=15000,
            formato_gramos=250,
            precio_por_kilo=60000.0,
            disponible=True,
        )
        self.db.add_all([self.prod_suspect, var])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        app.dependency_overrides.clear()

    def test_single_confirm_coffee_success(self):
        resp = self.client.patch(
            "/api/v1/administracion/productos/101/confirmar-cafe",
            json={"confirmado": True},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["es_cafe_confirmado"])
        self.assertEqual(data["categoria"], "cafe")
        self.assertFalse(data["oculto_catalogo"])

        # Verificar en DB
        self.db.expire_all()
        p = self.db.get(Producto, 101)
        self.assertTrue(p.es_cafe_confirmado)
        self.assertEqual(p.categoria, "cafe")

    def test_single_confirm_coffee_english_alias(self):
        resp = self.client.patch(
            "/api/v1/admin/products/101/confirm-coffee",
            json={"confirmado": True},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["es_cafe_confirmado"])

    def test_single_revert_confirm_coffee(self):
        # Primero confirmar
        self.client.patch(
            "/api/v1/administracion/productos/101/confirmar-cafe",
            json={"confirmado": True},
        )
        # Revertir
        resp = self.client.patch(
            "/api/v1/administracion/productos/101/confirmar-cafe",
            json={"confirmado": False},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["es_cafe_confirmado"])
        self.assertEqual(data["categoria"], "no_cafe")

    def test_bulk_confirm_coffee(self):
        # Crear segundo producto sospechoso
        prod2 = Producto(
            id=102,
            tienda_id=1,
            nombre="Caja Sorpresa de Café",
            categoria="no_cafe",
            url_detalle="https://test.cl/caja-sorpresa",
            activo=True,
            oculto_catalogo=False,
            es_cafe_confirmado=False,
        )
        var2 = Variante(
            id=1002,
            producto_id=102,
            id_variante_externo="v1002",
            opcion="Default",
            precio_clp=20000,
            precio_original_clp=20000,
            formato_gramos=500,
            precio_por_kilo=40000.0,
            disponible=True,
        )
        self.db.add_all([prod2, var2])
        self.db.commit()

        resp = self.client.post(
            "/api/v1/administracion/productos/confirmar-cafe-lote",
            json={"product_ids": [101, 102], "confirmado": True},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["updated_count"], 2)

        self.db.expire_all()
        p1 = self.db.get(Producto, 101)
        p2 = self.db.get(Producto, 102)
        self.assertTrue(p1.es_cafe_confirmado)
        self.assertTrue(p2.es_cafe_confirmado)
        self.assertEqual(p1.categoria, "cafe")
        self.assertEqual(p2.categoria, "cafe")

    def test_moderation_modes_filtering(self):
        # Inicialmente está en sospechosos
        resp_suspect = self.client.get("/api/v1/administracion/productos/moderacion?mode=suspected")
        self.assertEqual(resp_suspect.status_code, 200)
        items_suspect = resp_suspect.json()["items"]
        self.assertTrue(any(i["id"] == 101 for i in items_suspect))

        # Confirmar producto
        self.client.patch(
            "/api/v1/administracion/productos/101/confirmar-cafe",
            json={"confirmado": True},
        )

        # Ahora no debe aparecer en sospechosos
        resp_suspect2 = self.client.get("/api/v1/administracion/productos/moderacion?mode=suspected")
        items_suspect2 = resp_suspect2.json()["items"]
        self.assertFalse(any(i["id"] == 101 for i in items_suspect2))

        # Pero debe aparecer en mode=confirmed
        resp_confirmed = self.client.get("/api/v1/administracion/productos/moderacion?mode=confirmed")
        self.assertEqual(resp_confirmed.status_code, 200)
        data_conf = resp_confirmed.json()
        self.assertGreaterEqual(data_conf["total_confirmados_cafe"], 1)
        self.assertTrue(any(i["id"] == 101 for i in data_conf["items"]))
        self.assertTrue(data_conf["items"][0]["es_cafe_confirmado"])

    def test_guardar_catalogo_preserves_confirmed_coffee(self):
        # Confirmar el producto
        p = self.db.get(Producto, 101)
        p.es_cafe_confirmado = True
        p.categoria = "cafe"
        self.db.commit()

        # Simular scraping que clasifica nuevamente como 'no_cafe'
        manager = DatabaseManager("sqlite://")
        manager.SessionLocal = self.SessionLocal

        scraped_data = [
            {
                "tienda_id": 1,
                "nombre": "Pack Tazas y Café Barista",
                "categoria": "no_cafe",
                "url_detalle": "https://test.cl/pack-barista",
                "imagen": "https://test.cl/pack.jpg",
                "descripcion": "Descripción del pack",
                "id_externo": "ext101",
                "activo": True,
                "variantes": [
                    {
                        "id_variante_externo": "v1001",
                        "opcion": "Default",
                        "precio_clp": 15000,
                        "precio_original_clp": 15000,
                        "en_oferta": False,
                        "descuento_porcentaje": 0,
                        "formato_gramos": 250,
                        "precio_por_kilo": 60000.0,
                        "disponible": True,
                    }
                ],
            }
        ]

        manager.guardar_catalogo(scraped_data, 1)

        self.db.expire_all()
        refreshed = self.db.get(Producto, 101)
        self.assertEqual(refreshed.categoria, "cafe", "guardar_catalogo debe respetar es_cafe_confirmado")
        self.assertTrue(refreshed.es_cafe_confirmado)


if __name__ == "__main__":
    unittest.main()
