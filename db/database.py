import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, 
    Numeric, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from db.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

Base = declarative_base()

class Tienda(Base):
    __tablename__ = 'tiendas'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    url_base = Column(String(255), nullable=False)
    productos = relationship("Producto", back_populates="tienda", cascade="all, delete-orphan")

class Producto(Base):
    __tablename__ = 'productos'
    id = Column(Integer, primary_key=True)
    tienda_id = Column(Integer, ForeignKey('tiendas.id'), nullable=False)
    nombre = Column(String(255), nullable=False)
    url_detalle = Column(String(500), unique=True, nullable=False)
    imagen = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
        logging.info("Inicializando esquema en PostgreSQL (psycopg3)...")
        Base.metadata.create_all(bind=self.engine)
        logging.info("✅ Tablas sincronizadas correctamente.")

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

    def guardar_catalogo(self, catalogo: List[Dict[str, Any]]):
        session = self.SessionLocal()
        total_a_procesar = len(catalogo)
        try:
            total_productos = 0
            total_variantes = 0
            total_historial = 0
            fecha_actual = datetime.now(timezone.utc)

            tiendas_cache = {t.nombre: t.id for t in session.query(Tienda).all()}
            tiendas_a_insertar = []
            tiendas_a_actualizar = []
            tiendas_insertadas_vistas = set()
            productos_a_insertar = []
            productos_a_actualizar = []
            variantes_a_insertar = []
            variantes_a_actualizar = []
            historial_a_insertar = []

            logging.info(f"💾 Iniciando persistencia de {total_a_procesar} productos en PostgreSQL...")

            for prod_data in catalogo:
                nombre_tienda = prod_data['tienda']
                if nombre_tienda not in tiendas_cache and nombre_tienda not in tiendas_insertadas_vistas:
                    tiendas_insertadas_vistas.add(nombre_tienda)
                    tiendas_a_insertar.append({
                        'nombre': nombre_tienda,
                        'url_base': prod_data['url_detalle'],
                    })
                elif nombre_tienda in tiendas_cache:
                    tienda_id = tiendas_cache[nombre_tienda]
                    tiendas_a_actualizar.append({
                        'id': tienda_id,
                        'nombre': nombre_tienda,
                        'url_base': prod_data['url_detalle'],
                    })

            if tiendas_a_insertar:
                self._bulk_insert_batch(session, Tienda, tiendas_a_insertar)
                tiendas_cache.update(self._ids_por_columna(session, Tienda, 'nombre', [row['nombre'] for row in tiendas_a_insertar]))

            if tiendas_a_actualizar:
                self._bulk_update_batch(session, Tienda, tiendas_a_actualizar)

            unique_product_urls = set()
            for prod_data in catalogo:
                url_detalle = prod_data['url_detalle']
                if url_detalle in unique_product_urls:
                    continue
                unique_product_urls.add(url_detalle)

                tienda_id = tiendas_cache.get(prod_data['tienda'])
                if tienda_id is None:
                    continue

                producto_mapping = {
                    'tienda_id': tienda_id,
                    'nombre': prod_data['nombre'],
                    'url_detalle': url_detalle,
                    'imagen': prod_data['imagen'],
                    'descripcion': prod_data['descripcion'],
                    'fecha_actualizacion': fecha_actual,
                }
                productos_a_insertar.append(producto_mapping)
                total_productos += 1

            if productos_a_insertar:
                existing_product_ids = self._ids_por_columna(session, Producto, 'url_detalle', [row['url_detalle'] for row in productos_a_insertar])
                producto_rows_nuevos = []
                producto_rows_actualizar = []

                for row in productos_a_insertar:
                    url_detalle = row['url_detalle']
                    if url_detalle in existing_product_ids:
                        producto_rows_actualizar.append({
                            'id': existing_product_ids[url_detalle],
                            'tienda_id': row['tienda_id'],
                            'nombre': row['nombre'],
                            'url_detalle': url_detalle,
                            'imagen': row['imagen'],
                            'descripcion': row['descripcion'],
                            'fecha_actualizacion': row['fecha_actualizacion'],
                        })
                    else:
                        producto_rows_nuevos.append(row)

                if producto_rows_nuevos:
                    self._bulk_insert_batch(session, Producto, producto_rows_nuevos)

                if producto_rows_actualizar:
                    self._bulk_update_batch(session, Producto, producto_rows_actualizar)

                producto_ids = self._ids_por_columna(session, Producto, 'url_detalle', [row['url_detalle'] for row in productos_a_insertar])

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
                            'fecha_actualizacion': fecha_actual,
                        }
                        variantes_a_insertar.append(variante_mapping)
                        total_variantes += 1

                if variantes_a_insertar:
                    existing_variante_ids = self._ids_por_columna(session, Variante, 'id_variante_externo', [row['id_variante_externo'] for row in variantes_a_insertar])
                    variante_rows_nuevos = []
                    variante_rows_actualizar = []

                    for row in variantes_a_insertar:
                        ext_id = row['id_variante_externo']
                        if ext_id in existing_variante_ids:
                            variante_rows_actualizar.append({
                                'id': existing_variante_ids[ext_id],
                                **row,
                            })
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

            logging.info(f"💾 Persistencia exitosa: {total_productos} productos, {total_variantes} variantes y {total_historial} registros históricos.")

        except Exception as e:
            try:
                session.rollback()
            except Exception:
                pass
            logging.error(f"❌ Error al guardar en la base de datos: {e}")
            raise
        finally:
            session.close()
