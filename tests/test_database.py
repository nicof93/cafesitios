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
    NotaCata,
    Producto,
    ProductoNotaCata,
    Sincronizacion,
    Tienda,
    Variante,
)


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


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
    def test_guardar_catalogo_persists_characteristics_and_normalized_notes(self):
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        db = DatabaseManager.__new__(DatabaseManager)
        db.SessionLocal = sessionmaker(bind=engine)
        session = db.SessionLocal()
        store = Tienda(nombre='Tienda Café', url_base='https://coffee.example')
        session.add(store)
        session.commit()
        store_id = store.id
        session.close()

        product = {
            'tienda': 'Tienda Café',
            'id_externo': 'coffee-001',
            'nombre': 'Café de prueba',
            'url_detalle': 'https://coffee.example/coffee-001',
            'imagen': None,
            'descripcion': '<p>Finca y notas</p>',
            'caracteristicas_cafe': {
                'proceso': (
                    'post-cosecha: oxidación en cereza por 24 hrs, despulpado, '
                    'fermentación en mucílago en tanques por 72 hrs, lavado, '
                    'secado sobre camas en pergamino por 15 días'
                ),
                'finca': 'Los Robles',
                'variedad': 'Caturra',
                'elevacion_min_msnm': 1650,
                'elevacion_max_msnm': 1800,
                'cosecha': '2024/25',
                'fermentacion_tipo': 'anaeróbica',
                'fermentacion_horas': 72,
                'fuentes': {
                    'proceso': {
                        'texto': 'Proceso: Natural',
                        'confianza': 0.95,
                        'version': 'rules-v1',
                    },
                },
                'notas_cata_mencionadas': True,
                'notas_cata': [{
                    'nombre': 'frutos rojos',
                    'clave_normalizada': 'frutos-rojos',
                    'texto_origen': 'Perfil de taza: berries',
                    'confianza': 0.9,
                    'version_extractor': 'rules-v1',
                }],
            },
            'variantes': [{
                'id_variante_externo': 'coffee-001-250',
                'opcion': 'Grano',
                'formato_gramos': 250,
                'precio_clp': 10000,
                'precio_original_clp': 10000,
                'en_oferta': False,
                'descuento_porcentaje': 0,
                'precio_por_kilo': 40000,
                'disponible': True,
            }],
        }

        db.guardar_catalogo([product], tienda_id=store_id)
        product['caracteristicas_cafe'] = {
            'notas_cata_mencionadas': False,
        }
        db.guardar_catalogo([product], tienda_id=store_id)

        session = db.SessionLocal()
        try:
            saved_product = session.query(Producto).filter_by(id_externo='coffee-001').one()
            self.assertEqual(
                saved_product.proceso,
                'post-cosecha: oxidación en cereza por 24 hrs, despulpado, '
                'fermentación en mucílago en tanques por 72 hrs, lavado, '
                'secado sobre camas en pergamino por 15 días',
            )
            self.assertEqual(saved_product.finca, 'Los Robles')
            self.assertEqual(saved_product.variedad, 'Caturra')
            self.assertEqual(saved_product.elevacion_min_msnm, 1650)
            self.assertEqual(saved_product.elevacion_max_msnm, 1800)
            self.assertEqual(saved_product.cosecha, '2024/25')
            self.assertEqual(saved_product.fermentacion_tipo, 'anaeróbica')
            self.assertEqual(float(saved_product.fermentacion_horas), 72)
            self.assertEqual(saved_product.caracteristicas_fuente['proceso']['confianza'], 0.95)
            previous_update = saved_product.fecha_actualizacion
            self.assertEqual(session.query(NotaCata).count(), 1)
            self.assertEqual(session.query(ProductoNotaCata).count(), 1)
            relation = session.query(ProductoNotaCata).one()
            self.assertEqual(relation.nota.clave_normalizada, 'frutos-rojos')
            self.assertEqual(relation.texto_origen, 'Perfil de taza: berries')
            self.assertEqual(relation.confianza, 0.9)
            self.assertEqual(relation.version_extractor, 'rules-v1')
        finally:
            session.close()

        product['caracteristicas_cafe'] = {
            'notas_cata_mencionadas': True,
            'notas_cata': [{
                'nombre': 'cacao',
                'clave_normalizada': 'cacao',
                'texto_origen': 'Tasting notes: cocoa',
                'confianza': 0.9,
                'version_extractor': 'rules-v1',
            }],
        }
        db.guardar_catalogo([product], tienda_id=store_id)

        session = db.SessionLocal()
        try:
            saved_product = session.query(Producto).filter_by(id_externo='coffee-001').one()
            self.assertGreater(saved_product.fecha_actualizacion, previous_update)
            self.assertEqual(session.query(ProductoNotaCata).count(), 1)
            relation = session.query(ProductoNotaCata).one()
            self.assertEqual(relation.nota.clave_normalizada, 'cacao')
            self.assertEqual(session.query(NotaCata).count(), 2)
        finally:
            session.close()
            engine.dispose()

    def test_listar_tiendas_activas_omits_disabled_stores(self):
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        db = DatabaseManager.__new__(DatabaseManager)
        db.SessionLocal = sessionmaker(bind=engine)
        session = db.SessionLocal()
        active_store = Tienda(nombre='Activa', url_base='https://active.example')
        disabled_store = Tienda(
            nombre='Desactivada',
            url_base='https://disabled.example',
            activo=False,
        )
        session.add_all([active_store, disabled_store])
        session.commit()
        disabled_store_id = disabled_store.id
        session.close()

        try:
            stores = db.listar_tiendas_activas()
            self.assertEqual([store['nombre'] for store in stores], ['Activa'])
            with self.assertRaisesRegex(ValueError, 'tienda activa'):
                db.iniciar_sincronizacion(disabled_store_id)
        finally:
            engine.dispose()

    def test_inicializar_db_adopts_legacy_schema_without_sync_state(self):
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import inspect, text
        from tempfile import TemporaryDirectory

        project_root = Path(__file__).resolve().parent.parent
        with TemporaryDirectory() as directory:
            database_path = Path(directory) / 'legacy.sqlite'
            database_url = f"sqlite:///{database_path.as_posix()}"
            config = Config(str(project_root / 'alembic.ini'))
            config.attributes['database_url'] = database_url
            config.set_main_option('sqlalchemy.url', database_url)
            command.upgrade(config, '0001_baseline')

            legacy_engine = create_engine(database_url)
            with legacy_engine.begin() as connection:
                connection.execute(
                    text("INSERT INTO tiendas (nombre, url_base) VALUES ('Tienda existente', 'https://example.com')")
                )
                connection.execute(text('DROP TABLE estado_sincronizacion'))
                connection.execute(text('DROP TABLE alembic_version'))
            legacy_engine.dispose()

            db = DatabaseManager.__new__(DatabaseManager)
            db.engine = create_engine(database_url)
            try:
                db.inicializar_db()

                with db.engine.connect() as connection:
                    store_name = connection.execute(
                        text('SELECT nombre FROM tiendas WHERE id = 1')
                    ).scalar_one()
                    revision = connection.execute(
                        text('SELECT version_num FROM alembic_version')
                    ).scalar_one()

                self.assertEqual(store_name, 'Tienda existente')
                self.assertEqual(revision, '0006_long_coffee_process')
                self.assertIn('sincronizaciones', inspect(db.engine).get_table_names())
                self.assertIn('estado_sincronizacion', inspect(db.engine).get_table_names())
                product_columns = {
                    column['name']: str(column['type']).upper()
                    for column in inspect(db.engine).get_columns('productos')
                }
                self.assertEqual(product_columns['proceso'], 'TEXT')
                self.assertEqual(product_columns['fermentacion_tipo'], 'TEXT')
            finally:
                db.engine.dispose()

    def test_inicializar_db_rejects_partial_unversioned_schema(self):
        from tempfile import TemporaryDirectory
        from sqlalchemy import inspect, text

        project_root = Path(__file__).resolve().parent.parent
        with TemporaryDirectory() as directory:
            database_url = f"sqlite:///{(Path(directory) / 'partial.sqlite').as_posix()}"
            db = DatabaseManager.__new__(DatabaseManager)
            db.engine = create_engine(database_url)
            try:
                with db.engine.begin() as connection:
                    connection.execute(text(
                        'CREATE TABLE tiendas (id INTEGER PRIMARY KEY, nombre VARCHAR(100), url_base VARCHAR(255))'
                    ))

                with self.assertRaisesRegex(RuntimeError, 'incompleto y sin versionar'):
                    db.inicializar_db()

                self.assertNotIn('productos', inspect(db.engine).get_table_names())
            finally:
                db.engine.dispose()

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

        fake_session.inserted[Tienda] = [SimpleNamespace(
            id=1,
            nombre='Tienda Demo',
            url_base='https://example.com',
            plataforma='shopify',
            activo=True,
        )]
        counts = db.guardar_catalogo(catalogo, tienda_id=1)

        table_names = [name for name, _ in fake_session.calls]
        self.assertNotIn('tiendas', table_names)
        self.assertIn('productos', table_names)
        self.assertIn('variantes', table_names)
        self.assertIn('historial_precios', table_names)
        self.assertEqual(counts, {'agregados': 1, 'eliminados': 0, 'actualizados': 0})

    def test_sync_counts_product_changes_and_persists_result(self):
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        db = DatabaseManager.__new__(DatabaseManager)
        db.SessionLocal = sessionmaker(bind=engine)

        session = db.SessionLocal()
        store = Tienda(nombre='Tienda Demo', url_base='https://example.com', plataforma='woocommerce')
        session.add(store)
        session.commit()
        store_id = store.id
        session.close()
        synchronization_id = db.iniciar_sincronizacion(store_id)

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
        ], tienda_id=store_id)

        session = db.SessionLocal()
        try:
            retained = session.query(Producto).filter_by(id_externo='product-1').one()
            variant = session.query(Variante).filter_by(id_variante_externo='variant-1').one()
            store = retained.tienda
            product_created = retained.fecha_creacion
            variant_created = variant.fecha_creacion
            store_created = store.fecha_creacion
            store_updated = store.fecha_actualizacion
            removed = session.query(Producto).filter_by(id_externo='product-2').one()
            removed_id = removed.id
            removed_created = removed.fecha_creacion
            retained.fecha_actualizacion = datetime(2000, 1, 1)
            variant.fecha_actualizacion = datetime(2000, 1, 1)
            session.commit()
        finally:
            session.close()

        counts = db.guardar_catalogo([
            product('Retenido actualizado', 'https://example.com/retained-v2', 'variant-1', 11000, 'product-1'),
            product('Nuevo', 'https://example.com/new', 'variant-3', 13000, 'product-3'),
        ], tienda_id=store_id)

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
            self.assertEqual(session.query(Producto).count(), 3)
            self.assertEqual(session.query(Variante).count(), 3)
            self.assertEqual(session.query(HistorialPrecio).count(), 4)
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
            removed = session.query(Producto).filter_by(id=removed_id).one()
            self.assertFalse(removed.activo)
            self.assertEqual(removed.fecha_creacion, removed_created)
            self.assertEqual(session.query(HistorialPrecio).filter(HistorialPrecio.variante_id == removed.variantes[0].id).count(), 1)
            self.assertEqual(
                session.query(HistorialPrecio)
                .join(Variante)
                .filter(Variante.id_variante_externo == 'variant-2')
                .count(),
                1,
            )
        finally:
            session.close()

        reactivation_counts = db.guardar_catalogo([
            product('Retenido actualizado', 'https://example.com/retained-v2', 'variant-1', 11000, 'product-1'),
            product('Nuevo', 'https://example.com/new', 'variant-3', 13000, 'product-3'),
            product('Reaparecido', 'https://example.com/removed-v2', 'variant-2', 12000, 'product-2'),
        ], tienda_id=store_id)
        self.assertEqual(reactivation_counts, {'agregados': 0, 'eliminados': 0, 'actualizados': 3})

        session = db.SessionLocal()
        try:
            reactivated = session.query(Producto).filter_by(id_externo='product-2').one()
            self.assertEqual(reactivated.id, removed_id)
            self.assertTrue(reactivated.activo)
            self.assertEqual(reactivated.fecha_creacion, removed_created)
            self.assertEqual(session.query(HistorialPrecio).filter(
                HistorialPrecio.variante_id == reactivated.variantes[0].id
            ).count(), 2)
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

        fake_session.inserted[Tienda] = [SimpleNamespace(
            id=1,
            nombre='Tienda Demo',
            url_base='https://example.com',
            plataforma='desconocida',
            activo=True,
        )]
        db.guardar_catalogo(catalogo, tienda_id=1)

        product_calls = [m for name, m in fake_session.calls if name == 'productos']
        self.assertEqual(len(product_calls), 1)


if __name__ == '__main__':
    unittest.main()
