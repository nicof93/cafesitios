import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean,
    Numeric, DateTime, ForeignKey, UniqueConstraint, Index, inspect, text, Float, JSON, ARRAY
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
REQUIRED_LEGACY_TABLES = BASELINE_TABLES - {'estado_sincronizacion'}

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Tienda(Base):
    __tablename__ = 'tiendas'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    url_base = Column(String(255), nullable=False)
    plataforma = Column(String(50), nullable=False, default='desconocida', server_default='desconocida')
    activo = Column(Boolean, nullable=False, default=True, server_default='true')
    direccion = Column(String(255), nullable=True)
    latitud = Column(Numeric(10, 8), nullable=True)
    longitud = Column(Numeric(11, 8), nullable=True)
    comuna = Column(String(100), nullable=True)
    fecha_creacion = Column(DateTime, nullable=False, default=_utcnow)
    fecha_actualizacion = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    productos = relationship("Producto", back_populates="tienda", cascade="all, delete-orphan")
    sincronizaciones = relationship("Sincronizacion", back_populates="tienda", cascade="all, delete-orphan")
    sucursales = relationship("SucursalTienda", back_populates="tienda", cascade="all, delete-orphan")


class SucursalTienda(Base):
    __tablename__ = 'sucursales_tienda'
    id = Column(Integer, primary_key=True)
    tienda_id = Column(Integer, ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    direccion = Column(String(255), nullable=True)
    comuna = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    latitud = Column(Numeric(10, 8), nullable=True)
    longitud = Column(Numeric(11, 8), nullable=True)
    activo = Column(Boolean, nullable=False, default=True, server_default='true')
    fecha_creacion = Column(DateTime, nullable=False, default=_utcnow)
    fecha_actualizacion = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    tienda = relationship("Tienda", back_populates="sucursales")


class NotaCata(Base):
    __tablename__ = 'notas_cata'
    id = Column(Integer, primary_key=True)
    clave_normalizada = Column(String(160), unique=True, nullable=False)
    nombre = Column(String(160), nullable=False)
    productos = relationship("ProductoNotaCata", back_populates="nota")

class Producto(Base):
    __tablename__ = 'productos'
    __table_args__ = (
        UniqueConstraint('tienda_id', 'id_externo', name='uq_producto_tienda_id_externo'),
        Index('idx_productos_tienda_id', 'tienda_id'),
        Index('idx_productos_activo_oculto_cat', 'activo', 'oculto_catalogo', 'categoria'),
    )
    id = Column(Integer, primary_key=True)
    tienda_id = Column(Integer, ForeignKey('tiendas.id'), nullable=False)
    id_externo = Column(String(255), nullable=True)
    activo = Column(Boolean, nullable=False, default=True, server_default='true')
    oculto_catalogo = Column(Boolean, nullable=False, default=False, server_default='false')
    categoria = Column(String(30), nullable=False, default='cafe', server_default='cafe', index=True)
    nombre = Column(String(255), nullable=False)
    url_detalle = Column(String(500), unique=True, nullable=False)
    imagen = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)
    proceso = Column(Text, nullable=True)
    tueste = Column(String(255), nullable=True)
    finca = Column(String(255), nullable=True)
    variedad = Column(String(255), nullable=True)
    pais_origen = Column(String(255), nullable=True)
    elevacion_min_msnm = Column(Integer, nullable=True)
    elevacion_max_msnm = Column(Integer, nullable=True)
    cosecha = Column(String(100), nullable=True)
    fermentacion_tipo = Column(Text, nullable=True)
    fermentacion_horas = Column(Numeric(8, 2), nullable=True)
    caracteristicas_fuente = Column(JSON, nullable=True)
    fecha_creacion = Column(DateTime, nullable=False, default=_utcnow)
    fecha_actualizacion = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    tienda = relationship("Tienda", back_populates="productos")
    variantes = relationship("Variante", back_populates="producto", cascade="all, delete-orphan")
    notas_cata = relationship("ProductoNotaCata", back_populates="producto", cascade="all, delete-orphan")

