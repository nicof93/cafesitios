import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, InteraccionClic
from main import app
from api.dependencies import get_db_session
from application.manage_telemetry import ManageTelemetryUseCase


class TestTelemetryAPI(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.TestingSessionLocal = sessionmaker(bind=self.engine)

        def override_get_db():
            db = self.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db_session] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_record_click_event(self):
        payload = {
            "tipo_evento": "clic_tienda_externa",
            "producto_id": 10,
            "variante_id": 20,
            "metadata_evento": {
                "tienda_destino": "Singular Coffee",
                "precio_clp": 15000,
            }
        }
        res = self.client.post(
            "/api/v1/telemetry/event",
            json=payload,
            headers={"X-Forwarded-For": "186.104.22.8"}
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["event_id"] > 0)

        # Verificar en base de datos
        db = self.TestingSessionLocal()
        interaccion = db.query(InteraccionClic).filter(InteraccionClic.id == data["event_id"]).first()
        self.assertIsNotNone(interaccion)
        self.assertEqual(interaccion.tipo_evento, "clic_tienda_externa")
        expected_hash = ManageTelemetryUseCase.hash_ip("186.104.22.8")
        self.assertEqual(interaccion.ip_hash, expected_hash)
        self.assertEqual(interaccion.metadata_evento["tienda_destino"], "Singular Coffee")
        db.close()


if __name__ == "__main__":
    unittest.main()

