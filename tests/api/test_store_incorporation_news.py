from datetime import datetime, timedelta, timezone
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app_plataforma import create_plataforma_app
from api.dependencies import get_db_session
from core.store_news_helper import contar_cafes_activos_tienda, sincronizar_novedad_nueva_tienda
from db.database import Base, NovedadTienda, Producto, Tienda, Variante, _utcnow
from main import app


def _crear_variante(producto_id: int, ext_id: str, precio: int = 12000, disponible: bool = True) -> Variante:
    return Variante(
        producto_id=producto_id,
        id_variante_externo=ext_id,
        opcion="250g",
        formato_gramos=250,
        precio_clp=precio,
        precio_original_clp=precio,
        precio_por_kilo=round((precio / 250) * 1000, 2),
        disponible=disponible,
    )


class TestStoreIncorporationNews(unittest.TestCase):
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
            session = self.SessionLocal()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db_session] = override_get_db
        self.client = TestClient(app)

        self.plataforma_app = create_plataforma_app()
        self.plataforma_app.dependency_overrides[get_db_session] = override_get_db
        self.admin_client = TestClient(self.plataforma_app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.plataforma_app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_create_store_creates_welcome_novelty_automatically(self):
        payload = {
            "nombre": "Café Cordillera",
            "url_base": "https://cafecordillera.cl",
            "url_catalogo": "https://cafecordillera.cl/collections/cafe",
            "plataforma": "shopify",
            "activo": True,
            "comuna": "Providencia",
            "sucursales": [],
            "catalogos": [
                {"url_catalogo": "https://cafecordillera.cl/collections/cafe", "etiqueta": "Principal", "activa": True}
            ]
        }
        res = self.admin_client.post("/api/v1/administracion/tiendas", json=payload)
        self.assertEqual(res.status_code, 201)
        store_id = res.json()["id"]

        novedad = self.db.query(NovedadTienda).filter(
            NovedadTienda.tienda_id == store_id,
            NovedadTienda.categoria_tipo == "nueva_tienda"
        ).first()

        self.assertIsNotNone(novedad)
        self.assertIn("Café Cordillera", novedad.titulo)
        self.assertIn("Café Cordillera", novedad.descripcion)
        self.assertEqual(novedad.categoria_tipo, "nueva_tienda")
        self.assertEqual(novedad.creado_por_rol, "PLATFORM_ADMIN")

    def test_sync_products_updates_welcome_novelty_count(self):
        store = Tienda(
            nombre="Café Araucanía",
            url_base="https://cafearaucania.cl",
            activo=True,
            fecha_creacion=_utcnow()
        )
        self.db.add(store)
        self.db.commit()
        self.db.refresh(store)

        sincronizar_novedad_nueva_tienda(store.id, self.db)
        self.db.commit()

        nov_initial = self.db.query(NovedadTienda).filter(
            NovedadTienda.tienda_id == store.id,
            NovedadTienda.categoria_tipo == "nueva_tienda"
        ).first()
        self.assertIn("Estamos preparando su catálogo", nov_initial.descripcion)

        p1 = Producto(
            tienda_id=store.id,
            nombre="Café Etiopía Yirgacheffe",
            url_detalle="https://cafearaucania.cl/p1",
            activo=True,
            oculto_catalogo=False,
        )
        p2 = Producto(
            tienda_id=store.id,
            nombre="Café Colombia Geisha",
            url_detalle="https://cafearaucania.cl/p2",
            activo=True,
            oculto_catalogo=False,
        )
        self.db.add_all([p1, p2])
        self.db.flush()

        v1 = _crear_variante(p1.id, "p1-v1", 12990)
        v2 = _crear_variante(p2.id, "p2-v1", 15990)
        self.db.add_all([v1, v2])
        self.db.commit()

        sincronizar_novedad_nueva_tienda(store.id, self.db)
        self.db.commit()
        self.db.refresh(nov_initial)

        self.assertIn("2 cafés disponibles", nov_initial.descripcion)
        self.assertIn("Caf%C3%A9+Araucan%C3%ADa", nov_initial.link_url)

    def test_latest_store_incorporation_endpoint(self):
        t_antigua = Tienda(
            nombre="Tostaduría Ancestral",
            url_base="https://ancestral.cl",
            activo=True,
            fecha_creacion=_utcnow() - timedelta(days=45)
        )
        t_nueva = Tienda(
            nombre="Tostaduría Austral",
            url_base="https://austral.cl",
            logo_url="https://austral.cl/logo.png",
            activo=True,
            fecha_creacion=_utcnow() - timedelta(days=2)
        )
        self.db.add_all([t_antigua, t_nueva])
        self.db.flush()

        p = Producto(
            tienda_id=t_nueva.id,
            nombre="Café Quindío Natural",
            url_detalle="https://austral.cl/quindio",
            activo=True,
            oculto_catalogo=False,
        )
        self.db.add(p)
        self.db.flush()
        v = _crear_variante(p.id, "v-austral-1", 11990)
        self.db.add(v)
        self.db.commit()

        res_es = self.client.get("/api/v1/tiendas/ultima-incorporada")
        self.assertEqual(res_es.status_code, 200)
        data = res_es.json()
        self.assertIsNotNone(data)
        self.assertEqual(data["nombre"], "Tostaduría Austral")
        self.assertEqual(data["cantidad_productos"], 1)
        self.assertTrue(data["es_reciente"])
        self.assertEqual(data["dias_desde_incorporacion"], 2)
        self.assertIn("Tostadur%C3%ADa+Austral", data["catalogo_url"])

        res_en = self.client.get("/api/v1/stores/latest")
        self.assertEqual(res_en.status_code, 200)
        self.assertEqual(res_en.json()["id"], data["id"])

    def test_novedades_feed_includes_nueva_tienda(self):
        store = Tienda(
            nombre="Singular Coffee Roasters",
            url_base="https://singular.cl",
            activo=True,
            fecha_creacion=_utcnow()
        )
        self.db.add(store)
        self.db.commit()

        sincronizar_novedad_nueva_tienda(store.id, self.db)
        self.db.commit()

        res = self.client.get("/api/v1/novedades?tipo=nueva_tienda")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["categoria_tipo"], "nueva_tienda")
        self.assertIn("Singular Coffee Roasters", data["items"][0]["titulo"])

    def test_stores_summary_sort_by_created_desc(self):
        t1 = Tienda(
            nombre="Tienda Uno",
            url_base="https://uno.cl",
            activo=True,
            fecha_creacion=_utcnow() - timedelta(days=10)
        )
        t2 = Tienda(
            nombre="Tienda Dos",
            url_base="https://dos.cl",
            activo=True,
            fecha_creacion=_utcnow()
        )
        self.db.add_all([t1, t2])
        self.db.flush()

        for idx, t in enumerate((t1, t2)):
            p = Producto(tienda_id=t.id, nombre=f"Café de {t.nombre}", url_detalle=f"u-{idx}", activo=True, oculto_catalogo=False)
            self.db.add(p)
            self.db.flush()
            self.db.add(_crear_variante(p.id, f"v-{idx}", 10000))
        self.db.commit()

        res = self.client.get("/api/v1/tiendas?sort_by=created_desc")
        self.assertEqual(res.status_code, 200)
        items = res.json()["items"]
        self.assertGreaterEqual(len(items), 2)
        self.assertEqual(items[0]["nombre"], "Tienda Dos")
        self.assertEqual(items[1]["nombre"], "Tienda Uno")


if __name__ == "__main__":
    unittest.main()
