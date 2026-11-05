import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db_session
from core.security_store_admin import create_store_admin_token
from db.database import Base, Producto, Tienda, Variante
from main import app


class TestHiddenProductPreview(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # Seed stores
        self.store1 = Tienda(
            id=1,
            nombre="Tostaduría Alfa",
            url_base="https://alfa.cl",
            activo=True,
        )
        self.store2 = Tienda(
            id=2,
            nombre="Tostaduría Beta",
            url_base="https://beta.cl",
            activo=True,
        )
        self.db.add_all([self.store1, self.store2])
        self.db.commit()

        # Seed products: prod 10 is hidden in store 1, prod 20 is visible in store 1
        self.prod_hidden = Producto(
            id=10,
            tienda_id=1,
            nombre="Geisha Oculto Alfa",
            url_detalle="https://alfa.cl/geisha",
            activo=True,
            oculto_catalogo=True,
        )
        self.db.add(self.prod_hidden)
        self.db.flush()

        self.var1 = Variante(
            id=101,
            producto_id=10,
            id_variante_externo="var-ext-101",
            opcion="Grano entero",
            formato_gramos=250,
            precio_clp=18000,
            precio_original_clp=18000,
            precio_por_kilo=72000,
            disponible=True,
        )
        self.db.add(self.var1)
        self.db.commit()

        # Generate tokens
        self.token_store1 = create_store_admin_token(usuario_id="user-1", tienda_id=1)
        self.token_store2 = create_store_admin_token(usuario_id="user-2", tienda_id=2)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db_session] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_hidden_product_without_token_returns_404(self):
        res = self.client.get("/api/v1/products/10/detail")
        self.assertEqual(res.status_code, 404)

    def test_hidden_product_with_invalid_token_returns_404(self):
        res = self.client.get("/api/v1/products/10/detail?preview_token=token_invalido_xyz")
        self.assertEqual(res.status_code, 404)

    def test_hidden_product_with_other_store_token_returns_404(self):
        res = self.client.get(f"/api/v1/products/10/detail?preview_token={self.token_store2}")
        self.assertEqual(res.status_code, 404)

    def test_hidden_product_with_owner_store_preview_token_returns_200(self):
        res = self.client.get(f"/api/v1/products/10/detail?preview_token={self.token_store1}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], 10)
        self.assertEqual(data["nombre"], "Geisha Oculto Alfa")
        self.assertTrue(data["oculto_catalogo"])

    def test_hidden_product_with_header_preview_token_returns_200(self):
        res = self.client.get(
            "/api/v1/products/10/detail",
            headers={"X-Preview-Token": self.token_store1}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], 10)

    def test_hidden_product_with_authorization_header_returns_200(self):
        res = self.client.get(
            "/api/v1/products/10/detail",
            headers={"Authorization": f"Bearer {self.token_store1}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], 10)



    def test_inactive_product_without_token_returns_404(self):
        prod_inactive = Producto(
            id=11,
            tienda_id=1,
            nombre="Caturra Inactivo Alfa",
            url_detalle="https://alfa.cl/caturra",
            activo=False,
            oculto_catalogo=False,
        )
        self.db.add(prod_inactive)
        self.db.flush()
        var = Variante(
            id=102,
            producto_id=11,
            id_variante_externo="var-ext-102",
            opcion="Grano entero",
            formato_gramos=250,
            precio_clp=12000,
            precio_original_clp=12000,
            precio_por_kilo=48000,
            disponible=True,
        )
        self.db.add(var)
        self.db.commit()

        res = self.client.get("/api/v1/products/11/detail")
        self.assertEqual(res.status_code, 404)

    def test_inactive_product_with_owner_token_returns_200(self):
        prod_inactive = Producto(
            id=12,
            tienda_id=1,
            nombre="Bourbon Inactivo Alfa",
            url_detalle="https://alfa.cl/bourbon",
            activo=False,
            oculto_catalogo=True,
        )
        self.db.add(prod_inactive)
        self.db.flush()
        var = Variante(
            id=103,
            producto_id=12,
            id_variante_externo="var-ext-103",
            opcion="Grano entero",
            formato_gramos=250,
            precio_clp=15000,
            precio_original_clp=15000,
            precio_por_kilo=60000,
            disponible=True,
        )
        self.db.add(var)
        self.db.commit()

        res = self.client.get(f"/api/v1/products/12/detail?preview_token={self.token_store1}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], 12)
        self.assertFalse(data["activo"])
        self.assertTrue(data["oculto_catalogo"])

    def test_inactive_store_product_with_owner_token_returns_200(self):
        store_inactive = Tienda(
            id=3,
            nombre="Tostaduría Inactiva Gamma",
            url_base="https://gamma.cl",
            activo=False,
        )
        self.db.add(store_inactive)
        self.db.flush()
        prod = Producto(
            id=30,
            tienda_id=3,
            nombre="Pacamara Gamma",
            url_detalle="https://gamma.cl/pacamara",
            activo=False,
            oculto_catalogo=False,
        )
        self.db.add(prod)
        self.db.flush()
        var = Variante(
            id=104,
            producto_id=30,
            id_variante_externo="var-ext-104",
            opcion="Grano entero",
            formato_gramos=250,
            precio_clp=14000,
            precio_original_clp=14000,
            precio_por_kilo=56000,
            disponible=True,
        )
        self.db.add(var)
        self.db.commit()

        token_gamma = create_store_admin_token(usuario_id="user-gamma", tienda_id=3)
        res = self.client.get(f"/api/v1/products/30/detail?preview_token={token_gamma}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], 30)

        # Without token, should be 404
        res_no_tok = self.client.get("/api/v1/products/30/detail")
        self.assertEqual(res_no_tok.status_code, 404)

    def test_platform_superadmin_can_preview_any_product(self):
        token_super = create_store_admin_token(
            usuario_id="super-1",
            tienda_id=None,
            rol="PLATFORM_SUPERADMIN"
        )
        res = self.client.get(f"/api/v1/products/10/detail?preview_token={token_super}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], 10)


if __name__ == "__main__":
    unittest.main()
