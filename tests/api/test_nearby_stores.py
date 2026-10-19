import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, Producto, Tienda, Variante
from api.stores import get_stores_summary, haversine_distance


class TestNearbyStores(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

        # Tienda A en Providencia
        self.store_provi = Tienda(
            nombre="Café Providencia",
            url_base="https://provi.cl",
            comuna="Providencia",
            latitud=-33.4314,
            longitud=-70.6093,
        )
        # Tienda B en Viña del Mar
        self.store_vina = Tienda(
            nombre="Café Viña",
            url_base="https://vina.cl",
            comuna="Viña del Mar",
            latitud=-33.0245,
            longitud=-71.5518,
        )
        self.session.add_all([self.store_provi, self.store_vina])
        self.session.commit()

        # Agregar al menos 1 producto y variante disponible para que aparezcan en el ranking
        p1 = Producto(tienda=self.store_provi, nombre="Café 1", url_detalle="https://provi.cl/p1")
        p2 = Producto(tienda=self.store_vina, nombre="Café 2", url_detalle="https://vina.cl/p2")
        self.session.add_all([p1, p2])
        self.session.commit()

        v1 = Variante(
            id_variante_externo="v1", producto_id=p1.id, opcion="250g",
            formato_gramos=250, precio_clp=10000, precio_original_clp=10000,
            precio_por_kilo=40000, disponible=True
        )
        v2 = Variante(
            id_variante_externo="v2", producto_id=p2.id, opcion="250g",
            formato_gramos=250, precio_clp=10000, precio_original_clp=10000,
            precio_por_kilo=40000, disponible=True
        )
        self.session.add_all([v1, v2])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_haversine_formula(self):
        # Distancia aproximada entre Providencia (Stgo) y Viña del Mar (~98-100 km en línea recta)
        dist = haversine_distance(-33.4314, -70.6093, -33.0245, -71.5518)
        self.assertGreater(dist, 90.0)
        self.assertLess(dist, 115.0)

    def test_get_stores_ordered_by_proximity_to_santiago(self):
        # Usuario en Providencia (por cabecera o comuna)
        summary = get_stores_summary(
            page=1,
            page_size=10,
            sort_by="distance_asc",
            db_session=self.session,
            comuna="Providencia",
        )
        items = summary["items"]
        self.assertEqual(len(items), 2)
        # La tienda en Providencia debe estar primero por distancia mínima
        self.assertEqual(items[0]["nombre"], "Café Providencia")
        self.assertLess(items[0]["distancia_km"], 1.0)

        # La segunda debe ser Viña con mayor distancia
        self.assertEqual(items[1]["nombre"], "Café Viña")
        self.assertGreater(items[1]["distancia_km"], 50.0)


if __name__ == "__main__":
    unittest.main()

