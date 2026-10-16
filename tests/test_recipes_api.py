import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base
from main import app
from api.dependencies import get_db_session
from api.recipes import APP_CLIENT_KEY, _recipe_rate_limit


class TestRecipesAPI(unittest.TestCase):
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
        _recipe_rate_limit.clear()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_layer_2_rejects_missing_or_invalid_secret_key(self):
        payload = {
            "dispositivo_uuid": "device-uuid-1234567890",
            "nombre_receta": "V60 Matutino",
            "metodo": "V60",
            "dosis_cafe_g": 15.0,
            "agua_ml": 250.0,
        }
        # Sin cabecera
        res_no_key = self.client.post("/api/v1/recetas", json=payload)
        self.assertEqual(res_no_key.status_code, 422)  # Missing header

        # Con clave incorrecta
        res_wrong_key = self.client.post(
            "/api/v1/recetas",
            json=payload,
            headers={"X-App-Client-Key": "clave-falsa"}
        )
        self.assertEqual(res_wrong_key.status_code, 401)

    def test_layer_3_rejects_honeypot(self):
        payload = {
            "dispositivo_uuid": "device-uuid-1234567890",
            "nombre_receta": "Espresso Doble",
            "metodo": "Espresso",
            "dosis_cafe_g": 18.0,
            "agua_ml": 36.0,
            "website_hp": "http://spambot.com",  # Honeypot poblado
        }
        res = self.client.post(
            "/api/v1/recetas",
            json=payload,
            headers={"X-App-Client-Key": APP_CLIENT_KEY}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("bot", res.json()["detail"].lower())

    def test_create_and_list_recipes_successfully(self):
        payload = {
            "dispositivo_uuid": "device-uuid-1234567890",
            "nombre_receta": "Aeropress Invertido",
            "metodo": "Aeropress",
            "dosis_cafe_g": 12.0,
            "agua_ml": 200.0,
        }
        res = self.client.post(
            "/api/v1/recetas",
            json=payload,
            headers={"X-App-Client-Key": APP_CLIENT_KEY}
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["nombre_receta"], "Aeropress Invertido")
        self.assertEqual(data["ratio"], "1:16.7")

        # Listar recetas por dispositivo
        res_list = self.client.get("/api/v1/recetas?dispositivo_uuid=device-uuid-1234567890")
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(len(res_list.json()), 1)

    def test_layer_5_quota_per_device_limit_15(self):
        # Crear 15 recetas
        for i in range(15):
            _recipe_rate_limit.clear()  # Evitar rate limit para probar cuota
            payload = {
                "dispositivo_uuid": "device-quota-test",
                "nombre_receta": f"Receta {i}",
                "metodo": "Filtro",
                "dosis_cafe_g": 15.0,
                "agua_ml": 250.0,
            }
            res = self.client.post(
                "/api/v1/recetas",
                json=payload,
                headers={"X-App-Client-Key": APP_CLIENT_KEY}
            )
            self.assertEqual(res.status_code, 201)

        # La número 16 debe fallar por cuota
        _recipe_rate_limit.clear()
        res_16 = self.client.post(
            "/api/v1/recetas",
            json={
                "dispositivo_uuid": "device-quota-test",
                "nombre_receta": "Receta 16",
                "metodo": "Filtro",
                "dosis_cafe_g": 15.0,
                "agua_ml": 250.0,
            },
            headers={"X-App-Client-Key": APP_CLIENT_KEY}
        )
        self.assertEqual(res_16.status_code, 400)
        self.assertIn("cuota", res_16.json()["detail"].lower())

    def test_create_recipe_with_sca_cupping_attributes(self):
        payload = {
            "dispositivo_uuid": "device-cupping-test",
            "nombre_receta": "Cata Q-Grader Geisha",
            "metodo": "Catación SCA",
            "dosis_cafe_g": 8.25,
            "agua_ml": 150.0,
            "catacion_sca": {
                "fragancia_aroma": 8.5,
                "sabor": 8.75,
                "retrogusto": 8.25,
                "acidez": 8.5,
                "cuerpo": 8.0,
                "balance": 8.5,
                "uniformidad": 10.0,
                "taza_limpia": 10.0,
                "dulzor": 10.0,
                "puntaje_global": 8.75
            }
        }
        res = self.client.post(
            "/api/v1/recetas",
            json=payload,
            headers={"X-App-Client-Key": APP_CLIENT_KEY}
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIsNotNone(data["catacion_sca"])
        self.assertEqual(data["puntuacion_sca_total"], 89.25)
        self.assertEqual(data["catacion_sca"]["fragancia_aroma"], 8.5)
        self.assertEqual(data["catacion_sca"]["puntuacion_total_sca"], 89.25)


if __name__ == "__main__":
    unittest.main()

