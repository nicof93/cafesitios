from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any

class VariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_externo: str
    opcion: str
    formato_gramos: int
    precio_clp: int
    precio_original_clp: int
    en_oferta: bool
    descuento_porcentaje: int
    precio_por_kilo: float
    disponible: bool
    es_estimado: bool = True

class CheapestProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tienda: str
    nombre: str
    url_detalle: str
    imagen: Optional[str] = None
    categoria: str = "cafe"
    variante: VariantResponse


class PaginatedProductsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_items: int
    criterio_orden: str
    data: List[CheapestProductResponse]

class ProductVariantDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_externo: str
    opcion: str
    formato_gramos: int
    precio_clp: int
    precio_original_clp: int
    en_oferta: bool
    descuento_porcentaje: int
    precio_por_kilo: float
    disponible: bool
    es_estimado: bool = True
    fecha_actualizacion: Optional[datetime] = None
    historial_precios: List["ProductPriceHistoryResponse"] = []

class ProductPriceHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    fecha_registro: datetime
    precio_clp: int
    precio_por_kilo: float

class ProductTastingNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nombre: str
    clave_normalizada: str
    texto_origen: str
    confianza: float
    version_extractor: str

class ProductDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tienda: str
    tienda_url: str
    nombre: str
    descripcion: Optional[str] = None
    url_detalle: str
    imagen: Optional[str] = None
    fecha_actualizacion: Optional[datetime] = None
    proceso: Optional[str] = None
    tueste: Optional[str] = None
    puntuacion_sca: Optional[float] = None
    escala_agtron: Optional[int] = None
    pais_origen: Optional[str] = None
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

# --- CU-03: Comparativa Side-by-Side ---
class CompareVariantItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_externo: str
    formato_gramos: int
    opcion_resumida: str
    precio_clp: int
    precio_original_clp: int
    precio_por_kilo: float
    en_oferta: bool
    descuento_porcentaje: int
    es_estimado: bool
    disponible: bool

class CompareProductItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    tienda: str
    tienda_url: str
    url_detalle: str
    imagen: Optional[str] = None
    proceso: Optional[str] = None
    pais_origen: Optional[str] = None
    finca: Optional[str] = None
    variedad: Optional[str] = None
    notas_cata: List[str] = []
    variantes_por_gramaje: List[CompareVariantItem]

class CompareResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    productos: List[CompareProductItem]

# --- CU-04: Comparador de Disponibilidad ("Comprar con...") ---
class ProductMatchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tienda: str
    nombre: str
    url_detalle: str
    imagen: Optional[str] = None
    precio_clp: int
    precio_por_kilo: float
    formato_gramos: int
    diferencia_precio_clp: int
    diferencia_kilo_clp: float
    es_mas_barato: bool

class ProductMatchesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    producto_origen_id: int
    coincidencias: List[ProductMatchItem]

# --- CU-07: Recomendador / Quiz ---
class RecommendationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    tienda: str
    url_detalle: str
    imagen: Optional[str] = None
    proceso: Optional[str] = None
    pais_origen: Optional[str] = None
    variedad: Optional[str] = None
    tueste: Optional[str] = None
    precio_clp: int
    precio_por_kilo: float
    es_estimado: bool
    disponible: bool
    puntaje_coincidencia: int
    motivo_recomendacion: str

class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    recomendaciones: List[RecommendationItem]

# --- CU-08: Bitácora de Recetas y Catación SCA ---
class ScaCuppingAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    fragancia_aroma: Optional[float] = Field(None, ge=1.0, le=10.0, description="Fragancia / Aroma (1 a 10)")
    sabor: Optional[float] = Field(None, ge=1.0, le=10.0, description="Sabor (1 a 10)")
    retrogusto: Optional[float] = Field(None, ge=1.0, le=10.0, description="Retrogusto / Aftertaste (1 a 10)")
    acidez: Optional[float] = Field(None, ge=1.0, le=10.0, description="Acidez (1 a 10)")
    cuerpo: Optional[float] = Field(None, ge=1.0, le=10.0, description="Cuerpo (1 a 10)")
    balance: Optional[float] = Field(None, ge=1.0, le=10.0, description="Balance / Equilibrio (1 a 10)")
    uniformidad: Optional[float] = Field(None, ge=1.0, le=10.0, description="Uniformidad (1 a 10)")
    taza_limpia: Optional[float] = Field(None, ge=1.0, le=10.0, description="Taza Limpia / Clean Cup (1 a 10)")
    dulzor: Optional[float] = Field(None, ge=1.0, le=10.0, description="Dulzor / Sweetness (1 a 10)")
    puntaje_global: Optional[float] = Field(None, ge=1.0, le=10.0, description="Puntuación Global del Catador (1 a 10)")
    puntuacion_total_sca: Optional[float] = Field(None, ge=0.0, le=100.0, description="Puntuación total acumulada (0 a 100)")

class RecipeCreateRequest(BaseModel):
    dispositivo_uuid: str = Field(..., min_length=10, max_length=64)
    nombre_receta: str = Field(..., min_length=2, max_length=150)
    metodo: str = Field(..., min_length=2, max_length=100)
    dosis_cafe_g: float = Field(..., gt=0, le=500)
    agua_ml: float = Field(..., gt=0, le=5000)
    producto_id: Optional[int] = None
    ratio: Optional[str] = None
    molino_usado: Optional[str] = None
    grosor_molienda: Optional[str] = None
    temperatura_c: Optional[int] = Field(None, ge=50, le=100)
    tiempo_total_s: Optional[int] = Field(None, ge=1, le=1800)
    calificacion_1_10: Optional[int] = Field(None, ge=1, le=10)
    reintentar: bool = True
    notas_catado: Optional[str] = None
    catacion_sca: Optional[ScaCuppingAttributes] = None
    puntuacion_sca_total: Optional[float] = None
    website_hp: Optional[str] = None  # Capa 3: Honeypot Anti-Bot

class RecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dispositivo_uuid: str
    nombre_receta: str
    metodo: str
    dosis_cafe_g: float
    agua_ml: float
    ratio: Optional[str] = None
    molino_usado: Optional[str] = None
    grosor_molienda: Optional[str] = None
    temperatura_c: Optional[int] = None
    tiempo_total_s: Optional[int] = None
    calificacion_1_10: Optional[int] = None
    reintentar: bool
    notas_catado: Optional[str] = None
    catacion_sca: Optional[Dict[str, Any]] = None
    puntuacion_sca_total: Optional[float] = None
    fecha_creacion: datetime

# --- CU-11: Módulo Flotante de Feedback ---
class FeedbackCreateRequest(BaseModel):
    categoria: str = Field(..., min_length=2, max_length=50)
    mensaje: str = Field(..., min_length=5, max_length=2000)
    contacto_opcional: Optional[str] = Field(None, max_length=150)
    website_hp: Optional[str] = None  # Honeypot

class FeedbackResponse(BaseModel):
    status: str
    message: str

# --- Telemetría y Clics ---
class TelemetryEventRequest(BaseModel):
    tipo_evento: str = Field(..., min_length=2, max_length=50)
    producto_id: Optional[int] = None
    variante_id: Optional[int] = None
    metadata_evento: Dict[str, Any] = Field(default_factory=dict)

class TelemetryEventResponse(BaseModel):
    status: str
    event_id: int
