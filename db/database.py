import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, 
    Numeric, DateTime, ForeignKey, UniqueConstraint, inspect, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from db.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

Base = declarative_base()
BASELINE_TABLES = {
    'tiendas',
    'productos',
    'variantes',
    'historial_precios',
    'estado_sincronizacion',
}

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Tienda(Base):
    __tablename__ = 'tiendas'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    url_base = Column(String(255), nullable=False)
    plataforma = Column(String(50), nullable=False, default='desconocida', server_default='desconocida')
    fecha_creacion = Column(DateTime, nullable=False, default=_utcnow)
    fecha_actualizacion = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    productos = relationship("Producto", back_populates="tienda", cascade="all, delete-orphan")
    sincronizaciones = relationship("Sincronizacion", back_populates="tienda", cascade="all, delete-orphan")

class Producto(Base):
    __tablename__ = 'productos'
    __table_args__ = (UniqueConstraint('tienda_id', 'id_externo', name='uq_producto_tienda_id_externo'),)
    id = Column(Integer, primary_key=True)
    tienda_id = Column(Integer, ForeignKey('tiendas.id'), nullable=False)
    id_externo = Column(String(255), nullable=True)
    nombre = Column(String(255), nullable=False)
    url_detalle = Column(String(500), unique=True, nullable=False)
    imagen = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, nullable=False, default=_utcnow)
    fecha_actualizacion = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    tienda = relationship("Tienda", back_populates="productos")
    variantes = relationship("Variante", back_populates="producto", cascade="all, delete-orphan")

class Variante(Base):
    __tablename__ = 'variantes'
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    id_variante_externo = Column(String(100), unique=True, nullable=False)
    opcion = Column(String(100), nullable=False)
    formato_gramos = Column(Integer, nullable=False)
    precio_clp = Column(Integer, nullable=False)
    precio_original_clp = Column(Integer, nullable=False)
    en_oferta = Column(Boolean, default=False)
    descuento_porcentaje = Column(Integer, default=0)
    precio_por_kilo = Column(Numeric(10, 2), nullable=False)
    disponible = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, nullable=False, default=_utcnow)
    fecha_actualizacion = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    producto = relationship("Producto", back_populates="variantes")
    historial_precios = relationship("HistorialPrecio", back_populates="variante", cascade="all, delete-orphan")

