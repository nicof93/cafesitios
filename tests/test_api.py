import sys
from pathlib import Path
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app
from api.router import get_db_session
from domain.models import CoffeeProductDomain, VariantDomain

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

def mock_get_db_session_override():
    yield MockDatabaseSession()

app.dependency_overrides[get_db_session] = mock_get_db_session_override

class TestAPI(unittest.TestCase):
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
            self.assertEqual(data["total_items"], 1)
        finally:
            api.router.PostgresCoffeeRepository = original_repo

if __name__ == "__main__":
    unittest.main()
