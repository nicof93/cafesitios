import os
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["ENVIRONMENT"] = "testing"

from api.dependencies import get_db_session, require_local_admin
from core.security_store_admin import decode_store_admin_token
from db.database import AuditoriaAccionesTienda, Base, Tienda, UsuarioTienda
from plataforma_backend import app


class TestSuperadminAuditAndImpersonate(unittest.TestCase):
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

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_impersonate_generates_audit_and_target_env(self):
        # 1. Crear tienda
        store = Tienda(
            nombre="Tostaduría Impersonate Test",
            url_base="https://testimpersonate.cl",
            plataforma="shopify",
            activo=True,
        )
        self.db.add(store)
        self.db.commit()
        self.db.refresh(store)

        # 2. Llamar endpoint de impersonación con header x-target-environment: supabase
        headers = {"x-target-environment": "supabase"}
        response = self.client.post(
            f"/api/v1/administracion/tiendas/{store.id}/impersonar",
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("target_env=supabase", data.get("redirect_url"))
        self.assertTrue(data.get("redirect_url", "").startswith("https://cafesitios.cl/admin-tienda/dashboard"))

        token = data.get("token")
        payload = decode_store_admin_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("rol"), "PLATFORM_SUPERADMIN")
        self.assertEqual(payload.get("tienda_id"), store.id)
        self.assertEqual(payload.get("target_env"), "supabase")

        # 3. Validar que se creó el registro de auditoría de inicio de impersonación
        audit_entry = self.db.scalars(
            select(AuditoriaAccionesTienda)
            .where(AuditoriaAccionesTienda.tienda_id == store.id)
            .where(AuditoriaAccionesTienda.accion == "IMPERSONACION_INICIADA")
        ).first()

        self.assertIsNotNone(audit_entry)
        self.assertIn("SUPERADMIN", audit_entry.usuario_id)
        self.assertEqual(audit_entry.valores_nuevos.get("ambiente"), "supabase")
        self.assertEqual(audit_entry.valores_nuevos.get("_ejecutado_por"), "SUPERADMIN_PLATAFORMA")

    def test_impersonate_local_environment_redirect_url(self):
        # Para el ambiente local, debe usar http://localhost:4321
        store = Tienda(
            nombre="Tostaduría Local Test",
            url_base="https://localtest.cl",
            plataforma="woocommerce",
            activo=True,
        )
        self.db.add(store)
        self.db.commit()
        self.db.refresh(store)

        headers = {"x-target-environment": "local"}
        response = self.client.post(
            f"/api/v1/administracion/tiendas/{store.id}/impersonar",
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("redirect_url", "").startswith("http://localhost:4321/admin-tienda/dashboard"))
        self.assertIn("target_env=local", data.get("redirect_url"))


if __name__ == "__main__":
    unittest.main()
