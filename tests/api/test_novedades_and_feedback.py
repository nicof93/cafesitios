from datetime import datetime, timezone
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app_plataforma import create_plataforma_app
from api.dependencies import get_db_session
from core.security_store_admin import create_store_admin_token
from db.config import settings
from db.database import Base, NovedadTienda, PlanTienda, SugerenciaFeedback, Tienda, UsuarioTienda
from main import app


class TestNovedadesAndFeedback(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # Seed Plans
        self.plan_basic = PlanTienda(
            id=1,
            nombre="Plan Básico",
            codigo="plan_basico",
            precio_mensual_clp=0,
            funcionalidades={"publicaciones_novedades": False},
            activo=True,
        )
        self.plan_pro = PlanTienda(
            id=2,
            nombre="Plan Pro",
            codigo="plan_pro",
            precio_mensual_clp=19990,
            funcionalidades={"publicaciones_novedades": True},
            activo=True,
        )
        self.db.add_all([self.plan_basic, self.plan_pro])
        self.db.commit()

        # Seed Stores
        self.store_basic = Tienda(
            id=1,
            nombre="Tostaduría Básica",
            url_base="https://basica.cl",
            plan_id=1,
            activo=True,
        )
        self.store_pro = Tienda(
            id=2,
            nombre="Tostaduría Pro",
            url_base="https://pro.cl",
            plan_id=2,
            activo=True,
        )
        self.db.add_all([self.store_basic, self.store_pro])
        self.db.commit()

        # Seed UsuariosTienda
        self.user_basic = UsuarioTienda(
            usuario_id="user-basic",
            tienda_id=1,
            rol="STORE_ADMIN",
        )
        self.user_pro = UsuarioTienda(
            usuario_id="user-pro",
            tienda_id=2,
            rol="STORE_ADMIN",
        )
        self.db.add_all([self.user_basic, self.user_pro])
        self.db.commit()

        # Tokens
        self.token_basic = create_store_admin_token(usuario_id="user-basic", tienda_id=1)
        self.token_pro = create_store_admin_token(usuario_id="user-pro", tienda_id=2)
        self.token_super = create_store_admin_token(usuario_id="super-1", tienda_id=None, rol="PLATFORM_SUPERADMIN")

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        self.admin_app = create_plataforma_app()
        app.dependency_overrides[get_db_session] = override_get_db
        self.admin_app.dependency_overrides[get_db_session] = override_get_db
        self.client = TestClient(app)
        self.admin_client = TestClient(self.admin_app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.admin_app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    # --- NOVEDADES PÚBLICAS ---

    def test_public_novedades_feed_and_pagination(self):
        # Seed 3 posts
        for i in range(1, 4):
            post = NovedadTienda(
                tienda_id=2,
                titulo=f"Feria Café #{i}",
                descripcion=f"Gran evento cafetero #{i} de especialidad.",
                categoria_tipo="evento" if i == 1 else "promocion",
                activo=True,
            )
            self.db.add(post)
        self.db.commit()

        # Feed general
        res = self.client.get("/api/v1/novedades?page=1&limit=2")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["items"]), 2)
        self.assertTrue(data["has_more"])
        self.assertEqual(data["items"][0]["tienda_nombre"], "Tostaduría Pro")

        # Filtro por tipo
        res_tipo = self.client.get("/api/v1/novedades?tipo=evento")
        self.assertEqual(res_tipo.status_code, 200)
        self.assertEqual(res_tipo.json()["total"], 1)

    def test_inactive_novedad_is_excluded_from_public_feed(self):
        post = NovedadTienda(
            tienda_id=2,
            titulo="Promo Oculta",
            descripcion="Descripción oculta",
            activo=False,
        )
        self.db.add(post)
        self.db.commit()

        res = self.client.get(f"/api/v1/novedades/{post.id}")
        self.assertEqual(res.status_code, 404)

    # --- ADMIN TIENDA & CONTROL DE PLANES ---

    def test_store_admin_without_plan_permission_cannot_create_novedad(self):
        # store_basic has plan_basic (publicaciones_novedades = False)
        payload = {
            "titulo": "Promoción no autorizada",
            "descripcion": "Intento de publicación sin plan",
            "categoria_tipo": "promocion",
        }
        res = self.client.post(
            "/api/v1/admin/tienda/novedades",
            json=payload,
            headers={"Authorization": f"Bearer {self.token_basic}"}
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("plan actual no incluye", res.json()["detail"])

    def test_store_admin_with_plan_permission_can_create_novedad(self):
        # store_pro has plan_pro (publicaciones_novedades = True)
        payload = {
            "titulo": "2x1 en Café Geisha",
            "descripcion": "Aprovecha durante este fin de semana largo en nuestra tostaduría.",
            "link_url": "https://pro.cl/ofertas",
            "categoria_tipo": "promocion",
        }
        res = self.client.post(
            "/api/v1/admin/tienda/novedades",
            json=payload,
            headers={"Authorization": f"Bearer {self.token_pro}"}
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["titulo"], "2x1 en Café Geisha")
        self.assertEqual(data["tienda_id"], 2)

    def test_store_can_edit_existing_post_even_if_plan_downgraded(self):
        # Post was previously published
        post = NovedadTienda(
            tienda_id=1,
            titulo="Publicación Antigua",
            descripcion="Descripción original",
            activo=True,
        )
        self.db.add(post)
        self.db.commit()

        # store_basic has no publish permission now, but MUST be allowed to edit existing ones
        res = self.client.put(
            f"/api/v1/admin/tienda/novedades/{post.id}",
            json={"titulo": "Título Corregido", "activo": False},
            headers={"Authorization": f"Bearer {self.token_basic}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["titulo"], "Título Corregido")
        self.assertFalse(res.json()["activo"])

    # --- SUPERADMIN GESTIÓN GLOBAL & FEEDBACK ---

    def test_superadmin_can_manage_novedades_for_any_store(self):
        # Superadmin publishes for basic store bypassing plan limits
        payload = {
            "tienda_id": 1,
            "titulo": "Anuncio Patrocinado Superadmin",
            "descripcion": "Publicado desde la consola global.",
            "categoria_tipo": "anuncio",
        }
        res = self.admin_client.post(
            "/api/v1/administracion/novedades",
            json=payload,
            headers={"Authorization": f"Bearer {self.token_super}"}
        )
        self.assertEqual(res.status_code, 201)
        new_id = res.json()["id"]

        # Superadmin deletes post
        res_del = self.admin_client.delete(
            f"/api/v1/administracion/novedades/{new_id}",
            headers={"Authorization": f"Bearer {self.token_super}"}
        )
        self.assertEqual(res_del.status_code, 200)

    def test_novedad_without_category_or_blog_and_pause_toggle(self):
        # 1. Crear novedad sin categoría (None) como superadmin
        payload_nocat = {
            "tienda_id": 2,
            "titulo": "Aviso General Sin Categoría",
            "descripcion": "Publicación informativa sin categoría fija.",
            "categoria_tipo": None,
            "activo": True,
        }
        res1 = self.admin_client.post(
            "/api/v1/administracion/novedades",
            json=payload_nocat,
            headers={"Authorization": f"Bearer {self.token_super}"}
        )
        self.assertEqual(res1.status_code, 201)
        self.assertIsNone(res1.json()["categoria_tipo"])
        id_nocat = res1.json()["id"]

        # 2. Crear novedad tipo 'blog' o 'educativo'
        payload_blog = {
            "tienda_id": 2,
            "titulo": "Guía de Molienda para Aeropress",
            "descripcion": "Artículo educativo sobre granulometría y extracción.",
            "categoria_tipo": "blog",
            "activo": True,
        }
        res2 = self.admin_client.post(
            "/api/v1/administracion/novedades",
            json=payload_blog,
            headers={"Authorization": f"Bearer {self.token_super}"}
        )
        self.assertEqual(res2.status_code, 201)
        self.assertEqual(res2.json()["categoria_tipo"], "blog")
        id_blog = res2.json()["id"]

        # 3. Filtrar feed público por sin_categoria y por blog
        res_feed_nocat = self.client.get("/api/v1/novedades?tipo=sin_categoria")
        self.assertEqual(res_feed_nocat.status_code, 200)
        self.assertGreaterEqual(res_feed_nocat.json()["total"], 1)

        res_feed_blog = self.client.get("/api/v1/novedades?tipo=blog")
        self.assertEqual(res_feed_blog.status_code, 200)
        self.assertGreaterEqual(res_feed_blog.json()["total"], 1)

        # 4. Pausar (ocultar) la publicación desde superadmin
        res_pause = self.admin_client.put(
            f"/api/v1/administracion/novedades/{id_nocat}",
            json={"activo": False},
            headers={"Authorization": f"Bearer {self.token_super}"}
        )
        self.assertEqual(res_pause.status_code, 200)
        self.assertFalse(res_pause.json()["activo"])

        # 5. Listar desde superadmin filtrando por activo=false
        res_list_paused = self.admin_client.get(
            "/api/v1/administracion/novedades?activo=false",
            headers={"Authorization": f"Bearer {self.token_super}"}
        )
        self.assertEqual(res_list_paused.status_code, 200)
        ids_paused = [x["id"] for x in res_list_paused.json()["items"]]
        self.assertIn(id_nocat, ids_paused)

    def test_superadmin_can_view_and_delete_feedback(self):
        # Seed feedbacks
        fb1 = SugerenciaFeedback(
            categoria="mejora",
            mensaje="Me gustaría poder ordenar por puntuación SCA.",
            contacto_opcional="barista@gmail.com",
            ip_hash="hash123",
            fecha_creacion=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        fb2 = SugerenciaFeedback(
            categoria="bug",
            mensaje="En Safari mobile se corta la rueda de sabores.",
            contacto_opcional=None,
            ip_hash="hash456",
            fecha_creacion=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add_all([fb1, fb2])
        self.db.commit()

        # List feedback
        res = self.admin_client.get(
            "/api/v1/administracion/feedback",
            headers={"Authorization": f"Bearer {self.token_super}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["conteo_por_categoria"].get("mejora"), 1)
        self.assertEqual(data["conteo_por_categoria"].get("bug"), 1)

        # Filter by category
        res_filtered = self.admin_client.get(
            "/api/v1/administracion/feedback?categoria=bug",
            headers={"Authorization": f"Bearer {self.token_super}"}
        )
        self.assertEqual(res_filtered.status_code, 200)
        self.assertEqual(res_filtered.json()["total"], 1)

        # Delete feedback
        res_del = self.admin_client.delete(
            f"/api/v1/administracion/feedback/{fb1.id}",
            headers={"Authorization": f"Bearer {self.token_super}"}
        )
        self.assertEqual(res_del.status_code, 200)


if __name__ == "__main__":
    unittest.main()
