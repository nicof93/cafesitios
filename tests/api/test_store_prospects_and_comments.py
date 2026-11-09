import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db_session
from db.database import Base, Tienda, TiendaCatalogo, TiendaComentario
from plataforma_backend import app


class TestStoreProspectsAndComments(unittest.TestCase):
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

    def tearDown(self):
        self.db.close()
        app.dependency_overrides.clear()

    def test_create_prospect_store_without_catalogs_success(self):
        payload = {
            "nombre": "Tostaduría Prospecto Sur",
            "es_prospecto": True,
            "activo": False,
            "contacto_nombre": "Carlos Rojas",
            "contacto_telefono": "+56912345678",
            "contacto_email": "carlos@prospecto.cl",
            "comuna": "Valdivia",
            "direccion": "Costanera 450",
            "catalogos": [],
        }
        resp = self.client.post("/api/v1/administracion/tiendas", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["nombre"], "Tostaduría Prospecto Sur")
        self.assertTrue(data["es_prospecto"])
        self.assertFalse(data["activo"])
        self.assertEqual(data["contacto_nombre"], "Carlos Rojas")
        self.assertEqual(data["contacto_telefono"], "+56912345678")
        self.assertEqual(data["contacto_email"], "carlos@prospecto.cl")
        self.assertEqual(len(data["catalogos"]), 0)

        # Verificar en base de datos
        store_id = data["id"]
        store_db = self.db.get(Tienda, store_id)
        self.assertIsNotNone(store_db)
        self.assertTrue(store_db.es_prospecto)
        self.assertFalse(store_db.activo)
        self.assertEqual(len(store_db.catalogos), 0)

    def test_create_active_store_without_catalogs_fails_with_400(self):
        payload = {
            "nombre": "Tienda Invalida Sin Catalogo",
            "es_prospecto": False,
            "activo": True,
            "catalogos": [],
        }
        resp = self.client.post("/api/v1/administracion/tiendas", json=payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("URL de catálogo", resp.json()["detail"])

    def test_list_stores_includes_prospect_and_comments_count(self):
        # Crear 1 tienda activa con catálogo y 1 prospecto
        tienda_activa = Tienda(
            id=1,
            nombre="Tostaduría Alfa",
            url_base="https://alfa.cl",
            activo=True,
            es_prospecto=False,
        )
        cat = TiendaCatalogo(tienda_id=1, url_catalogo="https://alfa.cl/cafe", activa=True)
        tienda_prospecto = Tienda(
            id=2,
            nombre="Tostaduría Beta Prospecto",
            url_base="",
            activo=False,
            es_prospecto=True,
            contacto_nombre="Marcela",
        )
        # Añadir 2 comentarios a la tienda prospecto
        c1 = TiendaComentario(
            tienda_id=2,
            autor="Admin",
            tipo_contacto="llamada",
            comentario="Hablé con Marcela, llamó interesada.",
        )
        c2 = TiendaComentario(
            tienda_id=2,
            autor="Admin",
            tipo_contacto="whatsapp",
            comentario="Le envié tarifario por WhatsApp.",
        )
        self.db.add_all([tienda_activa, cat, tienda_prospecto, c1, c2])
        self.db.commit()

        resp = self.client.get("/api/v1/administracion/tiendas")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_tiendas"], 2)

        items_by_id = {t["id"]: t for t in data["tiendas"]}
        self.assertFalse(items_by_id[1]["es_prospecto"])
        self.assertEqual(items_by_id[1]["total_comentarios"], 0)

        self.assertTrue(items_by_id[2]["es_prospecto"])
        self.assertEqual(items_by_id[2]["contacto_nombre"], "Marcela")
        self.assertEqual(items_by_id[2]["total_comentarios"], 2)

        # Prospectos inactivos no deben inflar 'total_pendientes' de sincronización
        self.assertEqual(data["total_pendientes"], 1)

    def test_store_comments_crud_lifecycle(self):
        store = Tienda(id=10, nombre="Café Central", url_base="https://central.cl", activo=True)
        self.db.add(store)
        self.db.commit()

        # 1. Crear comentario
        resp_post = self.client.post(
            "/api/v1/administracion/tiendas/10/comentarios",
            json={
                "tipo_contacto": "llamada",
                "comentario": "Llamé al dueño, pidió llamarlo después de las 18:00.",
                "autor": "Superadmin",
            },
        )
        self.assertEqual(resp_post.status_code, 201)
        comment_data = resp_post.json()
        self.assertEqual(comment_data["tienda_id"], 10)
        self.assertEqual(comment_data["tipo_contacto"], "llamada")
        self.assertEqual(comment_data["autor"], "Superadmin")
        self.assertIn("después de las 18:00", comment_data["comentario"])
        comment_id = comment_data["id"]

        # 2. Listar comentarios
        resp_list = self.client.get("/api/v1/administracion/tiendas/10/comentarios")
        self.assertEqual(resp_list.status_code, 200)
        list_data = resp_list.json()
        self.assertEqual(list_data["total"], 1)
        self.assertEqual(list_data["tienda_nombre"], "Café Central")
        self.assertEqual(list_data["comentarios"][0]["id"], comment_id)

        # 3. Probar alias en inglés
        resp_alias = self.client.get("/api/v1/admin/stores/10/comments")
        self.assertEqual(resp_alias.status_code, 200)
        self.assertEqual(resp_alias.json()["total"], 1)

        # 4. Eliminar comentario
        resp_del = self.client.delete(f"/api/v1/administracion/tiendas/10/comentarios/{comment_id}")
        self.assertEqual(resp_del.status_code, 200)
        self.assertEqual(resp_del.json()["status"], "ok")

        # 5. Verificar lista vacía
        resp_list_after = self.client.get("/api/v1/administracion/tiendas/10/comentarios")
        self.assertEqual(resp_list_after.json()["total"], 0)

    def test_multi_tenant_isolation_comments_not_exposed_in_store_admin(self):
        # El portal de tiendas nunca debe exponer los comentarios confidenciales del superadmin
        resp = self.client.get("/api/v1/admin-tienda/tiendas/10/comentarios")
        self.assertIn(resp.status_code, [404, 405])


if __name__ == "__main__":
    unittest.main()