class ProductoNotaCata(Base):
    __tablename__ = 'producto_notas_cata'
    producto_id = Column(Integer, ForeignKey('productos.id'), primary_key=True)
    nota_id = Column(Integer, ForeignKey('notas_cata.id'), primary_key=True)
    texto_origen = Column(Text, nullable=False)
    confianza = Column(Float, nullable=False)
    version_extractor = Column(String(50), nullable=False)
    producto = relationship("Producto", back_populates="notas_cata")
    nota = relationship("NotaCata", back_populates="productos")

class Variante(Base):
    __tablename__ = 'variantes'
    __table_args__ = (
        Index('idx_variantes_producto_id', 'producto_id'),
        Index('idx_variantes_disponible_kilo', 'disponible', 'precio_por_kilo'),
        Index('idx_variantes_disponible_precio', 'disponible', 'precio_clp'),
    )
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
    es_estimado = Column(Boolean, nullable=False, default=True, server_default='true')
    disponible = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, nullable=False, default=_utcnow)
    fecha_actualizacion = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    producto = relationship("Producto", back_populates="variantes")
    historial_precios = relationship("HistorialPrecio", back_populates="variante", cascade="all, delete-orphan")

class HistorialPrecio(Base):
    __tablename__ = 'historial_precios'
    __table_args__ = (
        Index('idx_historial_precios_variante_id', 'variante_id'),
        Index('idx_historial_precios_var_fecha', 'variante_id', 'fecha_registro'),
    )
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

class SincronizacionLog(Base):
    __tablename__ = 'sincronizaciones_log'
    id = Column(Integer, primary_key=True)
    fecha_ejecucion = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    estado = Column(String(20), nullable=False, default='OK', server_default='OK')
    productos_nuevos = Column(Integer, nullable=False, default=0, server_default='0')
    productos_actualizados = Column(Integer, nullable=False, default=0, server_default='0')
    productos_con_cambio_precio = Column(Integer, nullable=False, default=0, server_default='0')
    duracion_segundos = Column(Numeric(10, 2), nullable=False, default=0, server_default='0')
    mensaje_error = Column(Text, nullable=True)

class Receta(Base):
    __tablename__ = 'recetas'
    id = Column(Integer, primary_key=True)
    dispositivo_uuid = Column(String(64), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey('productos.id', ondelete='SET NULL'), nullable=True)
    nombre_receta = Column(String(150), nullable=False)
    metodo = Column(String(100), nullable=False)
    dosis_cafe_g = Column(Numeric(5, 2), nullable=False)
    agua_ml = Column(Numeric(6, 2), nullable=False)
    ratio = Column(String(20), nullable=True)
    molino_usado = Column(String(100), nullable=True)
    grosor_molienda = Column(String(50), nullable=True)
    temperatura_c = Column(Integer, nullable=True)
    tiempo_total_s = Column(Integer, nullable=True)
    calificacion_1_10 = Column(Integer, nullable=True)
    reintentar = Column(Boolean, default=True, server_default='true')
    notas_catado = Column(Text, nullable=True)
    catacion_sca = Column(JSON, nullable=True)
    puntuacion_sca_total = Column(Numeric(5, 2), nullable=True)
    fecha_creacion = Column(DateTime, nullable=False, default=_utcnow)
    producto = relationship("Producto")

class SugerenciaFeedback(Base):
    __tablename__ = 'sugerencias_feedback'
    id = Column(Integer, primary_key=True)
    categoria = Column(String(50), nullable=False)
    mensaje = Column(Text, nullable=False)
    contacto_opcional = Column(String(150), nullable=True)
    ip_hash = Column(String(64), nullable=False)
    fecha_creacion = Column(DateTime, nullable=False, default=_utcnow)

