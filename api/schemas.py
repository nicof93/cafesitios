from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any

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
    historial_precios: List["ProductPriceHistoryResponse"] = []

class ProductPriceHistoryResponse(BaseModel):
    fecha_registro: datetime
    precio_clp: int
    precio_por_kilo: float

class ProductTastingNoteResponse(BaseModel):
    nombre: str
    clave_normalizada: str
    texto_origen: str
    confianza: float
    version_extractor: str

class ProductDetailResponse(BaseModel):
    id: int
    tienda: str
    tienda_url: str
    nombre: str
    descripcion: Optional[str] = None
    url_detalle: str
    imagen: Optional[str] = None
    fecha_actualizacion: Optional[datetime] = None
    proceso: Optional[str] = None
    finca: Optional[str] = None
    variedad: Optional[str] = None
    elevacion_min_msnm: Optional[int] = None
    elevacion_max_msnm: Optional[int] = None
    cosecha: Optional[str] = None
    fermentacion_tipo: Optional[str] = None
    fermentacion_horas: Optional[float] = None
    caracteristicas_fuente: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    notas_cata: List[ProductTastingNoteResponse] = Field(default_factory=list)
    variantes: List[ProductVariantDetailResponse]
