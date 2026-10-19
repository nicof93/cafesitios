import unittest
from fastapi.testclient import TestClient
from main import app
from db.environments import EnvironmentManager


class TestMultiEnvironmentAdmin(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_list_environments_localhost_success(self):
        response = self.client.get(
            "/api/v1/administracion/ambientes",
            headers={"Host": "localhost:8000"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        env_ids = [e["id"] for e in data]
        self.assertIn("local", env_ids)
        self.assertIn("supabase", env_ids)

    def test_list_environments_forbidden_outside_localhost(self):
        response = self.client.get(
            "/api/v1/administracion/ambientes",
            headers={"Host": "cafesitios.cl", "X-Forwarded-For": "200.1.2.3"},
        )
        self.assertEqual(response.status_code, 403)

    def test_create_and_delete_custom_environment(self):
        payload = {
            "id": "test-staging",
            "nombre": "Staging DB",
            "descripcion": "Ambiente de prueba para staging",
            "tipo": "postgres",
            "connection_url": "postgresql+psycopg://user:pass@localhost:5432/staging_db",
            "color_badge": "purple",
            "activo": True,
            "es_protegido": False,
        }
        # Crear
        res_create = self.client.post(
            "/api/v1/administracion/ambientes",
            json=payload,
            headers={"Host": "localhost:8000"},
        )
        self.assertEqual(res_create.status_code, 201)
        created = res_create.json()["environment"]
        self.assertEqual(created["id"], "test-staging")

        # Verificar en lista
        res_list = self.client.get(
            "/api/v1/administracion/ambientes",
            headers={"Host": "localhost:8000"},
        )
        env_ids = [e["id"] for e in res_list.json()]
        self.assertIn("test-staging", env_ids)

        # Eliminar
        res_del = self.client.delete(
            "/api/v1/administracion/ambientes/test-staging",
            headers={"Host": "localhost:8000"},
        )
        self.assertEqual(res_del.status_code, 200)

        # Intentar eliminar ambiente de sistema debe fallar (400)
        res_del_sys = self.client.delete(
            "/api/v1/administracion/ambientes/local",
            headers={"Host": "localhost:8000"},
        )
        self.assertEqual(res_del_sys.status_code, 400)

    def test_get_and_update_environment(self):
        # 1. Obtener ambiente local
        res_get = self.client.get(
            "/api/v1/administracion/ambientes/local",
            headers={"Host": "localhost:8000"},
        )
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["id"], "local")

        # 2. Editar descripción de ambiente local
        new_desc = "Base de datos local actualizada para pruebas"
        res_put = self.client.put(
            "/api/v1/administracion/ambientes/local",
            json={"descripcion": new_desc},
            headers={"Host": "localhost:8000"},
        )
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(res_put.json()["environment"]["descripcion"], new_desc)

    def test_test_environment_connection(self):
        res = self.client.post(
            "/api/v1/administracion/ambientes/local/probar",
            headers={"Host": "localhost:8000"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("success", data)
        self.assertIn("latency_ms", data)


if __name__ == "__main__":
    unittest.main()

