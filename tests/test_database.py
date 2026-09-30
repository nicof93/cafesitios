import sys
from pathlib import Path
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.database import DatabaseManager


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
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def add(self, obj):
        pass

    def flush(self):
        pass

    def execute(self, *args, **kwargs):
        return None


class TestDatabaseManager(unittest.TestCase):
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

        db.guardar_catalogo(catalogo)

        table_names = [name for name, _ in fake_session.calls]
        self.assertIn('tiendas', table_names)
        self.assertIn('productos', table_names)
        self.assertIn('variantes', table_names)
        self.assertIn('historial_precios', table_names)

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
