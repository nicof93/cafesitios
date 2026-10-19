import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.database import Base, DatabaseManager, Tienda, Producto, Variante
import scrapper_application


class FakeCatalogDriver:
    def __init__(self, nombre, url_base):
        self.nombre = nombre
        self.url_base = url_base

    def consumir_productos(self):
        if '250g' in self.url_base:
            return [
                {
                    'tienda': self.nombre,
                    'id_externo': 'prod-blend-house',
                    'nombre': 'Mandrake House Blend',
                    'url_detalle': 'https://cafemandrake.cl/products/house-blend',
                    'imagen': 'https://cafemandrake.cl/img/250.jpg',
                    'descripcion': 'Blend especial tostado medio',
                    'variantes': [
                        {
                            'id_variante_externo': 'var-250',
                            'opcion': '250g',
                            'formato_gramos': 250,
                            'precio_clp': 9990,
                            'precio_original_clp': 9990,
                            'en_oferta': False,
                            'descuento_porcentaje': 0,
                            'precio_por_kilo': 39960.0,
                            'disponible': True,
                            'es_estimado': True,
                        }
                    ],
                }
            ]
        elif '1kg' in self.url_base:
            return [
                {
                    'tienda': self.nombre,
                    'id_externo': 'prod-blend-house',
                    'nombre': 'Mandrake House Blend',
                    'url_detalle': 'https://cafemandrake.cl/products/house-blend',
                    'imagen': 'https://cafemandrake.cl/img/1000.jpg',
                    'descripcion': 'Blend especial tostado medio',
                    'variantes': [
                        {
                            'id_variante_externo': 'var-1000',
                            'opcion': '1kg',
                            'formato_gramos': 1000,
                            'precio_clp': 32000,
                            'precio_original_clp': 32000,
                            'en_oferta': False,
                            'descuento_porcentaje': 0,
                            'precio_por_kilo': 32000.0,
                            'disponible': True,
                            'es_estimado': True,
                        }
                    ],
                }
            ]
        return []


class TestMultiCatalogSync(unittest.TestCase):
    def test_consumir_productos_tienda_combines_variants_across_collections(self):
        tienda = {
            'id': 1,
            'nombre': 'Café Mandrake',
            'url_base': 'https://cafemandrake.cl',
            'plataforma': 'shopify',
            'catalogos': [
                {'url_catalogo': 'https://cafemandrake.cl/collections/250g', 'etiqueta': '250g', 'activa': True},
                {'url_catalogo': 'https://cafemandrake.cl/collections/1kg', 'etiqueta': '1kg', 'activa': True},
            ],
        }

        with patch.dict(scrapper_application.drivers_por_plataforma, {'shopify': FakeCatalogDriver}, clear=True):
            productos = scrapper_application.consumir_productos_tienda(tienda)

        # Debe existir un solo producto unificado
        self.assertEqual(len(productos), 1)
        p = productos[0]
        self.assertEqual(p['nombre'], 'Mandrake House Blend')
        self.assertEqual(p['id_externo'], 'prod-blend-house')
        # Ambas variantes (250g y 1kg) deben estar presentes
        self.assertEqual(len(p['variantes']), 2)
        gramos_presentes = {v['formato_gramos'] for v in p['variantes']}
        self.assertEqual(gramos_presentes, {250, 1000})

    def test_guardar_catalogo_persists_under_single_store_id(self):
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        db = DatabaseManager.__new__(DatabaseManager)
        db.SessionLocal = sessionmaker(bind=engine)

        session = db.SessionLocal()
        store = Tienda(nombre='Café Mandrake', url_base='https://cafemandrake.cl', plataforma='shopify')
        session.add(store)
        session.commit()
        store_id = store.id
        session.close()

        # Simular productos combinados de múltiples catálogos
        unified_products = [
            {
                'tienda': 'Café Mandrake',
                'id_externo': 'prod-blend-house',
                'nombre': 'Mandrake House Blend',
                'url_detalle': 'https://cafemandrake.cl/products/house-blend',
                'imagen': 'https://cafemandrake.cl/img/250.jpg',
                'descripcion': 'Blend especial tostado medio',
                'variantes': [
                    {
                        'id_variante_externo': 'var-250',
                        'opcion': '250g',
                        'formato_gramos': 250,
                        'precio_clp': 9990,
                        'precio_original_clp': 9990,
                        'en_oferta': False,
                        'descuento_porcentaje': 0,
                        'precio_por_kilo': 39960.0,
                        'disponible': True,
                    },
                    {
                        'id_variante_externo': 'var-1000',
                        'opcion': '1kg',
                        'formato_gramos': 1000,
                        'precio_clp': 32000,
                        'precio_original_clp': 32000,
                        'en_oferta': False,
                        'descuento_porcentaje': 0,
                        'precio_por_kilo': 32000.0,
                        'disponible': True,
                    },
                ],
            }
        ]

        db.guardar_catalogo(unified_products, tienda_id=store_id)

        session = db.SessionLocal()
        try:
            prods = session.query(Producto).filter_by(tienda_id=store_id).all()
            self.assertEqual(len(prods), 1)
            prod = prods[0]
            self.assertEqual(prod.nombre, 'Mandrake House Blend')
            self.assertEqual(len(prod.variantes), 2)
            self.assertEqual({v.formato_gramos for v in prod.variantes}, {250, 1000})
        finally:
            session.close()
            engine.dispose()


if __name__ == '__main__':
    unittest.main()

