from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class VariantResponse(BaseModel):
    id_externo: str
    opcion: str
    formato_gramos: int
    precio_clp: int
    precio_original_clp: int
    en_oferta: bool
    descuento_porcentaje: int
    precio_por_kilo: float
    disponible: bool

class CheapestProductResponse(BaseModel):
    id: int
    tienda: str
    nombre: str
    url_detalle: str
    imagen: Optional[str] = None
    variante: VariantResponse

class PaginatedProductsResponse(BaseModel):
    total_items: int
    criterio_orden: str
    data: List[CheapestProductResponse]

class ProductVariantDetailResponse(BaseModel):
    id_externo: str
    opcion: str
    formato_gramos: int
    precio_clp: int
    precio_original_clp: int
    en_oferta: bool
    descuento_porcentaje: int
    precio_por_kilo: float
    disponible: bool
    fecha_actualizacion: Optional[datetime] = None

class ProductDetailResponse(BaseModel):
    id: int
    tienda: str
    tienda_url: str
    nombre: str
    descripcion: Optional[str] = None
    url_detalle: str
    imagen: Optional[str] = None
    fecha_actualizacion: Optional[datetime] = None
    variantes: List[ProductVariantDetailResponse]
