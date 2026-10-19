import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.products import get_weekly_price_drops
from application.get_weekly_price_drops import GetWeeklyPriceDropsUseCase
from db.database import Base, HistorialPrecio, Producto, Tienda, Variante


class TestWeeklyPriceDrops(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_get_weekly_price_drops_calculates_discounts_accurately(self):
        store = Tienda(
            id=1,
            nombre='Tostaduría Ejemplo',
            url_base='https://tostaduria.cl/catalogo',
            activo=True
        )
        self.session.add(store)

        prod_drop = Producto(
            id=10,
            tienda_id=1,
            id_externo='p-10',
            nombre='Café Geisha Especial',
            url_detalle='https://tostaduria.cl/cafe-geisha',
            activo=True,
            oculto_catalogo=False,
            imagen='https://example.com/geisha.jpg'
        )
        prod_nodrop = Producto(
            id=20,
            tienda_id=1,
            id_externo='p-20',
            nombre='Café Caturra Regular',
            url_detalle='https://tostaduria.cl/cafe-caturra',
            activo=True,
            oculto_catalogo=False
        )
        self.session.add_all([prod_drop, prod_nodrop])

        var_drop = Variante(
            id=101,
            producto_id=10,
            id_variante_externo='v-101',
            opcion='250g',
            formato_gramos=250,
            precio_clp=9000,
            precio_original_clp=12000,
            en_oferta=True,
            descuento_porcentaje=25,
            precio_por_kilo=36000.0,
            disponible=True
        )
        var_nodrop = Variante(
            id=201,
            producto_id=20,
            id_variante_externo='v-201',
            opcion='250g',
            formato_gramos=250,
            precio_clp=10000,
            precio_original_clp=10000,
            en_oferta=False,
            descuento_porcentaje=0,
            precio_por_kilo=40000.0,
            disponible=True
        )
        self.session.add_all([var_drop, var_nodrop])

        # Agregar historial de precios para var_drop (caída de 12000 a 9000 en los últimos 3 días)
        hp_old = HistorialPrecio(
            variante_id=101,
            precio_clp=12000,
            precio_original_clp=12000,
            precio_por_kilo=48000.0,
            fecha_registro=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=3)
        )
        hp_new = HistorialPrecio(
            variante_id=101,
            precio_clp=9000,
            precio_original_clp=12000,
            precio_por_kilo=36000.0,
            fecha_registro=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        )
        # Historial de var_nodrop (sin cambio)
        hp_nodrop = HistorialPrecio(
            variante_id=201,
            precio_clp=10000,
            precio_original_clp=10000,
            precio_por_kilo=40000.0,
            fecha_registro=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
        )
        self.session.add_all([hp_old, hp_new, hp_nodrop])
        self.session.commit()

        use_case = GetWeeklyPriceDropsUseCase(self.session)
        drops = use_case.execute(limit=10, dias=7)

        self.assertEqual(len(drops), 1)
        drop = drops[0]
        self.assertEqual(drop['producto_id'], 10)
        self.assertEqual(drop['nombre_producto'], 'Café Geisha Especial')
        self.assertEqual(drop['precio_anterior'], 12000)
        self.assertEqual(drop['precio_actual'], 9000)
        self.assertEqual(drop['monto_rebaja'], 3000)
        self.assertEqual(drop['porcentaje_descuento'], 25)
        self.assertEqual(drop['url_tienda'], 'https://tostaduria.cl')
        self.assertEqual(drop['formato_gramos'], 250)

    def test_get_weekly_price_drops_ignores_hidden_products(self):
        store = Tienda(id=2, nombre='Tostaduría 2', url_base='https://t2.cl', activo=True)
        self.session.add(store)

        prod_hidden = Producto(
            id=30,
            tienda_id=2,
            id_externo='p-30',
            nombre='Polera Barista (No café)',
            url_detalle='https://t2.cl/polera',
            activo=True,
            oculto_catalogo=True
        )
        self.session.add(prod_hidden)

        var_hidden = Variante(
            id=301,
            producto_id=30,
            id_variante_externo='v-301',
            opcion='Talla M',
            formato_gramos=250,
            precio_clp=10000,
            precio_original_clp=15000,
            en_oferta=True,
            descuento_porcentaje=33,
            precio_por_kilo=40000.0,
            disponible=True
        )
        self.session.add(var_hidden)

        hp1 = HistorialPrecio(variante_id=301, precio_clp=15000, precio_original_clp=15000, precio_por_kilo=60000.0, fecha_registro=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2))
        hp2 = HistorialPrecio(variante_id=301, precio_clp=10000, precio_original_clp=15000, precio_por_kilo=40000.0, fecha_registro=datetime.now(timezone.utc).replace(tzinfo=None))
        self.session.add_all([hp1, hp2])
        self.session.commit()

        use_case = GetWeeklyPriceDropsUseCase(self.session)
        drops = use_case.execute(limit=10, dias=7)
        self.assertEqual(len(drops), 0)

    def test_endpoint_returns_response_dto(self):
        store = Tienda(id=3, nombre='Tostaduría 3', url_base='https://t3.cl', activo=True)
        self.session.add(store)
        prod = Producto(id=40, tienda_id=3, id_externo='p-40', nombre='Blend Espresso', url_detalle='https://t3.cl/blend', activo=True, oculto_catalogo=False)
        self.session.add(prod)
        var = Variante(id=401, producto_id=40, id_variante_externo='v-401', opcion='250g', formato_gramos=250, precio_clp=8000, precio_original_clp=10000, en_oferta=True, descuento_porcentaje=20, precio_por_kilo=32000.0, disponible=True)
        self.session.add(var)
        self.session.commit()

        response = get_weekly_price_drops(limit=10, dias=7, db_session=self.session)
        self.assertGreaterEqual(response.total, 1)
        self.assertEqual(response.dias_evaluados, 7)
        self.assertEqual(response.ofertas[0].nombre_producto, 'Blend Espresso')
        self.assertEqual(response.ofertas[0].precio_actual, 8000)
        self.assertEqual(response.ofertas[0].precio_anterior, 10000)
        self.assertEqual(response.ofertas[0].monto_rebaja, 2000)
        self.assertEqual(response.ofertas[0].porcentaje_descuento, 20)


if __name__ == '__main__':
    unittest.main()
