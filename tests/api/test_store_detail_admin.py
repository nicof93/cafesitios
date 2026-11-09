import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app_plataforma import create_plataforma_app
from api.app_public import create_public_app
from api.dependencies import get_db_session
from db.database import (
    Base,
    PlanTienda,
    SucursalTienda,
    Tienda,
    TiendaCatalogo,
    TiendaComentario,
    UsuarioTienda,
)


class TestStoreDetailAdmin(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        self.app_plataforma = create_plataforma_app()
        self.app_public = create_public_app()

        def override_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        self.app_plataforma.dependency_overrides[get_db_session] = override_db
        self.app_public.dependency_overrides[get_db_session] = override_db
        self.client = TestClient(self.app_plataforma)
        self.public_client = TestClient(self.app_public)

    def tearDown(self):
        self.engine.dispose()

    def test_get_store_detail_success(self):
        with self.SessionLocal() as session:
            plan = PlanTienda(
                codigo="tostador_pro",
                nombre="Plan Tostador Pro",
                precio_mensual_clp=25000,
                descripcion="Plan avanzado para tostadurías",
                limite_almacenamiento_mb=500,
                funcionalidades={"recetas": True, "whatsapp": True},
                activo=True,
            )
            session.add(plan)
            session.flush()

            tienda = Tienda(
                nombre="Tostaduría Altura",
                url_base="https://altura.cl",
                plataforma="shopify_json",
                activo=True,
                es_prospecto=False,
                direccion="Av. Providencia 1234",
                comuna="Providencia",
                latitud=-33.42,
                longitud=-70.61,
                telefono_whatsapp="+56911223344",
                contacto_nombre="Carlos Tostador",
                contacto_telefono="+56911223344",
                contacto_email="carlos@altura.cl",
                plan_id=plan.id,
                dia_pago_mensual=5,
                precio_acordado_clp=25000,
                estado_pago="al_dia",
            )
            session.add(tienda)
            session.flush()

            cat = TiendaCatalogo(
                tienda_id=tienda.id,
                url_catalogo="https://altura.cl/collections/cafe/products.json",
                etiqueta="Catálogo Café en Grano",
                activa=True,
            )
            session.add(cat)

            suc1 = SucursalTienda(
                tienda_id=tienda.id,
                nombre="Casa Matriz Providencia",
                direccion="Av. Providencia 1234",
                comuna="Providencia",
                latitud=-33.425,
                longitud=-70.615,
                activo=True,
            )
            suc2 = SucursalTienda(
                tienda_id=tienda.id,
                nombre="Cafetería El Golf",
                direccion="Isidora Goyenechea 3000",
                comuna="Las Condes",
                latitud=-33.415,
                longitud=-70.598,
                activo=True,
            )
            session.add_all([suc1, suc2])

            nota1 = TiendaComentario(
                tienda_id=tienda.id,
                autor="Superadmin",
                tipo_contacto="llamada",
                comentario="Hablamos con Carlos, acordamos reunión para revisar facturación el martes.",
                fecha_creacion=datetime.now(timezone.utc),
            )
            nota2 = TiendaComentario(
                tienda_id=tienda.id,
                autor="Admin Ventas",
                tipo_contacto="whatsapp",
                comentario="Enviada propuesta comercial por WhatsApp.",
                fecha_creacion=datetime.now(timezone.utc),
            )
            session.add_all([nota1, nota2])
            session.commit()
            store_id = tienda.id

        # 1. Endpoint canónico en español
        resp = self.client.get(f"/api/v1/administracion/tiendas/{store_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["id"], store_id)
        self.assertEqual(data["nombre"], "Tostaduría Altura")
        self.assertEqual(data["plataforma"], "shopify_json")
        self.assertEqual(data["comuna"], "Providencia")
        self.assertEqual(data["contacto_nombre"], "Carlos Tostador")
        self.assertEqual(data["plan_nombre"], "Plan Tostador Pro")
        self.assertEqual(data["total_comentarios"], 2)

        # Verificar sucursales
        self.assertEqual(len(data["sucursales"]), 2)
        nombres_sucursales = [s["nombre"] for s in data["sucursales"]]
        self.assertIn("Casa Matriz Providencia", nombres_sucursales)
        self.assertIn("Cafetería El Golf", nombres_sucursales)

        # Verificar catálogos
        self.assertEqual(len(data["catalogos"]), 1)
        self.assertEqual(data["catalogos"][0]["etiqueta"], "Catálogo Café en Grano")

        # Verificar comentarios
        self.assertEqual(len(data["comentarios"]), 2)
        autores = [c["autor"] for c in data["comentarios"]]
        self.assertIn("Superadmin", autores)
        self.assertIn("Admin Ventas", autores)

    def test_get_store_detail_english_alias(self):
        with self.SessionLocal() as session:
            tienda = Tienda(
                nombre="Café Origen",
                url_base="https://cafeorigen.cl",
                plataforma="woocommerce_store_api",
                activo=True,
            )
            session.add(tienda)
            session.commit()
            store_id = tienda.id

        resp = self.client.get(f"/api/v1/admin/stores/{store_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], store_id)
        self.assertEqual(data["nombre"], "Café Origen")

    def test_get_store_detail_not_found(self):
        resp = self.client.get("/api/v1/administracion/tiendas/999999")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("no encontrada", resp.json()["detail"].lower())

    def test_get_store_detail_prospect(self):
        with self.SessionLocal() as session:
            prospecto = Tienda(
                nombre="Cafetería Prospecto Austral",
                url_base="",
                plataforma="manual",
                activo=False,
                es_prospecto=True,
                contacto_nombre="Fernanda Lagos",
                contacto_telefono="+56999887766",
                contacto_email="fernanda@austral.cl",
            )
            session.add(prospecto)
            session.commit()
            store_id = prospecto.id

        resp = self.client.get(f"/api/v1/administracion/tiendas/{store_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["es_prospecto"])
        self.assertFalse(data["activo"])
        self.assertEqual(data["contacto_nombre"], "Fernanda Lagos")
        self.assertEqual(data["catalogos"], [])
        self.assertEqual(data["sucursales"], [])

    def test_store_admin_isolation(self):
        resp = self.public_client.get("/api/v1/admin-tienda/tiendas/1")
        self.assertIn(resp.status_code, [404, 405])


if __name__ == "__main__":
    unittest.main()
