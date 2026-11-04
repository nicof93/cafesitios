import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db_session
from db.database import Base, Producto, Tienda, Variante
from plataforma_backend import app


class TestModerationStoreFilter(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db_session] = override_get_db
        self.client = TestClient(app)

        # Tienda A
        self.store_a = Tienda(id=1, nombre="Tostaduría Alfa", url_base="https://alfa.cl", activo=True)
        # Tienda B
        self.store_b = Tienda(id=2, nombre="Tostaduría Beta", url_base="https://beta.cl", activo=True)
        self.db.add_all([self.store_a, self.store_b])
        self.db.commit()

        # Productos Tienda A:
        # 1 visible café, 1 sospechoso no-café (polera), 1 oculto
        prod_a1 = Producto(id=10, tienda_id=1, nombre="Café Etiopía Yirgacheffe", url_detalle="https://alfa.cl/etiopia", activo=True, oculto_catalogo=False)
        prod_a2 = Producto(id=11, tienda_id=1, nombre="Polera Barista Unisex", url_detalle="https://alfa.cl/polera", activo=True, oculto_catalogo=False)
        prod_a3 = Producto(id=12, tienda_id=1, nombre="Taza Cerámica", url_detalle="https://alfa.cl/taza", activo=True, oculto_catalogo=True)

        # Productos Tienda B:
        # 2 visibles café
        prod_b1 = Producto(id=20, tienda_id=2, nombre="Café Colombia Huila", url_detalle="https://beta.cl/huila", activo=True, oculto_catalogo=False)
        prod_b2 = Producto(id=21, tienda_id=2, nombre="Café Kenia Nyeri", url_detalle="https://beta.cl/kenia", activo=True, oculto_catalogo=False)

        self.db.add_all([prod_a1, prod_a2, prod_a3, prod_b1, prod_b2])
        self.db.commit()

        # Variantes mínimas
        for p_id in [10, 11, 12, 20, 21]:
            var = Variante(
                id=p_id * 10,
                producto_id=p_id,
                id_variante_externo=f"var-{p_id}",
                opcion="Grano",
                formato_gramos=250,
                precio_clp=10000,
                precio_original_clp=10000,
                precio_por_kilo=40000,
                disponible=True,
            )
            self.db.add(var)
        self.db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_moderation_without_filter_returns_global_totals(self):
        res = self.client.get("/api/v1/admin/products/moderation?mode=all")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Global: 3 visibles café (a1, b1, b2), 1 sospechoso no-café visible (a2), 1 oculto (a3)
        self.assertEqual(data["total_sospechosos"], 1)
        self.assertEqual(data["total_ocultos"], 1)
        self.assertEqual(data["total_visibles_cafe"], 3)
        self.assertEqual(len(data["items"]), 5)

    def test_moderation_filtered_by_store_a_restricts_kpis_and_items(self):
        res = self.client.get("/api/v1/admin/products/moderation?mode=all&store_name=Tostaduría Alfa")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Solo Tienda A: 1 visible café, 1 sospechoso no-café, 1 oculto
        self.assertEqual(data["total_sospechosos"], 1)
        self.assertEqual(data["total_ocultos"], 1)
        self.assertEqual(data["total_visibles_cafe"], 1)
        self.assertEqual(len(data["items"]), 3)
        for item in data["items"]:
            self.assertEqual(item["tienda"], "Tostaduría Alfa")

    def test_moderation_filtered_by_store_b_restricts_kpis_and_items(self):
        res = self.client.get("/api/v1/admin/products/moderation?mode=all&store_name=Beta")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Solo Tienda B: 2 visibles café, 0 sospechosos, 0 ocultos
        self.assertEqual(data["total_sospechosos"], 0)
        self.assertEqual(data["total_ocultos"], 0)
        self.assertEqual(data["total_visibles_cafe"], 2)
        self.assertEqual(len(data["items"]), 2)
        for item in data["items"]:
            self.assertEqual(item["tienda"], "Tostaduría Beta")


if __name__ == "__main__":
    unittest.main()