class InteraccionClic(Base):
    __tablename__ = 'interacciones_clics'
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey('productos.id', ondelete='SET NULL'), nullable=True)
    variante_id = Column(Integer, ForeignKey('variantes.id', ondelete='SET NULL'), nullable=True)
    tipo_evento = Column(String(50), nullable=False)
    ip_hash = Column(String(64), nullable=False)
    metadata_evento = Column(JSON, nullable=True)
    fecha_creacion = Column(DateTime, nullable=False, default=_utcnow)

class HistorialBusqueda(Base):
    __tablename__ = 'historial_busquedas'
    id = Column(Integer, primary_key=True)
    termino_busqueda = Column(String(255), nullable=False)
    resultados_encontrados = Column(Integer, nullable=False, default=0, server_default='0')
    fecha_creacion = Column(DateTime, nullable=False, default=_utcnow)

class Cafe(Base):
    __tablename__ = 'cafes'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    origen = Column(String(255), nullable=True)
    finca_productor = Column(String(255), nullable=True)
    variedad = Column(String(255), nullable=True)
    proceso = Column(String(255), nullable=True)
    lote = Column(String(100), nullable=True)
    notas_cata = Column(ARRAY(String).with_variant(JSON, 'sqlite'), nullable=True)
    notas_normalizadas = Column(ARRAY(String).with_variant(JSON, 'sqlite'), nullable=True)
    hash_descripcion = Column(String(32), nullable=True, index=True)
    fecha_creacion = Column(DateTime, nullable=False, default=_utcnow)
    fecha_actualizacion = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    ofertas = relationship("OfertaTienda", back_populates="cafe", cascade="all, delete-orphan")

class OfertaTienda(Base):
    __tablename__ = 'ofertas_tienda'
    id = Column(Integer, primary_key=True)
    cafe_id = Column(Integer, ForeignKey('cafes.id', ondelete='CASCADE'), nullable=False)
    tienda_id = Column(Integer, ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False)
    precio_actual = Column(Integer, nullable=False)
    formato_gramos = Column(Integer, nullable=False)
    precio_por_kilo = Column(Numeric(10, 2), nullable=False)
    es_estimado = Column(Boolean, nullable=False, default=True, server_default='true')
    link_detalle = Column(String(500), unique=True, nullable=False)
    disponible = Column(Boolean, nullable=False, default=True, server_default='true')
    ultima_actualizacion = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    cafe = relationship("Cafe", back_populates="ofertas")
    tienda = relationship("Tienda")


class UsuarioTienda(Base):
    __tablename__ = 'usuarios_tienda'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id = Column(String(36), nullable=False, index=True)
    tienda_id = Column(Integer, ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False, index=True)
    rol = Column(String(50), nullable=False, default='STORE_ADMIN', server_default='STORE_ADMIN')
    creado_en = Column(DateTime, nullable=False, default=_utcnow)
    tienda = relationship("Tienda")
    __table_args__ = (
        UniqueConstraint('usuario_id', 'tienda_id', name='uq_usuario_tienda'),
    )


class AuditoriaAccionesTienda(Base):
    __tablename__ = 'auditoria_acciones_tienda'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tienda_id = Column(Integer, ForeignKey('tiendas.id', ondelete='CASCADE'), nullable=False, index=True)
    usuario_id = Column(String(36), nullable=False, index=True)
    accion = Column(String(50), nullable=False)
    entidad = Column(String(50), nullable=False)
    entidad_id = Column(Integer, nullable=True)
    valores_previos = Column(JSON, nullable=True)
    valores_nuevos = Column(JSON, nullable=True)
    ip_origen = Column(String(45), nullable=True)
    fecha_registro = Column(DateTime, nullable=False, default=_utcnow, index=True)
    tienda = relationship("Tienda")