class HistorialPrecio(Base):
    __tablename__ = 'historial_precios'
    id = Column(Integer, primary_key=True)
    variante_id = Column(Integer, ForeignKey('variantes.id'), nullable=False)
    precio_clp = Column(Integer, nullable=False)
    precio_original_clp = Column(Integer, nullable=False)
    precio_por_kilo = Column(Numeric(10, 2), nullable=False)
    en_oferta = Column(Boolean, default=False)
    descuento_porcentaje = Column(Integer, default=0)
    disponible = Column(Boolean, default=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    variante = relationship("Variante", back_populates="historial_precios")

class EstadoSincronizacion(Base):
    __tablename__ = 'estado_sincronizacion'
    id = Column(Integer, primary_key=True)
    ultima_ejecucion = Column(DateTime(timezone=True), nullable=False)

class Sincronizacion(Base):
    __tablename__ = 'sincronizaciones'
    id = Column(Integer, primary_key=True)
    tienda_id = Column(Integer, ForeignKey('tiendas.id'), nullable=False)
    fecha_inicio = Column(DateTime(timezone=True), nullable=False)
    fecha_fin = Column(DateTime(timezone=True), nullable=True)
    resultado = Column(String(20), nullable=False)
    detalle_error = Column(Text, nullable=True)
    productos_agregados = Column(Integer, nullable=False, default=0, server_default='0')
    productos_eliminados = Column(Integer, nullable=False, default=0, server_default='0')
    productos_actualizados = Column(Integer, nullable=False, default=0, server_default='0')
    tienda = relationship("Tienda", back_populates="sincronizaciones")

class DatabaseManager:
    def __init__(self, db_url: str = None):
        url_final = db_url or settings.database_url
        self.engine = create_engine(
            url_final,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={"prepare_threshold": None}
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

    def inicializar_db(self):
        from alembic import command
        from alembic.config import Config
        from pathlib import Path

        logging.info("Aplicando migraciones de base de datos...")
        config = Config(str(Path(__file__).resolve().parent.parent / 'alembic.ini'))
        database_url = self.engine.url.render_as_string(hide_password=False)
        config.attributes['database_url'] = database_url
        config.set_main_option('sqlalchemy.url', database_url.replace('%', '%%'))

        existing_tables = set(inspect(self.engine).get_table_names())
        revision = None
        if 'alembic_version' in existing_tables:
            with self.engine.connect() as connection:
                revision = connection.execute(
                    text('SELECT version_num FROM alembic_version LIMIT 1')
                ).scalar_one_or_none()

        if revision is None:
            existing_baseline_tables = existing_tables.intersection(BASELINE_TABLES)
            if existing_baseline_tables == BASELINE_TABLES:
                logging.info("Esquema heredado completo detectado; registrando baseline Alembic.")
                command.stamp(config, '0001_baseline')
            elif existing_baseline_tables:
                missing_tables = sorted(BASELINE_TABLES - existing_baseline_tables)
                raise RuntimeError(
                    "Esquema de base de datos incompleto y sin versionar. "
                    f"Faltan tablas del baseline: {', '.join(missing_tables)}. "
                    "Revise la base antes de aplicar migraciones."
                )

        command.upgrade(config, 'head')
        logging.info("✅ Migraciones aplicadas correctamente.")

    def iniciar_sincronizacion(self, nombre_tienda: str, url_base: str, plataforma: str) -> int:
        session = self.SessionLocal()
        try:
            tienda = session.query(Tienda).filter(Tienda.nombre == nombre_tienda).first()
            if tienda is None:
                tienda = Tienda(nombre=nombre_tienda, url_base=url_base, plataforma=plataforma)
                session.add(tienda)
                session.flush()
            else:
                if tienda.url_base != url_base or tienda.plataforma != plataforma:
                    tienda.url_base = url_base
                    tienda.plataforma = plataforma
                    tienda.fecha_actualizacion = _utcnow()

            sincronizacion = Sincronizacion(
                tienda_id=tienda.id,
                fecha_inicio=datetime.now(timezone.utc),
                resultado='en_progreso',
            )
            session.add(sincronizacion)
            session.commit()
            return sincronizacion.id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def finalizar_sincronizacion(
        self,
        sincronizacion_id: int,
        resultado: str,
        detalle_error: str = None,
        productos_agregados: int = 0,
        productos_eliminados: int = 0,
        productos_actualizados: int = 0,
    ):
        session = self.SessionLocal()
        try:
            sincronizacion = session.query(Sincronizacion).filter(Sincronizacion.id == sincronizacion_id).one()
            sincronizacion.fecha_fin = datetime.now(timezone.utc)
            sincronizacion.resultado = resultado
            sincronizacion.detalle_error = detalle_error
            sincronizacion.productos_agregados = productos_agregados
            sincronizacion.productos_eliminados = productos_eliminados
            sincronizacion.productos_actualizados = productos_actualizados
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def registrar_ultima_sincronizacion(self):
        session = self.SessionLocal()
        try:
            estado = EstadoSincronizacion(id=1, ultima_ejecucion=datetime.now(timezone.utc))
            session.merge(estado)
            session.commit()
            return estado.ultima_ejecucion
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _bulk_insert_batch(session, model, mappings):
        if not mappings:
            return
        session.bulk_insert_mappings(model, mappings)
        session.commit()

    @staticmethod
    def _bulk_update_batch(session, model, mappings):
        if not mappings:
            return
        session.bulk_update_mappings(model, mappings)
        session.commit()

    @staticmethod
    def _ids_por_columna(session, model, column_name, values):
        if not values:
            return {}
        column = getattr(model, column_name)
        rows = session.query(column, model.id).filter(column.in_(values)).all()
        return {value: row_id for value, row_id in rows}

    def guardar_catalogo(
        self,
        catalogo: List[Dict[str, Any]],
        nombre_tienda: str = None,
        url_base: str = None,
        plataforma: str = 'desconocida',
    ):
        session = self.SessionLocal()
        total_a_procesar = len(catalogo)
        try:
            total_productos = 0
            total_variantes = 0
            total_historial = 0
            fecha_actual = _utcnow()

            tiendas_existentes = {t.nombre: t for t in session.query(Tienda).all()}
            tiendas_cache = {nombre: tienda.id for nombre, tienda in tiendas_existentes.items()}
            tiendas_a_insertar = []
            tiendas_a_actualizar = []
            tiendas_insertadas_vistas = set()
            productos_a_insertar = []
            productos_a_actualizar = []
            variantes_a_insertar = []
            variantes_a_actualizar = []
            historial_a_insertar = []

            if nombre_tienda is None and catalogo:
                nombre_tienda = catalogo[0]['tienda']
            if nombre_tienda is not None and any(p['tienda'] != nombre_tienda for p in catalogo):
                raise ValueError('Cada sincronización debe contener productos de una sola tienda.')

            logging.info(f"💾 Iniciando persistencia de {total_a_procesar} productos en PostgreSQL...")

            for prod_data in catalogo:
                nombre_tienda = prod_data['tienda']
                tienda_url_base = url_base or prod_data.get('url_base') or prod_data['url_detalle']
                if nombre_tienda not in tiendas_cache and nombre_tienda not in tiendas_insertadas_vistas:
                    tiendas_insertadas_vistas.add(nombre_tienda)
                    tiendas_a_insertar.append({
                        'nombre': nombre_tienda,
                        'url_base': tienda_url_base,
                        'plataforma': plataforma,
                        'fecha_creacion': fecha_actual,
                        'fecha_actualizacion': fecha_actual,
                    })
                elif nombre_tienda in tiendas_cache:
                    tienda = tiendas_existentes[nombre_tienda]
                    if tienda.url_base != tienda_url_base or tienda.plataforma != plataforma:
                        tiendas_a_actualizar.append({
                            'id': tienda.id,
                            'nombre': nombre_tienda,
                            'url_base': tienda_url_base,
                            'plataforma': plataforma,
                            'fecha_actualizacion': fecha_actual,
                        })

            if tiendas_a_insertar:
                self._bulk_insert_batch(session, Tienda, tiendas_a_insertar)
                tiendas_cache.update(self._ids_por_columna(session, Tienda, 'nombre', [row['nombre'] for row in tiendas_a_insertar]))

            if tiendas_a_actualizar:
                self._bulk_update_batch(session, Tienda, tiendas_a_actualizar)

            productos_agregados = 0
            productos_actualizados = 0
            productos_eliminados = 0
            ids_eliminados = []
            tienda_id_actual = tiendas_cache.get(nombre_tienda) if nombre_tienda else None
            productos_existentes = []
            if tienda_id_actual is not None:
                productos_existentes = session.query(Producto).filter(Producto.tienda_id == tienda_id_actual).all()
            productos_por_id_externo = {
                prod.id_externo: prod for prod in productos_existentes if prod.id_externo
            }
            productos_por_url = {prod.url_detalle: prod for prod in productos_existentes}

            unique_product_keys = set()
            for prod_data in catalogo:
                url_detalle = prod_data['url_detalle']
                id_externo = prod_data.get('id_externo') or prod_data.get('sku')
                id_externo = str(id_externo) if id_externo is not None else None
                clave_producto = ('id_externo', id_externo) if id_externo else ('url', url_detalle)
                if clave_producto in unique_product_keys:
                    continue
                unique_product_keys.add(clave_producto)

                tienda_id = tiendas_cache.get(prod_data['tienda'])
                if tienda_id is None:
                    continue

                producto_mapping = {
                    'tienda_id': tienda_id,
                    'id_externo': id_externo,
                    'nombre': prod_data['nombre'],
                    'url_detalle': url_detalle,
                    'imagen': prod_data['imagen'],
                    'descripcion': prod_data['descripcion'],
                    'fecha_creacion': fecha_actual,
                    'fecha_actualizacion': fecha_actual,
                }
                productos_a_insertar.append(producto_mapping)
                total_productos += 1

            if productos_a_insertar:
                producto_rows_nuevos = []
                producto_rows_actualizar = []
                productos_encontrados_ids = set()

                for row in productos_a_insertar:
                    url_detalle = row['url_detalle']
                    producto_existente = (
                        productos_por_id_externo.get(row['id_externo']) if row['id_externo'] else None
                    ) or productos_por_url.get(url_detalle)
                    if producto_existente is not None:
                        productos_actualizados += 1
                        productos_encontrados_ids.add(producto_existente.id)
                        cambios = {'id': producto_existente.id}
                        for campo in ('tienda_id', 'nombre', 'url_detalle', 'imagen', 'descripcion'):
                            if getattr(producto_existente, campo) != row[campo]:
                                cambios[campo] = row[campo]
                        if row['id_externo'] and producto_existente.id_externo != row['id_externo']:
                            cambios['id_externo'] = row['id_externo']
                        if len(cambios) > 1:
                            cambios['fecha_actualizacion'] = fecha_actual
                            producto_rows_actualizar.append(cambios)
                    else:
                        productos_agregados += 1
                        producto_rows_nuevos.append(row)

                ids_eliminados = [
                    prod.id for prod in productos_existentes
                    if prod.id not in productos_encontrados_ids
                ]
                productos_eliminados = len(ids_eliminados)

                if producto_rows_nuevos:
                    self._bulk_insert_batch(session, Producto, producto_rows_nuevos)

                if producto_rows_actualizar:
                    self._bulk_update_batch(session, Producto, producto_rows_actualizar)

                producto_ids = self._ids_por_columna(
                    session, Producto, 'url_detalle', [row['url_detalle'] for row in productos_a_insertar]
                )

                unique_variantes = set()
                for prod_data in catalogo:
                    producto_id = producto_ids.get(prod_data['url_detalle'])
                    if producto_id is None:
                        continue
                    for var_data in prod_data.get('variantes', []):
                        clave_variante = var_data['id_variante_externo']
                        if clave_variante in unique_variantes:
                            continue
                        unique_variantes.add(clave_variante)

                        variante_mapping = {
                            'producto_id': producto_id,
                            'id_variante_externo': var_data['id_variante_externo'],
                            'opcion': var_data['opcion'],
                            'formato_gramos': var_data['formato_gramos'],
                            'precio_clp': var_data['precio_clp'],
                            'precio_original_clp': var_data['precio_original_clp'],
                            'en_oferta': var_data['en_oferta'],
                            'descuento_porcentaje': var_data['descuento_porcentaje'],
                            'precio_por_kilo': var_data['precio_por_kilo'],
                            'disponible': var_data['disponible'],
                            'fecha_creacion': fecha_actual,
                            'fecha_actualizacion': fecha_actual,
                        }
                        variantes_a_insertar.append(variante_mapping)
                        total_variantes += 1

                if variantes_a_insertar:
                    variantes_existentes = {
                        variante.id_variante_externo: variante
                        for variante in session.query(Variante)
                        .filter(Variante.id_variante_externo.in_([
                            row['id_variante_externo'] for row in variantes_a_insertar
                        ])).all()
                    }
                    variante_rows_nuevos = []
                    variante_rows_actualizar = []

                    for row in variantes_a_insertar:
                        ext_id = row['id_variante_externo']
                        variante_existente = variantes_existentes.get(ext_id)
                        if variante_existente is not None:
                            cambios = {'id': variante_existente.id}
                            for campo in (
                                'producto_id', 'opcion', 'formato_gramos', 'precio_clp',
                                'precio_original_clp', 'en_oferta', 'descuento_porcentaje',
                                'precio_por_kilo', 'disponible',
                            ):
                                if getattr(variante_existente, campo) != row[campo]:
                                    cambios[campo] = row[campo]
                            if len(cambios) > 1:
                                cambios['fecha_actualizacion'] = fecha_actual
                                variante_rows_actualizar.append(cambios)
                        else:
                            variante_rows_nuevos.append(row)

                    if variante_rows_nuevos:
                        self._bulk_insert_batch(session, Variante, variante_rows_nuevos)

                    if variante_rows_actualizar:
                        self._bulk_update_batch(session, Variante, variante_rows_actualizar)

                    variante_ids = self._ids_por_columna(session, Variante, 'id_variante_externo', [row['id_variante_externo'] for row in variantes_a_insertar])

                    historial_vistos = set()
                    for prod_data in catalogo:
                        for var_data in prod_data.get('variantes', []):
                            variante_id = variante_ids.get(var_data['id_variante_externo'])
                            if variante_id is None or variante_id in historial_vistos:
                                continue
                            historial_vistos.add(variante_id)
                            historial_a_insertar.append({
                                'variante_id': variante_id,
                                'precio_clp': var_data['precio_clp'],
                                'precio_original_clp': var_data['precio_original_clp'],
                                'precio_por_kilo': var_data['precio_por_kilo'],
                                'en_oferta': var_data['en_oferta'],
                                'descuento_porcentaje': var_data['descuento_porcentaje'],
                                'disponible': var_data['disponible'],
                                'fecha_registro': fecha_actual,
                            })
                            total_historial += 1

                    if historial_a_insertar:
                        self._bulk_insert_batch(session, HistorialPrecio, historial_a_insertar)

            if ids_eliminados:
                variantes_ids = [row[0] for row in session.query(Variante.id).filter(Variante.producto_id.in_(ids_eliminados)).all()]
                if variantes_ids:
                    session.query(HistorialPrecio).filter(HistorialPrecio.variante_id.in_(variantes_ids)).delete(synchronize_session=False)
                    session.query(Variante).filter(Variante.id.in_(variantes_ids)).delete(synchronize_session=False)
                session.query(Producto).filter(Producto.id.in_(ids_eliminados)).delete(synchronize_session=False)
                session.commit()

            logging.info(f"💾 Persistencia exitosa: {total_productos} productos, {total_variantes} variantes y {total_historial} registros históricos.")
            return {
                'agregados': productos_agregados,
                'eliminados': productos_eliminados,
                'actualizados': productos_actualizados,
            }

        except Exception as e:
            try:
                session.rollback()
            except Exception:
                pass
            logging.error(f"❌ Error al guardar en la base de datos: {e}")
            raise
        finally:
            session.close()
