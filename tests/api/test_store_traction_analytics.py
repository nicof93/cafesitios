import unittest
from fastapi.testclient import TestClient
from plataforma_backend import app
from db.database import Base, DatabaseManager, Tienda, Producto, Variante, InteraccionClic, PedidoWhatsApp
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from api.dependencies import get_db_session


class TestStoreTractionAnalytics(unittest.TestCase):
    """Valida los endpoints y cálculos de métricas de tracción comercial multi-tienda."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        def override_get_db_session():
            session = cls.TestingSessionLocal()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db_session] = override_get_db_session
        cls.client = TestClient(app)

        # Poblar datos de prueba
        with cls.TestingSessionLocal() as session:
            t1 = Tienda(
                nombre="Tostaduría Austral",
                url_base="https://austral.cl",
                activo=True,
                telefono_whatsapp="+56911111111",
            )
            t2 = Tienda(
                nombre="Café del Valle",
                url_base="https://delvalle.cl",
                activo=True,
                telefono_whatsapp="+56922222222",
            )
            session.add_all([t1, t2])
            session.commit()
            session.refresh(t1)
            session.refresh(t2)

            p1 = Producto(
                nombre="Geisha Austral",
                url_detalle="https://austral.cl/geisha",
                tienda_id=t1.id,
                activo=True,
                categoria="cafe",
            )
            p2 = Producto(
                nombre="Bourbon Valle",
                url_detalle="https://delvalle.cl/bourbon",
                tienda_id=t2.id,
                activo=True,
                categoria="cafe",
            )
            session.add_all([p1, p2])
            session.commit()
            session.refresh(p1)
            session.refresh(p2)

            # Interacciones: outbounds, favorites, compare
            i1 = InteraccionClic(producto_id=p1.id, tipo_evento="outbound_click", ip_hash="abc")
            i2 = InteraccionClic(producto_id=p1.id, tipo_evento="add_favorite", ip_hash="abc")
            i3 = InteraccionClic(producto_id=p1.id, tipo_evento="compare_view", ip_hash="abc")
            i4 = InteraccionClic(producto_id=p2.id, tipo_evento="outbound_click", ip_hash="def")
            session.add_all([i1, i2, i3, i4])

            # Pedidos WhatsApp
            w1 = PedidoWhatsApp(tienda_id=t1.id, dispositivo_uuid="test-uuid-1", monto_total_clp=35000, estado="iniciado", items=[])
            w2 = PedidoWhatsApp(tienda_id=t1.id, dispositivo_uuid="test-uuid-2", monto_total_clp=20000, estado="iniciado", items=[])
            session.add_all([w1, w2])
            session.commit()

            cls.t1_id = t1.id
            cls.t2_id = t2.id

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(cls.engine)

    def test_get_stores_traction_canonical(self):
        resp = self.client.get("/api/v1/administracion/tiendas/traccion")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("resumen_global", data)
        self.assertIn("tiendas", data)

        resumen = data["resumen_global"]
        self.assertEqual(resumen["total_clics_salientes"], 2)
        self.assertEqual(resumen["total_cafes_favoritos"], 1)
        self.assertEqual(resumen["total_en_matriz_comparativa"], 1)
        self.assertEqual(resumen["total_ventas_solicitadas_whatsapp_clp"], 55000)
        self.assertEqual(resumen["total_pedidos_recibidos_whatsapp"], 2)

    def test_get_stores_traction_alias_and_store_metrics(self):
        resp = self.client.get("/api/v1/admin/stores/traction")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        tiendas = {t["tienda_id"]: t for t in data["tiendas"]}

        self.assertIn(self.t1_id, tiendas)
        t1_data = tiendas[self.t1_id]
        self.assertEqual(t1_data["nombre"], "Tostaduría Austral")
        self.assertEqual(t1_data["clics_salientes"], 1)
        self.assertEqual(t1_data["cafes_favoritos"], 1)
        self.assertEqual(t1_data["en_matriz_comparativa"], 1)
        self.assertEqual(t1_data["ventas_solicitadas_whatsapp_clp"], 55000)
        self.assertEqual(t1_data["pedidos_recibidos_whatsapp"], 2)
        self.assertEqual(t1_data["ticket_promedio_whatsapp_clp"], 27500.0)

        self.assertIn(self.t2_id, tiendas)
        t2_data = tiendas[self.t2_id]
        self.assertEqual(t2_data["clics_salientes"], 1)
        self.assertEqual(t2_data["cafes_favoritos"], 0)
        self.assertEqual(t2_data["en_matriz_comparativa"], 0)
        self.assertEqual(t2_data["ventas_solicitadas_whatsapp_clp"], 0)
        self.assertEqual(t2_data["pedidos_recibidos_whatsapp"], 0)


if __name__ == "__main__":
    unittest.main()