class DatabaseManager:
    def __init__(self, db_url: str = None):
        url_final = db_url or settings.database_url
        connect_args = {} if str(url_final).startswith("sqlite") else {"prepare_threshold": None}
        self.engine = create_engine(
            url_final,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args=connect_args,
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
            existing_legacy_tables = existing_tables.intersection(REQUIRED_LEGACY_TABLES)
            if existing_legacy_tables == REQUIRED_LEGACY_TABLES:
                if 'estado_sincronizacion' not in existing_tables:
                    logging.info("Creando la tabla auxiliar estado_sincronizacion ausente en el esquema heredado.")
                    EstadoSincronizacion.__table__.create(bind=self.engine, checkfirst=True)
                logging.info("Esquema heredado compatible detectado; registrando baseline Alembic.")
                command.stamp(config, '0001_baseline')
            elif existing_baseline_tables:
                missing_tables = sorted(REQUIRED_LEGACY_TABLES - existing_legacy_tables)
                raise RuntimeError(
                    "Esquema de base de datos incompleto y sin versionar. "
                    f"Faltan tablas del baseline: {', '.join(missing_tables)}. "
                    "Revise la base antes de aplicar migraciones."
                )

        command.upgrade(config, 'head')
        logging.info("✅ Migraciones aplicadas correctamente.")

    def listar_tiendas_activas(self) -> List[Dict[str, Any]]:
        session = self.SessionLocal()
        try:
            tiendas = (
                session.query(Tienda)
                .filter(Tienda.activo.is_(True))
                .order_by(Tienda.nombre.asc())
                .all()
            )
            return [
                {
                    'id': tienda.id,
                    'nombre': tienda.nombre,
                    'url_base': tienda.url_base,
                    'plataforma': tienda.plataforma,
                }
                for tienda in tiendas
            ]
        finally:
            session.close()

    def obtener_tienda_por_id(self, tienda_id: int) -> Optional[Dict[str, Any]]:
        session = self.SessionLocal()
        try:
            tienda = session.query(Tienda).filter(Tienda.id == tienda_id).first()
            if not tienda:
                return None
            return {
                'id': tienda.id,
                'nombre': tienda.nombre,
                'url_base': tienda.url_base,
                'plataforma': tienda.plataforma,
                'activo': bool(tienda.activo),
            }
        finally:
            session.close()

    def listar_tiendas_no_sincronizadas(self) -> List[Dict[str, Any]]:
        session = self.SessionLocal()
        try:
            tiendas_activas = (
                session.query(Tienda)
                .filter(Tienda.activo.is_(True))
                .order_by(Tienda.nombre.asc())
                .all()
            )
            unsynced = []
            for t in tiendas_activas:
                prod_count = (
                    session.query(func.count(Producto.id))
                    .filter(Producto.tienda_id == t.id, Producto.activo.is_(True))
                    .scalar()
                    or 0
                )
                has_successful_sync = (
                    session.query(Sincronizacion.id)
                    .filter(
                        Sincronizacion.tienda_id == t.id,
                        Sincronizacion.resultado == 'exitoso',
                    )
                    .first()
                    is not None
                )
                if prod_count == 0 or not has_successful_sync:
                    unsynced.append({
                        'id': t.id,
                        'nombre': t.nombre,
                        'url_base': t.url_base,
                        'plataforma': t.plataforma,
                    })
            return unsynced
        finally:
            session.close()

    def iniciar_sincronizacion(self, tienda_id: int) -> int:
        session = self.SessionLocal()
        try:
            tienda = session.query(Tienda).filter(
                Tienda.id == tienda_id,
                Tienda.activo.is_(True),
            ).first()
            if tienda is None:
                raise ValueError(f"La tienda activa con id {tienda_id} no existe.")

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

    def refrescar_vistas_materializadas(self):
        """Refresca concurrentemente las vistas materializadas en PostgreSQL."""
        if getattr(self.engine, 'dialect', None) and self.engine.dialect.name == 'postgresql':
            with self.engine.connect() as conn:
                try:
                    conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                        text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_variaciones_precio;")
                    )
                    logging.info("⚡ Vista materializada mv_variaciones_precio refrescada exitosamente.")
                except Exception as e:
                    logging.warning(f"No se pudo refrescar mv_variaciones_precio concurrentemente: {e}")

    def registrar_sincronizacion_log(
        self,
        estado: str = "OK",
        productos_nuevos: int = 0,
        productos_actualizados: int = 0,
        productos_con_cambio_precio: int = 0,
        duracion_segundos: float = 0.0,
        mensaje_error: str = None,
    ) -> int:
        session = self.SessionLocal()
        try:
            estado_norm = "OK" if str(estado).upper() in ("OK", "EXITOSO", "SUCCESS") else "ERROR"
            log_entry = SincronizacionLog(
                fecha_ejecucion=datetime.now(timezone.utc),
                estado=estado_norm,
                productos_nuevos=int(productos_nuevos or 0),
                productos_actualizados=int(productos_actualizados or 0),
                productos_con_cambio_precio=int(productos_con_cambio_precio or 0),
                duracion_segundos=round(float(duracion_segundos or 0.0), 2),
                mensaje_error=mensaje_error,
            )
            session.add(log_entry)
            session.commit()
            return log_entry.id
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
        tienda_id: int,
    ):
        session = self.SessionLocal()
        total_a_procesar = len(catalogo)
        try:
            total_productos = 0
            total_variantes = 0
            total_historial = 0
            fecha_actual = _utcnow()

            tienda = session.query(Tienda).filter(
                Tienda.id == tienda_id,
                Tienda.activo.is_(True),
            ).first()
            if tienda is None:
                raise ValueError(f"La tienda activa con id {tienda_id} no existe.")
            if any(producto['tienda'] != tienda.nombre for producto in catalogo):
                raise ValueError('Cada sincronización debe contener productos de una sola tienda.')

            productos_a_insertar = []
            productos_a_actualizar = []
            variantes_a_insertar = []
            variantes_a_actualizar = []
            historial_a_insertar = []
            productos_encontrados_ids = set()

            logging.info(f"💾 Iniciando persistencia de {total_a_procesar} productos en PostgreSQL...")

            productos_agregados = 0
            productos_actualizados = 0
            productos_eliminados = 0
            productos_existentes = [
                prod for prod in session.query(Producto).filter(
                    Producto.tienda_id == tienda.id
                ).all()
                if getattr(prod, 'tienda_id', tienda.id) == tienda.id
            ]
            productos_por_id_externo = {
                prod.id_externo: prod for prod in productos_existentes if prod.id_externo
            }
            productos_por_url = {prod.url_detalle: prod for prod in productos_existentes}

            urls_catalogo_set = {
                prod_data['url_detalle']
                for prod_data in catalogo
                if prod_data.get('url_detalle')
            }
            productos_globales_por_url = {
                prod.url_detalle: prod
                for prod in session.query(Producto).filter(
                    Producto.url_detalle.in_(list(urls_catalogo_set))
                ).all()
                if getattr(prod, 'url_detalle', None) in urls_catalogo_set
            } if urls_catalogo_set else {}

            unique_product_keys = set()
            seen_urls = set()
            for prod_data in catalogo:
                url_detalle = prod_data['url_detalle']
                id_externo = prod_data.get('id_externo') or prod_data.get('sku')
                id_externo = str(id_externo) if id_externo is not None else None
                clave_producto = ('id_externo', id_externo) if id_externo else ('url', url_detalle)
                if clave_producto in unique_product_keys or url_detalle in seen_urls:
                    continue
                unique_product_keys.add(clave_producto)
                seen_urls.add(url_detalle)
                caracteristicas = prod_data.get('caracteristicas_cafe') or {}
                fuentes = dict(caracteristicas.get('fuentes') or {})
                if caracteristicas.get('resumen_corto'):
                    fuentes['resumen_corto'] = caracteristicas['resumen_corto']
                elif prod_data.get('descripcion_resumida'):
                    fuentes['resumen_corto'] = prod_data['descripcion_resumida']

                from domain.search_normalizer import classify_product_category
                categoria_calc = classify_product_category(prod_data['nombre'])
                producto_mapping = {
                    'tienda_id': tienda.id,
                    'id_externo': id_externo,
                    'activo': True,
                    'categoria': categoria_calc,
                    'nombre': prod_data['nombre'],
                    'url_detalle': url_detalle,
                    'imagen': prod_data['imagen'],
                    'descripcion': prod_data['descripcion'],
                    'fecha_creacion': fecha_actual,
                    'fecha_actualizacion': fecha_actual,
                    'caracteristicas_fuente': fuentes,
                }
                for field in (
                    'proceso', 'tueste', 'finca', 'variedad', 'pais_origen', 'elevacion_min_msnm',
                    'elevacion_max_msnm', 'cosecha', 'fermentacion_tipo',
                    'fermentacion_horas',
                ):
                    if caracteristicas.get(field) is not None:
                        val = caracteristicas[field]
                        if field in ('tueste', 'finca', 'variedad', 'pais_origen') and isinstance(val, str):
                            val = val[:250]
                        elif field == 'cosecha' and isinstance(val, str):
                            val = val[:100]
                        producto_mapping[field] = val
                productos_a_insertar.append(producto_mapping)
                total_productos += 1

            if productos_a_insertar:
                producto_rows_nuevos = []
                producto_rows_actualizar = []

                for row in productos_a_insertar:
                    url_detalle = row['url_detalle']
                    prod_por_id_ext = (
                        productos_por_id_externo.get(row['id_externo']) if row['id_externo'] else None
                    )
                    prod_por_url = (
                        productos_por_url.get(url_detalle)
                        or productos_globales_por_url.get(url_detalle)
                    )
                    if prod_por_url is not None and (prod_por_id_ext is None or prod_por_url.id != prod_por_id_ext.id):
                        producto_existente = prod_por_url
                    else:
                        producto_existente = prod_por_id_ext or prod_por_url

                    if producto_existente is not None:
                        productos_actualizados += 1
                        productos_encontrados_ids.add(producto_existente.id)
                        cambios = {'id': producto_existente.id}
                        for campo in ('tienda_id', 'nombre', 'url_detalle', 'imagen', 'descripcion', 'activo', 'categoria'):
                            if getattr(producto_existente, campo, None) != row[campo]:
                                cambios[campo] = row[campo]
                        for campo in (
                            'proceso', 'tueste', 'finca', 'variedad', 'pais_origen', 'elevacion_min_msnm',
                            'elevacion_max_msnm', 'cosecha', 'fermentacion_tipo',
                            'fermentacion_horas',
                        ):
                            if campo in row:
                                val = row[campo]
                                if campo in ('tueste', 'finca', 'variedad', 'pais_origen') and isinstance(val, str):
                                    val = val[:250]
                                elif campo == 'cosecha' and isinstance(val, str):
                                    val = val[:100]
                                if getattr(producto_existente, campo) != val:
                                    cambios[campo] = val
                        if row['id_externo'] and producto_existente.id_externo != row['id_externo']:
                            conflicto_ext = productos_por_id_externo.get(row['id_externo'])
                            if conflicto_ext is None or conflicto_ext.id == producto_existente.id:
                                cambios['id_externo'] = row['id_externo']
                        fuentes_actuales = producto_existente.caracteristicas_fuente or {}
                        fuentes_nuevas = {**fuentes_actuales, **row['caracteristicas_fuente']}
                        if fuentes_nuevas != fuentes_actuales:
                            cambios['caracteristicas_fuente'] = fuentes_nuevas

                        caracteristicas = next(
                            (
                                producto.get('caracteristicas_cafe') or {}
                                for producto in catalogo
                                if producto['url_detalle'] == url_detalle
                            ),
                            {},
                        )
                        notas_cambiaron = False
                        if caracteristicas.get('notas_cata_mencionadas'):
                            claves_nuevas = {
                                note['clave_normalizada']
                                for note in caracteristicas.get('notas_cata', [])
                            }
                            claves_actuales = {
                                relation.nota.clave_normalizada
                                for relation in producto_existente.notas_cata
                            }
                            notas_cambiaron = claves_nuevas != claves_actuales
                        if len(cambios) > 1 or notas_cambiaron:
                            cambios['fecha_actualizacion'] = fecha_actual
                            producto_rows_actualizar.append(cambios)
                    else:
                        productos_agregados += 1
                        producto_rows_nuevos.append(row)

                if producto_rows_nuevos:
                    self._bulk_insert_batch(session, Producto, producto_rows_nuevos)

                if producto_rows_actualizar:
                    self._bulk_update_batch(session, Producto, producto_rows_actualizar)

                producto_ids = self._ids_por_columna(
                    session, Producto, 'url_detalle', [row['url_detalle'] for row in productos_a_insertar]
                )

                notas_por_clave = {}
                productos_con_notas_declaradas = {}
                for prod_data in catalogo:
                    caracteristicas = prod_data.get('caracteristicas_cafe') or {}
                    if not caracteristicas.get('notas_cata_mencionadas'):
                        continue
                    product_id = producto_ids.get(prod_data['url_detalle'])
                    if product_id is None:
                        continue
                    productos_con_notas_declaradas[product_id] = caracteristicas.get('notas_cata', [])
                    for note in caracteristicas.get('notas_cata', []):
                        notas_por_clave[note['clave_normalizada']] = note

                if productos_con_notas_declaradas:
                    notas_existentes = {
                        note.clave_normalizada: note
                        for note in session.query(NotaCata)
                        .filter(NotaCata.clave_normalizada.in_(list(notas_por_clave)))
                        .all()
                    } if notas_por_clave else {}
                    for key, note in notas_por_clave.items():
                        if key not in notas_existentes:
                            session.add(NotaCata(
                                clave_normalizada=key,
                                nombre=note['nombre'],
                            ))
                    if notas_por_clave:
                        session.flush()
                        notas_existentes.update({
                            note.clave_normalizada: note
                            for note in session.query(NotaCata)
                            .filter(NotaCata.clave_normalizada.in_(list(notas_por_clave)))
                            .all()
                        })

                    notas_ids = {key: note.id for key, note in notas_existentes.items()}
                    for product_id, product_notes in productos_con_notas_declaradas.items():
                        session.query(ProductoNotaCata).filter(
                            ProductoNotaCata.producto_id == product_id
                        ).delete(synchronize_session=False)
                        session.bulk_insert_mappings(
                            ProductoNotaCata,
                            [
                                {
                                    'producto_id': product_id,
                                    'nota_id': notas_ids[note['clave_normalizada']],
                                    'texto_origen': note['texto_origen'],
                                    'confianza': note['confianza'],
                                    'version_extractor': note.get('version_extractor', 'unknown'),
                                }
                                for note in product_notes
                            ],
                        )
                    session.commit()

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
                            'es_estimado': var_data.get('es_estimado', True),
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
                                'precio_por_kilo', 'es_estimado', 'disponible',
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

            ids_eliminados = [
                producto.id for producto in productos_existentes
                if producto.activo and producto.id not in productos_encontrados_ids
            ]
            productos_eliminados = len(ids_eliminados)
            if ids_eliminados:
                session.bulk_update_mappings(
                    Producto,
                    [
                        {
                            'id': producto_id,
                            'activo': False,
                            'fecha_actualizacion': fecha_actual,
                        }
                        for producto_id in ids_eliminados
                    ],
                )
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

    def guardar_cafes_cascada(
        self,
        catalogo_cascada: List[Dict[str, Any]],
        tienda_id: int,
        batch_size: int = 30,
    ) -> Dict[str, int]:
        """
        Persiste los cafés y ofertas normalizados por el pipeline en cascada
        con procesamiento por lotes (20-50 items) para PostgreSQL / Supabase.
        """
        session = self.SessionLocal()
        fecha_actual = _utcnow()
        cafes_agregados = 0
        cafes_actualizados = 0
        ofertas_guardadas = 0

        try:
            for i in range(0, len(catalogo_cascada), batch_size):
                lote = catalogo_cascada[i:i + batch_size]
                for item in lote:
                    # 1. Obtener o crear Café
                    nombre = item.get("nombre", "").strip()
                    origen = item.get("origen")
                    hash_desc = item.get("hash_descripcion")

                    cafe = None
                    if hash_desc:
                        cafe = session.query(Cafe).filter(Cafe.hash_descripcion == hash_desc).first()
                    if not cafe:
                        cafe = session.query(Cafe).filter(
                            Cafe.nombre == nombre,
                            Cafe.origen == origen,
                        ).first()

                    if not cafe:
                        cafe = Cafe(
                            nombre=nombre,
                            origen=origen,
                            finca_productor=item.get("finca_productor"),
                            variedad=item.get("variedad"),
                            proceso=item.get("proceso"),
                            lote=item.get("lote"),
                            notas_cata=item.get("notas_cata", []),
                            notas_normalizadas=item.get("notas_normalizadas", []),
                            hash_descripcion=hash_desc,
                            fecha_creacion=fecha_actual,
                            fecha_actualizacion=fecha_actual,
                        )
                        session.add(cafe)
                        session.flush()
                        cafes_agregados += 1
                    else:
                        # Actualizar atributos si cambiaron o se enriquecieron
                        cambiado = False
                        for attr in ["finca_productor", "variedad", "proceso", "lote"]:
                            val = item.get(attr)
                            if val and getattr(cafe, attr) != val:
                                setattr(cafe, attr, val)
                                cambiado = True
                        if item.get("notas_cata") and cafe.notas_cata != item.get("notas_cata"):
                            cafe.notas_cata = item.get("notas_cata")
                            cambiado = True
                        if item.get("notas_normalizadas") and cafe.notas_normalizadas != item.get("notas_normalizadas"):
                            cafe.notas_normalizadas = item.get("notas_normalizadas")
                            cambiado = True
                        if hash_desc and cafe.hash_descripcion != hash_desc:
                            cafe.hash_descripcion = hash_desc
                            cambiado = True
                        if cambiado:
                            cafe.fecha_actualizacion = fecha_actual
                            cafes_actualizados += 1

                    # 2. Guardar Ofertas de Tienda vinculadas al Café
                    ofertas = item.get("ofertas", [])
                    for of in ofertas:
                        link = of.get("link_detalle")
                        if not link:
                            continue

                        oferta = session.query(OfertaTienda).filter(
                            OfertaTienda.link_detalle == link
                        ).first()

                        if not oferta:
                            oferta = OfertaTienda(
                                cafe_id=cafe.id,
                                tienda_id=tienda_id,
                                precio_actual=of.get("precio_actual", 0),
                                formato_gramos=of.get("formato_gramos", 250),
                                precio_por_kilo=of.get("precio_por_kilo", 0.0),
                                es_estimado=of.get("es_estimado", True),
                                link_detalle=link,
                                disponible=of.get("disponible", True),
                                ultima_actualizacion=fecha_actual,
                            )
                            session.add(oferta)
                        else:
                            oferta.cafe_id = cafe.id
                            oferta.precio_actual = of.get("precio_actual", oferta.precio_actual)
                            oferta.formato_gramos = of.get("formato_gramos", oferta.formato_gramos)
                            oferta.precio_por_kilo = of.get("precio_por_kilo", oferta.precio_por_kilo)
                            oferta.es_estimado = of.get("es_estimado", oferta.es_estimado)
                            oferta.disponible = of.get("disponible", oferta.disponible)
                            oferta.ultima_actualizacion = fecha_actual

                        ofertas_guardadas += 1

                session.commit()

            return {
                "cafes_agregados": cafes_agregados,
                "cafes_actualizados": cafes_actualizados,
                "ofertas_guardadas": ofertas_guardadas,
            }
        except Exception as e:
            try:
                session.rollback()
            except Exception:
                pass
            logging.error(f"❌ Error al persistir lote en cascada: {e}")
            raise
        finally:
            session.close()

