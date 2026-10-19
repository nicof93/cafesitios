import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, SugerenciaFeedback
from main import app
from api.dependencies import get_db_session
from api.feedback import _feedback_rate_limit
from application.manage_feedback import ManageFeedbackUseCase


class TestFeedbackAPI(unittest.TestCase):
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
        _feedback_rate_limit.clear()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_honeypot_rejection(self):
        payload = {
            "categoria": "Funcionalidad",
            "mensaje": "Mensaje de bot",
            "website_hp": "spam link",
        }
        res = self.client.post("/api/v1/feedback", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("bot", res.json()["detail"].lower())

    def test_submit_feedback_with_sha256_ip_hash(self):
        payload = {
            "categoria": "Nueva Tienda",
            "mensaje": "Sugiero agregar Tostaduría Café Puerto Varas",
            "contacto_opcional": "barista@cafepv.cl",
        }
        res = self.client.post(
            "/api/v1/feedback",
            json=payload,
            headers={"X-Forwarded-For": "190.161.45.12"}
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["status"], "ok")

        # Verificar en base de datos que la IP quedó anonimizada con hash SHA-256
        db = self.TestingSessionLocal()
        fb = db.query(SugerenciaFeedback).first()
        self.assertIsNotNone(fb)
        self.assertEqual(fb.categoria, "Nueva Tienda")
        expected_hash = ManageFeedbackUseCase.hash_ip("190.161.45.12")
        self.assertEqual(fb.ip_hash, expected_hash)
        # Nunca guardar IP en texto plano (RNF-05)
        self.assertNotIn("190.161.45.12", fb.ip_hash)
        db.close()

    def test_rate_limit_2_per_hour(self):
        payload = {
            "categoria": "Funcionalidad",
            "mensaje": "Sugerencia de prueba",
        }
        headers = {"X-Forwarded-For": "200.50.10.5"}
        res1 = self.client.post("/api/v1/feedback", json=payload, headers=headers)
        self.assertEqual(res1.status_code, 201)

        res2 = self.client.post("/api/v1/feedback", json=payload, headers=headers)
        self.assertEqual(res2.status_code, 201)

        # La 3ra debe dar HTTP 429
        res3 = self.client.post("/api/v1/feedback", json=payload, headers=headers)
        self.assertEqual(res3.status_code, 429)


if __name__ == "__main__":
    unittest.main()

