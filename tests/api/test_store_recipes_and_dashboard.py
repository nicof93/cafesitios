import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from api.dependencies import get_db_session
from db.database import Base, Tienda, Producto, Variante, Receta, UsuarioTienda
from core.security_store_admin import create_store_admin_token


class TestStoreRecipesAndDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
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

        app.dependency_overrides[get_db_session] = override_get_db
        cls.client = TestClient(app)
        from plataforma_backend import app as plataforma_app
        plataforma_app.dependency_overrides[get_db_session] = override_get_db
        cls.plataforma_client = TestClient(plataforma_app)
        session = cls.SessionLocal()
        try:
            # Crear o buscar tienda de prueba
            tienda = session.query(Tienda).filter(Tienda.nombre == "Tostaduría Recetas Test").first()
            if not tienda:
                tienda = Tienda(
                    nombre="Tostaduría Recetas Test",
                    url_base="https://recetastest.cl",
                    plataforma="woocommerce",
                    activo=True,
                )
                session.add(tienda)
                session.flush()

            cls.tienda_id = tienda.id

            # Producto de prueba
            producto = session.query(Producto).filter(
                Producto.tienda_id == cls.tienda_id,
                Producto.nombre == "Café Geisha Especial Receta"
            ).first()
            if not producto:
                producto = Producto(
                    tienda_id=cls.tienda_id,
                    nombre="Café Geisha Especial Receta",
                    url_detalle="https://recetastest.cl/geisha",
                    categoria="cafe",
                    activo=True,
                    oculto_catalogo=False,
                )
                session.add(producto)
                session.flush()

                variante = Variante(
                    producto_id=producto.id,
                    id_variante_externo="geisha-250",
                    opcion="250g",
                    formato_gramos=250,
                    precio_clp=15000,
                    precio_original_clp=15000,
                    precio_por_kilo=60000.0,
                    disponible=True,
                )
                session.add(variante)
            else:
                producto.activo = True
                producto.oculto_catalogo = False
                session.flush()

            cls.producto_id = producto.id

            # Usuario Store Admin
            usuario = session.query(UsuarioTienda).filter(
                UsuarioTienda.tienda_id == cls.tienda_id,
                UsuarioTienda.usuario_id == "admin@recetastest.cl"
            ).first()
            if not usuario:
                usuario = UsuarioTienda(
                    tienda_id=cls.tienda_id,
                    usuario_id="admin@recetastest.cl",
                    rol="STORE_ADMIN",
                )
                session.add(usuario)

            session.commit()
            cls.token = create_store_admin_token(
                tienda_id=cls.tienda_id,
                usuario_id="admin@recetastest.cl",
                rol="STORE_ADMIN"
            )
        finally:
            session.close()

    def test_01_dashboard_admin_status_fields(self):
        headers = {"X-Admin-Role": "SUPER_ADMIN"}
        resp = self.plataforma_client.get("/api/v1/administracion/estado", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("productos_sin_moderar", data)
        self.assertIn("tiendas_resumen", data)
        self.assertIsInstance(data["tiendas_resumen"], list)

        if data["tiendas_resumen"]:
            first_store = data["tiendas_resumen"][0]
            self.assertIn("nombre", first_store)
            self.assertIn("estado_ultimo", first_store)
            self.assertIn("fecha_ultimo", first_store)
            self.assertIn("ultima_sincronizacion_exitosa", first_store)
            self.assertIn("detalle_error", first_store)

    def test_02_store_admin_create_and_list_recipe(self):
        headers = {"Authorization": f"Bearer {self.token}"}

        # 1. Crear receta
        payload = {
            "producto_id": self.producto_id,
            "nombre_receta": "V60 Tueste Ligero Recomendado",
            "metodo": "V60",
            "dosis_cafe_g": 18.0,
            "agua_ml": 270.0,
            "ratio": "1:15",
            "temperatura_c": 93,
            "tiempo_total_s": 170,
            "grosor_molienda": "Media-Fina",
            "molino_usado": "Comandante 22 clicks",
            "notas_catado": "Resalta notas a jazmín y durazno",
        }
        res_create = self.client.post("/api/v1/admin/tienda/recetas", json=payload, headers=headers)
        self.assertEqual(res_create.status_code, 201)
        created_data = res_create.json()
        self.assertEqual(created_data["nombre_receta"], "V60 Tueste Ligero Recomendado")
        self.assertEqual(created_data["producto_id"], self.producto_id)
        receta_id = created_data["id"]

        # 2. Listar recetas de la tienda
        res_list = self.client.get("/api/v1/admin/tienda/recetas", headers=headers)
        self.assertEqual(res_list.status_code, 200)
        recipes = res_list.json()
        self.assertTrue(any(r["id"] == receta_id for r in recipes))

        # 3. Consultar detalle público del producto para ver que la receta se expone
        res_detail = self.client.get(f"/api/v1/productos/{self.producto_id}/detalle")
        self.assertEqual(res_detail.status_code, 200)
        detail_data = res_detail.json()
        self.assertIn("recetas", detail_data)
        self.assertTrue(any(r["id"] == receta_id for r in detail_data["recetas"]))
        first_r = next(r for r in detail_data["recetas"] if r["id"] == receta_id)
        self.assertEqual(first_r["metodo"], "V60")
        self.assertEqual(first_r["dosis_cafe_g"], 18.0)
        self.assertEqual(first_r["agua_ml"], 270.0)

        # 4. Eliminar receta
        res_del = self.client.delete(f"/api/v1/admin/tienda/recetas/{receta_id}", headers=headers)
        self.assertEqual(res_del.status_code, 200)

    def test_03_draft_recipe_isolation_and_steps(self):
        headers = {"Authorization": f"Bearer {self.token}"}

        # 1. Crear receta en borrador con pasos
        payload = {
            "producto_id": self.producto_id,
            "nombre_receta": "Receta Borrador Aeropress",
            "metodo": "Aeropress",
            "dosis_cafe_g": 15.0,
            "agua_ml": 220.0,
            "ratio": "1:14.6",
            "temperatura_c": 88,
            "tiempo_total_s": 120,
            "es_borrador": True,
            "pasos": [
                "Paso 1: Colocar filtro de papel y enjuagar",
                "Paso 2: Verter 50ml y esperar 30s de blooming",
                "Paso 3: Verter hasta 220ml y presionar a los 1:45 min",
            ],
        }
        res_create = self.client.post("/api/v1/admin/tienda/recetas", json=payload, headers=headers)
        self.assertEqual(res_create.status_code, 201)
        created_data = res_create.json()
        self.assertTrue(created_data["es_borrador"])
        self.assertEqual(len(created_data["pasos"]), 3)
        draft_id = created_data["id"]

        try:
            # 2. El administrador de la tienda SÍ puede ver su borrador
            res_list = self.client.get("/api/v1/admin/tienda/recetas", headers=headers)
            self.assertEqual(res_list.status_code, 200)
            recipes = res_list.json()
            matching = [r for r in recipes if r["id"] == draft_id]
            self.assertEqual(len(matching), 1)
            self.assertTrue(matching[0]["es_borrador"])
            self.assertEqual(len(matching[0]["pasos"]), 3)

            # 3. La ficha pública NO debe mostrar la receta en borrador
            res_detail = self.client.get(f"/api/v1/productos/{self.producto_id}/detalle")
            self.assertEqual(res_detail.status_code, 200)
            detail_data = res_detail.json()
            public_recipes = detail_data.get("recetas", [])
            self.assertFalse(any(r["id"] == draft_id for r in public_recipes))

            res_pub_recipes = self.client.get(f"/api/v1/productos/{self.producto_id}/recetas")
            self.assertEqual(res_pub_recipes.status_code, 200)
            self.assertFalse(any(r["id"] == draft_id for r in res_pub_recipes.json()))
        finally:
            # Cleanup
            self.client.delete(f"/api/v1/admin/tienda/recetas/{draft_id}", headers=headers)

    def test_04_change_store_admin_password(self):
        headers = {"Authorization": f"Bearer {self.token}"}

        # Cambiar contraseña
        change_payload = {
            "password_nuevo": "NuevoPasswordSeguro2026!"
        }
        res_change = self.client.post("/api/v1/admin/tienda/auth/cambiar-password", json=change_payload, headers=headers)
        self.assertEqual(res_change.status_code, 200)
        data = res_change.json()
        self.assertTrue(data.get("exito"))


    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(get_db_session, None)
        cls.engine.dispose()


if __name__ == '__main__':
    unittest.main()

