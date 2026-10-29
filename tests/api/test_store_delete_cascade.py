import os
import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["ENVIRONMENT"] = "testing"

from api.dependencies import get_db_session, require_local_admin
from db.database import (
    Base,
    HistorialPrecio,
    InteraccionClic,
    PedidoWhatsApp,
    Producto,
    Receta,
    Sincronizacion,
    SucursalTienda,
    Tienda,
    TiendaCatalogo,
    Variante,
)
from plataforma_backend import app


class TestStoreDeleteCascade(unittest.TestCase):
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

    def test_delete_store_not_found(self):
        response = self.client.delete("/api/v1/administracion/tiendas/999999")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("Tienda no encontrada", data.get("detail", ""))

    def test_delete_store_cascade_success(self):
        # 1. Crear Tienda A (la que eliminaremos)
        store_a = Tienda(
            nombre="Tostaduría Para Eliminar",
            url_base="https://eliminar.cl",
            plataforma="shopify",
            activo=True,
        )
        # Tienda B (para asegurar aislamiento)
        store_b = Tienda(
            nombre="Tostaduría Que Sobrevive",
            url_base="https://sobrevive.cl",
            plataforma="woocommerce",
            activo=True,
        )
        self.db.add_all([store_a, store_b])
        self.db.commit()
        self.db.refresh(store_a)
        self.db.refresh(store_b)

        store_a_id = store_a.id
        store_b_id = store_b.id

        # 2. Agregar datos relacionales a Tienda A
        sucursal = SucursalTienda(tienda_id=store_a_id, nombre="Casa Matriz")
        catalogo = TiendaCatalogo(tienda_id=store_a_id, url_catalogo="https://eliminar.cl/products.json")
        sync = Sincronizacion(
            tienda_id=store_a_id,
            fecha_inicio=datetime.now(timezone.utc),
            resultado="EXITOSO",
            productos_agregados=1,
        )
        self.db.add_all([sucursal, catalogo, sync])
        self.db.commit()

        prod_a = Producto(
            tienda_id=store_a_id,
            nombre="Café Etiopía Guji",
            url_detalle="https://eliminar.cl/cafe-etiopia",
            categoria="cafe_grano",
            activo=True,
        )
        prod_b = Producto(
            tienda_id=store_b_id,
            nombre="Café Colombia Geisha",
            url_detalle="https://sobrevive.cl/cafe-geisha",
            categoria="cafe_grano",
            activo=True,
        )
        self.db.add_all([prod_a, prod_b])
        self.db.commit()
        self.db.refresh(prod_a)
        self.db.refresh(prod_b)

        prod_a_id = prod_a.id
        prod_b_id = prod_b.id

        var_a = Variante(
            producto_id=prod_a_id,
            id_variante_externo="var-ext-1234",
            opcion="250g Grano",
            precio_clp=12990,
            precio_original_clp=12990,
            formato_gramos=250,
            precio_por_kilo=51960.0,
            disponible=True,
        )
        self.db.add(var_a)
        self.db.commit()
        self.db.refresh(var_a)

        var_a_id = var_a.id

        hist = HistorialPrecio(
            variante_id=var_a_id,
            precio_clp=12990,
            precio_original_clp=12990,
            precio_por_kilo=51960.0,
        )
        clic_prod = InteraccionClic(producto_id=prod_a_id, tipo_evento="click_outbound", ip_hash="abc")
        clic_var = InteraccionClic(variante_id=var_a_id, tipo_evento="click_outbound", ip_hash="abc")
        pedido = PedidoWhatsApp(
            tienda_id=store_a_id,
            items=[{"nombre": "Café Etiopía"}],
            monto_total_clp=12990,
            dispositivo_uuid="test-uuid",
        )
        receta = Receta(
            tienda_id=store_a_id,
            producto_id=prod_a_id,
            nombre_receta="V60 Etiopía",
            metodo="V60",
            dosis_cafe_g=15,
            agua_ml=250,
            dispositivo_uuid="test-uuid",
        )
        self.db.add_all([hist, clic_prod, clic_var, pedido, receta])
        self.db.commit()

        # Expulsar objetos cacheados en sesión para comprobar estado limpio
        self.db.expire_all()

        # 3. Ejecutar DELETE
        response = self.client.delete(f"/api/v1/administracion/tiendas/{store_a_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("exito"))
        self.assertEqual(data.get("tienda_id"), store_a_id)

        # 4. Verificar que tienda A y sus dependencias ya no existen
        self.assertIsNone(self.db.scalars(select(Tienda).where(Tienda.id == store_a_id)).first())
        self.assertIsNone(self.db.scalars(select(Producto).where(Producto.id == prod_a_id)).first())
        self.assertIsNone(self.db.scalars(select(Variante).where(Variante.id == var_a_id)).first())
        self.assertIsNone(self.db.scalars(select(SucursalTienda).where(SucursalTienda.tienda_id == store_a_id)).first())
        self.assertIsNone(self.db.scalars(select(TiendaCatalogo).where(TiendaCatalogo.tienda_id == store_a_id)).first())
        self.assertIsNone(self.db.scalars(select(Sincronizacion).where(Sincronizacion.tienda_id == store_a_id)).first())
        self.assertIsNone(self.db.scalars(select(PedidoWhatsApp).where(PedidoWhatsApp.tienda_id == store_a_id)).first())

        # 5. Verificar que tienda B sigue intacta
        self.assertIsNotNone(self.db.scalars(select(Tienda).where(Tienda.id == store_b_id)).first())
        self.assertIsNotNone(self.db.scalars(select(Producto).where(Producto.id == prod_b_id)).first())


if __name__ == "__main__":
    unittest.main()
