import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, 
    Numeric, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.dialects.postgresql import insert

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
        self.engine = create_engine(url_final, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def inicializar_db(self):
        logging.info("Inicializando esquema en PostgreSQL (psycopg3)...")
        Base.metadata.create_all(bind=self.engine)
        logging.info("✅ Tablas sincronizadas correctamente.")

    def guardar_catalogo(self, catalogo: List[Dict[str, Any]]):
        session = self.SessionLocal()
        try:
            total_productos = 0
            total_variantes = 0
            total_historial = 0
            fecha_actual = datetime.utcnow()

            for prod_data in catalogo:
                nombre_tienda = prod_data['tienda']
                tienda = session.query(Tienda).filter_by(nombre=nombre_tienda).first()
                if not tienda:
                    tienda = Tienda(nombre=nombre_tienda, url_base=prod_data['url_detalle'])
                    session.add(tienda)
                    session.flush()

                stmt_prod = insert(Producto).values(
                    tienda_id=tienda.id,
                    nombre=prod_data['nombre'],
                    url_detalle=prod_data['url_detalle'],
                    imagen=prod_data['imagen'],
                    descripcion=prod_data['descripcion'],
                    fecha_actualizacion=fecha_actual
                ).on_conflict_do_update(
                    index_elements=['url_detalle'],
                    set_={
                        'nombre': prod_data['nombre'],
                        'imagen': prod_data['imagen'],
                        'descripcion': prod_data['descripcion'],
                        'fecha_actualizacion': fecha_actual
                    }
                ).returning(Producto.id)

                res_prod = session.execute(stmt_prod)
                producto_id = res_prod.scalar()
                total_productos += 1

                for var_data in prod_data.get('variantes', []):
                    stmt_var = insert(Variante).values(
                        producto_id=producto_id,
                        id_variante_externo=var_data['id_variante_externo'],
                        opcion=var_data['opcion'],
                        formato_gramos=var_data['formato_gramos'],
                        precio_clp=var_data['precio_clp'],
                        precio_original_clp=var_data['precio_original_clp'],
                        en_oferta=var_data['en_oferta'],
                        descuento_porcentaje=var_data['descuento_porcentaje'],
                        precio_por_kilo=var_data['precio_por_kilo'],
                        disponible=var_data['disponible'],
                        fecha_actualizacion=fecha_actual
                    ).on_conflict_do_update(
                        index_elements=['id_variante_externo'],
                        set_={
                            'precio_clp': var_data['precio_clp'],
                            'precio_original_clp': var_data['precio_original_clp'],
                            'en_oferta': var_data['en_oferta'],
                            'descuento_porcentaje': var_data['descuento_porcentaje'],
                            'precio_por_kilo': var_data['precio_por_kilo'],
                            'disponible': var_data['disponible'],
                            'fecha_actualizacion': fecha_actual
                        }
                    ).returning(Variante.id)

                    res_var = session.execute(stmt_var)
                    variante_id = res_var.scalar()
                    total_variantes += 1

                    historial_entry = HistorialPrecio(
                        variante_id=variante_id,
                        precio_clp=var_data['precio_clp'],
                        precio_original_clp=var_data['precio_original_clp'],
                        precio_por_kilo=var_data['precio_por_kilo'],
                        en_oferta=var_data['en_oferta'],
                        descuento_porcentaje=var_data['descuento_porcentaje'],
                        disponible=var_data['disponible'],
                        fecha_registro=fecha_actual
                    )
                    session.add(historial_entry)
                    total_historial += 1

            session.commit()
            logging.info(f"💾 Persistencia exitosa: {total_productos} productos, {total_variantes} variantes y {total_historial} registros históricos.")

        except Exception as e:
            session.rollback()
            logging.error(f"❌ Error al guardar en la base de datos: {e}")
        finally:
            session.close()
