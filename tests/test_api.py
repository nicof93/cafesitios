import sys
from pathlib import Path
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app
from api.router import get_db_session, get_product_detail
from db.database import Base, Producto, Tienda, Variante
from domain.models import CoffeeProductDomain, VariantDomain
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

client = TestClient(app)

class MockDatabaseSession:
    pass

class MockCoffeeRepositoryForAPI:
    def __init__(self, session=None):
        pass

    def get_cheapest_products(self, **kwargs):
        return [
            CoffeeProductDomain(
                id=1,
                tienda="Singular Coffee",
                nombre="Café Test",
                url_detalle="https://singular.cl/p1",
                imagen=None,
                descripcion="Floral",
                variante_mas_barata=VariantDomain(
                    id_externo="v1", opcion="250g", formato_gramos=250,
                    precio_clp=10000, precio_original_clp=10000, en_oferta=False,
                    descuento_porcentaje=0, precio_por_kilo=40000.0, disponible=True
                )
            )
        ]

    def count_cheapest_products(self, **kwargs):
        return 2

def mock_get_db_session_override():
    yield MockDatabaseSession()

app.dependency_overrides[get_db_session] = mock_get_db_session_override

class TestAPI(unittest.TestCase):
    def test_product_detail_returns_description_and_all_variants(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        try:
            store = Tienda(nombre="Tienda Demo", url_base="https://example.com")
            product = Producto(
                tienda=store,
                nombre="Café de prueba",
                url_detalle="https://example.com/cafe",
                descripcion="Notas de cacao y frutos rojos",
            )
            product.variantes = [
                Variante(
                    id_variante_externo="variant-250",
                    opcion="Grano",
                    formato_gramos=250,
                    precio_clp=10000,
                    precio_original_clp=12000,
                    en_oferta=True,
                    descuento_porcentaje=17,
                    precio_por_kilo=40000,
                    disponible=True,
                ),
                Variante(
                    id_variante_externo="variant-1000",
                    opcion="Grano",
                    formato_gramos=1000,
                    precio_clp=35000,
                    precio_original_clp=35000,
                    en_oferta=False,
                    descuento_porcentaje=0,
                    precio_por_kilo=35000,
                    disponible=False,
                ),
            ]
            session.add(product)
            session.commit()

            result = get_product_detail(product.id, session)

            self.assertEqual(result["descripcion"], "Notas de cacao y frutos rojos")
            self.assertEqual(result["tienda"], "Tienda Demo")
            self.assertEqual(len(result["variantes"]), 2)
            self.assertEqual(result["variantes"][1]["formato_gramos"], 1000)
            self.assertFalse(result["variantes"][1]["disponible"])
        finally:
            session.close()
            engine.dispose()

    def test_healthcheck(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "Cafe-sitios API"})

    def test_api_route_registered(self):
        # Patch PostgresCoffeeRepository in api.router
        import api.router
        original_repo = api.router.PostgresCoffeeRepository
        api.router.PostgresCoffeeRepository = MockCoffeeRepositoryForAPI
        try:
            response = client.get("/api/v1/products/cheapest?limit=5")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("data", data)
            self.assertEqual(data["total_items"], 2)
        finally:
            api.router.PostgresCoffeeRepository = original_repo

    def test_stores_summary_endpoint(self):
        response = client.get("/api/v1/stores?page=1&page_size=10&sort_by=product_count_desc")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertIn("total_items", data)
        self.assertTrue(isinstance(data["items"], list))

    def test_last_sync_endpoint_without_record(self):
        response = client.get("/api/v1/sync/last")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"last_sync": None})

if __name__ == "__main__":
    unittest.main()
