from datetime import datetime, timezone
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db_session, require_local_admin
from db.database import AuditoriaAccionesTienda, Base, Tienda
from plataforma_backend import app


class TestGlobalStoreAuditEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        def override_require_admin():
            return True

        app.dependency_overrides[get_db_session] = override_get_db
        app.dependency_overrides[require_local_admin] = override_require_admin
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        with self.SessionLocal() as session:
            # Clean existing test data
            t1 = Tienda(
                nombre="Tostaduría Global Audit Alpha",
                url_base="https://audit-alpha.cl",
                plataforma="woocommerce",
                activo=True,
            )
            t2 = Tienda(
                nombre="Tostaduría Global Audit Beta",
                url_base="https://audit-beta.cl",
                plataforma="shopify",
                activo=True,
            )
            session.add_all([t1, t2])
            session.commit()
            session.refresh(t1)
            session.refresh(t2)
            self.t1_id = t1.id
            self.t2_id = t2.id

            log1 = AuditoriaAccionesTienda(
                tienda_id=t1.id,
                usuario_id="admin@audit-alpha.cl",
                accion="CREAR_PRODUCTO",
                entidad="productos",
                entidad_id=101,
                valores_previos=None,
                valores_nuevos={"nombre": "Geisha Volcán", "precio_clp": 16990},
                ip_origen="192.168.1.10",
                fecha_registro=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            log2 = AuditoriaAccionesTienda(
                tienda_id=t2.id,
                usuario_id="tostador@audit-beta.cl",
                accion="UPDATE_PERFIL",
                entidad="tiendas",
                entidad_id=t2.id,
                valores_previos={"telefono_whatsapp": None},
                valores_nuevos={"telefono_whatsapp": "+56911223344"},
                ip_origen="192.168.1.20",
                fecha_registro=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            session.add_all([log1, log2])
            session.commit()
            session.refresh(log1)
            session.refresh(log2)
            self.log1_id = log1.id
            self.log2_id = log2.id

    def tearDown(self):
        with self.SessionLocal() as session:
            for tid in [self.t1_id, self.t2_id]:
                t = session.get(Tienda, tid)
                if t:
                    session.delete(t)
            session.commit()

    def test_list_global_audit_logs_all(self):
        # Localhost client
        res = self.client.get(
            "/api/v1/administracion/auditoria-tiendas",
            headers={"host": "localhost:8000"},
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("registros", data)
        self.assertIn("total", data)
        self.assertIn("total_tiendas", data)
        self.assertGreaterEqual(data["total"], 2)

        # Check that both stores appear
        ids = [item["id"] for item in data["registros"]]
        self.assertIn(self.log1_id, ids)
        self.assertIn(self.log2_id, ids)

        # Check tienda_nombre
        item1 = next(item for item in data["registros"] if item["id"] == self.log1_id)
        self.assertEqual(item1["tienda_nombre"], "Tostaduría Global Audit Alpha")
        self.assertEqual(item1["accion"], "CREAR_PRODUCTO")
        self.assertEqual(item1["valores_nuevos"]["nombre"], "Geisha Volcán")

    def test_filter_by_tienda_id(self):
        res = self.client.get(
            f"/api/v1/administracion/auditoria-tiendas?tienda_id={self.t1_id}",
            headers={"host": "localhost:8000"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(all(item["tienda_id"] == self.t1_id for item in data["registros"]))
        ids = [item["id"] for item in data["registros"]]
        self.assertIn(self.log1_id, ids)
        self.assertNotIn(self.log2_id, ids)

    def test_filter_by_accion(self):
        res = self.client.get(
            "/api/v1/administracion/auditoria-tiendas?accion=UPDATE_PERFIL",
            headers={"host": "localhost:8000"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(all(item["accion"] == "UPDATE_PERFIL" for item in data["registros"]))

    def test_alias_endpoint(self):
        res = self.client.get(
            "/api/v1/admin/stores/audit-logs",
            headers={"host": "localhost:8000"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("registros", data)


if __name__ == "__main__":
    unittest.main()
