import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, InteraccionClic, Tienda, Producto, Variante
from api.admin import calcular_traccion_tiendas_global
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

    def test_record_frontend_event_format_with_nested_product_id(self):
        payload = {
            "event_type": "outbound_click",
            "metadata": {
                "store_name": "Taller Café",
                "product_name": "Geisha Panamá",
                "product_id": 42,
                "price": 18990,
                "destination_url": "https://tallercafe.cl/p/geisha"
            }
        }
        res = self.client.post("/api/v1/telemetry/event", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "ok")

        db = self.TestingSessionLocal()
        inter = db.query(InteraccionClic).filter(InteraccionClic.id == data["event_id"]).first()
        self.assertIsNotNone(inter)
        self.assertEqual(inter.tipo_evento, "outbound_click")
        self.assertEqual(inter.producto_id, 42)
        db.close()

    def test_traction_metrics_counts_interactions_correctly(self):
        db = self.TestingSessionLocal()
        tienda = Tienda(nombre="Café Demo", url_base="https://cafedemo.cl", activo=True)
        db.add(tienda)
        db.commit()
        db.refresh(tienda)

        prod = Producto(
            tienda_id=tienda.id,
            nombre="Café Especial Etiopía",
            url_detalle="https://cafedemo.cl/etiopia",
            activo=True
        )
        db.add(prod)
        db.commit()
        db.refresh(prod)

        # 1. Enviar evento outbound_click
        res1 = self.client.post(
            "/api/v1/telemetry/event",
            json={
                "event_type": "outbound_click",
                "metadata": {"product_id": prod.id, "store_name": "Café Demo"}
            }
        )
        self.assertEqual(res1.status_code, 201)

        # 2. Enviar evento add_to_favorites
        res2 = self.client.post(
            "/api/v1/telemetry/event",
            json={
                "event_type": "add_to_favorites",
                "metadata": {"item_id": prod.id, "store_name": "Café Demo"}
            }
        )
        self.assertEqual(res2.status_code, 201)

        # 3. Enviar evento add_to_compare
        res3 = self.client.post(
            "/api/v1/telemetry/event",
            json={
                "event_type": "add_to_compare",
                "metadata": {"product_id": prod.id, "product_name": "Café Especial Etiopía"}
            }
        )
        self.assertEqual(res3.status_code, 201)

        # 4. Calcular tracción comercial
        traccion = calcular_traccion_tiendas_global(db)
        self.assertEqual(traccion.resumen_global.total_clics_salientes, 1)
        self.assertEqual(traccion.resumen_global.total_cafes_favoritos, 1)
        self.assertEqual(traccion.resumen_global.total_en_matriz_comparativa, 1)

        item = next((t for t in traccion.tiendas if t.tienda_id == tienda.id), None)
        self.assertIsNotNone(item)
        self.assertEqual(item.clics_salientes, 1)
        self.assertEqual(item.cafes_favoritos, 1)
        self.assertEqual(item.en_matriz_comparativa, 1)

        # 5. Tienda inactiva o eliminada no debe aparecer en reporte de tracción
        tienda_inactiva = Tienda(nombre="Tienda Inactiva", url_base="https://inactiva.cl", activo=False)
        db.add(tienda_inactiva)
        db.commit()

        traccion_post = calcular_traccion_tiendas_global(db)
        ids_tiendas = [t.tienda_id for t in traccion_post.tiendas]
        self.assertNotIn(tienda_inactiva.id, ids_tiendas)

        db.close()
        db.close()


if __name__ == "__main__":
    unittest.main()

