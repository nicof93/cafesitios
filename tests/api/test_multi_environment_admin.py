import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from db.database import Base, DatabaseManager
from db.environments import EnvironmentManager


class TestMultiEnvironmentAdmin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        cls.mock_db = DatabaseManager(db_url="sqlite://")
        cls.mock_db.engine = cls.engine
        cls.mock_db.SessionLocal = cls.SessionLocal
        cls._orig_local = DatabaseManager._instances.get("local")
        DatabaseManager._instances["local"] = cls.mock_db

    @classmethod
    def tearDownClass(cls):
        if cls._orig_local is not None:
            DatabaseManager._instances["local"] = cls._orig_local
        else:
            DatabaseManager._instances.pop("local", None)
        cls.engine.dispose()

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

    def test_admin_stores_with_target_environment_header(self):
        """Verifica que el header X-Target-Environment permita consultar tiendas sin 500."""
        res = self.client.get(
            "/api/v1/admin/stores",
            headers={"X-Target-Environment": "local"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("tiendas", data)
        self.assertIn("total_tiendas", data)

    def test_admin_status_with_target_environment_header(self):
        """Verifica que el header X-Target-Environment permita consultar status administrativo."""
        res = self.client.get(
            "/api/v1/admin/status",
            headers={"X-Target-Environment": "local"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_tiendas", data)

    def test_admin_export_with_target_environment_header(self):
        """Verifica que la exportación funcione con el header de ambiente."""
        res = self.client.get(
            "/api/v1/admin/stores/export",
            headers={"X-Target-Environment": "local"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("tiendas", data)
        self.assertIn("sql_script", data)

    def test_admin_resilience_to_legacy_schema_without_catalogos_or_user_tables(self):
        """Verifica que esquemas antiguos de BD (sin tabla tienda_catalogos ni usuarios_tienda) no rompan la API."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from db.database import Base, Tienda, SucursalTienda, Producto, Variante
        from api.admin import list_admin_stores, export_stores_and_branches, _get_store_catalogs_safe

        mem_engine = create_engine("sqlite:///:memory:")
        # Crear únicamente un subconjunto mínimo de tablas (simulando esquemas antiguos)
        Base.metadata.tables["tiendas"].create(mem_engine)
        Base.metadata.tables["sucursales_tienda"].create(mem_engine)
        Base.metadata.tables["productos"].create(mem_engine)
        Base.metadata.tables["variantes"].create(mem_engine)

        MemSession = sessionmaker(bind=mem_engine)
        session = MemSession()

        try:
            store = Tienda(
                nombre="Tostaduría Esquema Antiguo",
                url_base="https://esquema-antiguo.cl",
                plataforma="shopify",
                activo=True,
            )
            session.add(store)
            session.commit()

            # 1. _get_store_catalogs_safe no debe disparar lazy-load ni fallar
            catalogs = _get_store_catalogs_safe(store)
            self.assertEqual(catalogs, [])

            # 2. list_admin_stores debe responder con 200 (AdminStoresListResponse)
            res_stores = list_admin_stores(db_session=session)
            self.assertEqual(res_stores.total_tiendas, 1)
            self.assertEqual(res_stores.tiendas[0].nombre, "Tostaduría Esquema Antiguo")
            self.assertEqual(res_stores.tiendas[0].catalogos, [])

            # 3. export_stores_and_branches debe exportar exitosamente
            res_export = export_stores_and_branches(db_session=session)
            self.assertEqual(len(res_export.tiendas), 1)
            self.assertEqual(res_export.total_catalogos, 0)
        finally:
            session.close()
            mem_engine.dispose()


if __name__ == "__main__":
    unittest.main()

