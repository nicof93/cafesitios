import sys
from pathlib import Path
import unittest
from types import SimpleNamespace
from datetime import datetime
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.database import (
    Base,
    DatabaseManager,
    HistorialPrecio,
    Producto,
    Sincronizacion,
    Variante,
)


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self):
        self.calls = []
        self.inserted = {}
        self.updated = {}
        self.merged = []
        self.commit_count = 0

    def query(self, *args, **kwargs):
        if not args:
            return FakeQuery([])

        model_or_column = args[0]
        if hasattr(model_or_column, '__tablename__'):
            return FakeQuery(self.inserted.get(model_or_column, []))

        if len(args) >= 2 and hasattr(args[1], 'class_'):
            model = args[1].class_
            column_name = getattr(args[0], 'key', None)
            rows = []
            for item in self.inserted.get(model, []):
                if column_name is None:
                    continue
                rows.append((getattr(item, column_name), item.id))
            return FakeQuery(rows)

        return FakeQuery([])

    def bulk_insert_mappings(self, model, mappings):
        self.calls.append((model.__tablename__, list(mappings)))
        stored_rows = self.inserted.setdefault(model, [])
        seen = set()
        for mapping in mappings:
            key = (
                mapping.get('url_detalle')
                or mapping.get('id_variante_externo')
                or mapping.get('nombre')
                or mapping.get('variante_id')
            )
            if key is None:
                continue
            if key in seen:
                raise ValueError(f'Duplicate unique value: {key}')
            seen.add(key)
        starting_id = max((row.id for row in stored_rows), default=0) + 1
        for index, mapping in enumerate(mappings):
            obj = SimpleNamespace(**mapping)
            obj.id = starting_id + index
            stored_rows.append(obj)

    def bulk_update_mappings(self, model, mappings):
        self.calls.append((model.__tablename__ + '_update', list(mappings)))
        self.updated.setdefault(model, []).extend(mappings)

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        pass

    def close(self):
        pass

    def add(self, obj):
        pass

    def merge(self, obj):
        self.merged.append(obj)
        return obj

    def flush(self):
        pass

    def execute(self, *args, **kwargs):
        return None


