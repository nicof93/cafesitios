import unittest
from fastapi.testclient import TestClient
from main import app as public_app
from plataforma_backend import app as plataforma_app


class TestBackendSeparation(unittest.TestCase):
    """Valida la separación física y lógica entre el backend público/tiendas (Parte 1)
    y el backend de la plataforma de administración superadmin (Parte 2).
    """

    @classmethod
    def setUpClass(cls):
        cls.public_client = TestClient(public_app)
        cls.plataforma_client = TestClient(plataforma_app)

    def test_public_app_healthcheck(self):
        resp = self.public_client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("service"), "Cafe-sitios API")

    def test_plataforma_app_healthcheck(self):
        resp = self.plataforma_client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("service"), "Cafe-sitios Plataforma Superadmin API")

    def test_public_app_has_public_and_store_admin_routes(self):
        paths = list(public_app.openapi()["paths"].keys())
        # Debe contener catálogo público y comparador
        self.assertTrue(any(p.startswith("/api/v1/productos") or p.startswith("/api/v1/products") for p in paths))
        self.assertTrue(any(p.startswith("/api/v1/tiendas") or p.startswith("/api/v1/stores") for p in paths))
        self.assertTrue(any(p.startswith("/api/v1/recetas") for p in paths))
        self.assertTrue(any(p.startswith("/api/v1/pedidos") or p.startswith("/api/v1/orders") for p in paths))
        self.assertTrue(any(p.startswith("/api/v1/telemetria") or p.startswith("/api/v1/telemetry") for p in paths))
        self.assertTrue(any(p.startswith("/api/v1/sugerencias") or p.startswith("/api/v1/feedback") for p in paths))
        # Debe contener el portal de administración de tostadurías por parte del encargado
        self.assertTrue(any(p.startswith("/api/v1/admin/tienda") for p in paths))

    def test_public_app_does_not_contain_platform_admin_routes(self):
        paths = list(public_app.openapi()["paths"].keys())
        # NO debe contener endpoints de administración global superadmin
        self.assertFalse(any(p.startswith("/api/v1/administracion") for p in paths))
        self.assertFalse(any(p.startswith("/api/v1/admin/stores") for p in paths))
        self.assertFalse(any(p.startswith("/api/v1/admin/status") for p in paths))

        # Al consultar un endpoint superadmin en la app pública, debe responder 404
        resp = self.public_client.get("/api/v1/administracion/ambientes")
        self.assertEqual(resp.status_code, 404)

        resp2 = self.public_client.get("/api/v1/administracion/tiendas")
        self.assertEqual(resp2.status_code, 404)

    def test_plataforma_app_contains_platform_admin_routes(self):
        paths = list(plataforma_app.openapi()["paths"].keys())
        # Debe contener la superadministración de tiendas, ambientes, almacenamiento y auditoría
        self.assertTrue(any(p.startswith("/api/v1/administracion") for p in paths))
        self.assertTrue(any(p.startswith("/api/v1/admin/stores") for p in paths))
        self.assertTrue(any("/ambientes" in p for p in paths))
        self.assertTrue(any("/tiendas" in p for p in paths))


if __name__ == "__main__":
    unittest.main()