class TestDatabaseManager(unittest.TestCase):
    def test_registrar_ultima_sincronizacion_persists_singleton(self):
        db = DatabaseManager.__new__(DatabaseManager)
        fake_session = FakeSession()
        db.SessionLocal = lambda: fake_session

        timestamp = db.registrar_ultima_sincronizacion()

        self.assertEqual(fake_session.merged[0].id, 1)
        self.assertEqual(fake_session.merged[0].ultima_ejecucion, timestamp)
        self.assertEqual(fake_session.commit_count, 1)

    def test_guardar_catalogo_uses_bulk_insert_mappings(self):
        db = DatabaseManager.__new__(DatabaseManager)
        fake_session = FakeSession()
        db.SessionLocal = lambda: fake_session

        catalogo = [{
            'tienda': 'Tienda Demo',
            'nombre': 'Café Especial',
            'url_detalle': 'https://example.com/producto-1',
            'imagen': None,
            'descripcion': 'Café de especialidad',
            'variantes': [{
                'id_variante_externo': 'var-1',
                'opcion': '250g',
                'formato_gramos': 250,
                'precio_clp': 10000,
                'precio_original_clp': 12000,
                'en_oferta': True,
                'descuento_porcentaje': 17,
                'precio_por_kilo': 40000.0,
                'disponible': True,
            }],
        }]

        counts = db.guardar_catalogo(catalogo, plataforma='shopify')

        table_names = [name for name, _ in fake_session.calls]
        self.assertIn('tiendas', table_names)
        self.assertIn('productos', table_names)
        self.assertIn('variantes', table_names)
        self.assertIn('historial_precios', table_names)
        self.assertEqual(counts, {'agregados': 1, 'eliminados': 0, 'actualizados': 0})
        tienda_mapping = next(mappings[0] for name, mappings in fake_session.calls if name == 'tiendas')
        self.assertEqual(tienda_mapping['plataforma'], 'shopify')

    def test_sync_counts_product_changes_and_persists_result(self):
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        db = DatabaseManager.__new__(DatabaseManager)
        db.SessionLocal = sessionmaker(bind=engine)

        synchronization_id = db.iniciar_sincronizacion(
            'Tienda Demo', 'https://example.com', 'woocommerce'
        )

        def product(name, url, variant_id, price, external_id):
            return {
                'tienda': 'Tienda Demo',
            'id_externo': external_id,
                'nombre': name,
                'url_detalle': url,
                'imagen': None,
                'descripcion': name,
                'variantes': [{
                    'id_variante_externo': variant_id,
                    'opcion': '250g',
                    'formato_gramos': 250,
                    'precio_clp': price,
                    'precio_original_clp': price,
                    'en_oferta': False,
                    'descuento_porcentaje': 0,
                    'precio_por_kilo': price * 4,
                    'disponible': True,
                }],
            }

        db.guardar_catalogo([
            product('Retenido', 'https://example.com/retained', 'variant-1', 10000, 'product-1'),
            product('Eliminado', 'https://example.com/removed', 'variant-2', 12000, 'product-2'),
        ], nombre_tienda='Tienda Demo', url_base='https://example.com', plataforma='woocommerce')

        session = db.SessionLocal()
        try:
            retained = session.query(Producto).filter_by(id_externo='product-1').one()
            variant = session.query(Variante).filter_by(id_variante_externo='variant-1').one()
            store = retained.tienda
            product_created = retained.fecha_creacion
            variant_created = variant.fecha_creacion
            store_created = store.fecha_creacion
            store_updated = store.fecha_actualizacion
            retained.fecha_actualizacion = datetime(2000, 1, 1)
            variant.fecha_actualizacion = datetime(2000, 1, 1)
            session.commit()
        finally:
            session.close()

        counts = db.guardar_catalogo([
            product('Retenido actualizado', 'https://example.com/retained-v2', 'variant-1', 11000, 'product-1'),
            product('Nuevo', 'https://example.com/new', 'variant-3', 13000, 'product-3'),
        ], nombre_tienda='Tienda Demo', url_base='https://example.com', plataforma='woocommerce')

        db.finalizar_sincronizacion(
            synchronization_id,
            'exitoso',
            productos_agregados=counts['agregados'],
            productos_eliminados=counts['eliminados'],
            productos_actualizados=counts['actualizados'],
        )

        session = db.SessionLocal()
        try:
            sync = session.query(Sincronizacion).one()
            self.assertEqual(counts, {'agregados': 1, 'eliminados': 1, 'actualizados': 1})
            self.assertEqual(sync.resultado, 'exitoso')
            self.assertIsNotNone(sync.fecha_fin)
            self.assertEqual(sync.productos_agregados, 1)
            self.assertEqual(sync.productos_eliminados, 1)
            self.assertEqual(sync.productos_actualizados, 1)
            self.assertEqual(session.query(Producto).count(), 2)
            self.assertEqual(session.query(Variante).count(), 2)
            self.assertEqual(session.query(HistorialPrecio).count(), 3)
            retained = session.query(Producto).filter_by(id_externo='product-1').one()
            retained_variant = session.query(Variante).filter_by(id_variante_externo='variant-1').one()
            store = retained.tienda
            self.assertEqual(retained.url_detalle, 'https://example.com/retained-v2')
            self.assertEqual(retained.fecha_creacion, product_created)
            self.assertGreater(retained.fecha_actualizacion, datetime(2000, 1, 1))
            self.assertEqual(retained_variant.fecha_creacion, variant_created)
            self.assertGreater(retained_variant.fecha_actualizacion, datetime(2000, 1, 1))
            self.assertEqual(store.fecha_creacion, store_created)
            self.assertEqual(store.fecha_actualizacion, store_updated)
            self.assertEqual(session.query(Producto).filter_by(url_detalle='https://example.com/retained').count(), 0)
            self.assertEqual(
                session.query(HistorialPrecio)
                .join(Variante)
                .filter(Variante.id_variante_externo == 'variant-2')
                .count(),
                0,
            )
        finally:
            session.close()
            engine.dispose()

    def test_guardar_catalogo_deduplica_productos_repetidos(self):
        db = DatabaseManager.__new__(DatabaseManager)
        fake_session = FakeSession()
        db.SessionLocal = lambda: fake_session

        catalogo = [
            {
                'tienda': 'Tienda Demo',
                'nombre': 'Café Especial',
                'url_detalle': 'https://example.com/producto-1',
                'imagen': None,
                'descripcion': 'Café de especialidad',
                'variantes': [{
                    'id_variante_externo': 'var-1',
                    'opcion': '250g',
                    'formato_gramos': 250,
                    'precio_clp': 10000,
                    'precio_original_clp': 12000,
                    'en_oferta': True,
                    'descuento_porcentaje': 17,
                    'precio_por_kilo': 40000.0,
                    'disponible': True,
                }],
            },
            {
                'tienda': 'Tienda Demo',
                'nombre': 'Café Especial',
                'url_detalle': 'https://example.com/producto-1',
                'imagen': None,
                'descripcion': 'Café de especialidad actualizado',
                'variantes': [{
                    'id_variante_externo': 'var-1',
                    'opcion': '250g',
                    'formato_gramos': 250,
                    'precio_clp': 11000,
                    'precio_original_clp': 13000,
                    'en_oferta': True,
                    'descuento_porcentaje': 15,
                    'precio_por_kilo': 44000.0,
                    'disponible': True,
                }],
            },
        ]

        db.guardar_catalogo(catalogo)

        product_calls = [m for name, m in fake_session.calls if name == 'productos']
        self.assertEqual(len(product_calls), 1)


if __name__ == '__main__':
    unittest.main()
