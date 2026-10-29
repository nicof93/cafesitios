from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

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
    tienda_id: Optional[int] = None
    tienda_telefono_whatsapp: Optional[str] = None
    nombre: str
    url_detalle: str
    imagen: Optional[str] = None
    categoria: str = "cafe"
    oculto_catalogo: bool = False
    envio_gratis_monto: Optional[int] = None
    retiro_en_tienda: bool = False
    dias_tueste: Optional[str] = None
    fecha_ultimo_tueste: Optional[str] = None
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
    estado: str = "confirmada"
    es_fuera_de_rueda: bool = False

class ProductRecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre_receta: str
    metodo: str
    dosis_cafe_g: float
    agua_ml: float
    ratio: Optional[str] = None
    molino_usado: Optional[str] = None
    grosor_molienda: Optional[str] = None
    temperatura_c: Optional[int] = None
    tiempo_total_s: Optional[int] = None
    notas_catado: Optional[str] = None
    es_borrador: bool = False
    pasos: Optional[List[str]] = None
    autor_tipo: str = "tostaduria"
    tienda_nombre: Optional[str] = None
    fecha_creacion: Optional[datetime] = None

class ProductDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tienda: str
    tienda_id: Optional[int] = None
    tienda_telefono_whatsapp: Optional[str] = None
    tienda_url: str
    tienda_sitio_oficial: Optional[str] = None
    sitio_oficial: Optional[str] = None
    tienda_catalogo_url: Optional[str] = None
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
    descripcion_resumida: Optional[str] = None
    resumen_corto: Optional[str] = None
    caracteristicas_fuente: Dict[str, Any] = Field(default_factory=dict)
    notas_cata: List[ProductTastingNoteResponse] = Field(default_factory=list)
    notas_confirmadas: List[ProductTastingNoteResponse] = Field(default_factory=list)
    notas_sugeridas: List[ProductTastingNoteResponse] = Field(default_factory=list)
    variantes: List[ProductVariantDetailResponse]
    recetas: List[ProductRecipeResponse] = Field(default_factory=list)
    oculto_catalogo: bool = False
    activo: bool = True

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
    tienda_sitio_oficial: Optional[str] = None
    tienda_catalogo_url: Optional[str] = None
    url_detalle: str
    imagen: Optional[str] = None
    proceso: Optional[str] = None
    pais_origen: Optional[str] = None
    finca: Optional[str] = None
    variedad: Optional[str] = None
    tueste: Optional[str] = None
    escala_agtron: Optional[int] = None
    elevacion_min_msnm: Optional[int] = None
    elevacion_max_msnm: Optional[int] = None
    altura_msnm: Optional[str] = None
    puntuacion_sca: Optional[float] = None
    atributos_organolepticos: Dict[str, int] = Field(default_factory=dict)
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
    variante: Optional[VariantResponse] = None

class ProductMatchesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    producto_origen_id: int
    coincidencias: List[ProductMatchItem]

# --- Mayores Caídas de Precio de la Semana (Ofertas Verificadas) ---
class WeeklyPriceDropItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    oferta_id: int
    producto_id: int
    nombre_producto: str
    tienda: str
    url_tienda: Optional[str] = None
    imagen_url: Optional[str] = None
    formato_gramos: int
    precio_anterior: int
    precio_actual: int
    precio_por_kilo: float
    monto_rebaja: int
    porcentaje_descuento: int
    link_detalle: str
    fecha_cambio: Optional[datetime] = None

class WeeklyPriceDropsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total: int
    dias_evaluados: int
    ofertas: List[WeeklyPriceDropItem]

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
    formato_gramos: int = 250
    es_estimado: bool
    disponible: bool
    puntaje_coincidencia: int
    match_score: float = 0.85
    motivo_recomendacion: str
    notas_cata: List[str] = Field(default_factory=list)
    variante: Optional[Dict[str, Any]] = None

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

# --- Reporte de Sincronización y Analítica ---
class SyncPriceChangeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    variante_id: int
    nombre: str
    tienda: str
    formato_gramos: int = 250
    formato: str = "250g"
    precio_anterior: int
    precio_nuevo: int
    precio_actual: int
    diferencia_clp: int
    porcentaje_variacion: float
    precio_kilo_anterior: float = 0.0
    precio_kilo_nuevo: float = 0.0
    diferencia_kilo_clp: float = 0.0
    tipo_cambio: Literal["SUBIO", "BAJO"]
    url_detalle: str
    fecha_cambio: Optional[datetime] = None

class SyncNewProductItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    tienda: str
    formato_gramos: int = 250
    formato: str = "250g"
    precio_clp: int
    precio_por_kilo: float
    origen: Optional[str] = None
    proceso: Optional[str] = None
    tueste: Optional[str] = None
    url_detalle: str
    imagen: Optional[str] = None
    fecha_creacion: Optional[datetime] = None

class SyncMetricsSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_nuevos: int = 0
    total_subieron_precio: int = 0
    total_bajaron_precio: int = 0
    total_cambios_precio: int = 0
    porcentaje_variacion_global: float = 0.0
    ahorro_total_clp: int = 0
    porcentaje_ahorro_promedio: float = 0.0
    total_ofertas_monitoreadas: int = 0
    total_productos_catalogados: int = 0

class SyncCurrentSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    fecha_ultima_sincronizacion: Optional[datetime] = None
    ultima_sincronizacion: Optional[datetime] = None
    estado: str = "OK"
    total_nuevos: int = 0
    total_subieron_precio: int = 0
    total_bajaron_precio: int = 0
    total_cambios_precio: int = 0
    porcentaje_variacion_global: float = 0.0
    ahorro_total_clp: int = 0
    porcentaje_ahorro_promedio: float = 0.0
    total_ofertas_monitoreadas: int = 0
    total_productos_catalogados: int = 0
    metricas: SyncMetricsSummary = Field(default_factory=SyncMetricsSummary)
    productos_nuevos: List[SyncNewProductItem] = Field(default_factory=list)
    novedades: List[SyncNewProductItem] = Field(default_factory=list)
    cambios_precio: List[SyncPriceChangeItem] = Field(default_factory=list)
    productos_cambio_precio: List[SyncPriceChangeItem] = Field(default_factory=list)

class SyncHistoryLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fecha_ejecucion: datetime
    fecha: str
    hora: str
    duracion_estimada_segundos: float = 0.0
    duracion_estimada: str = "0.0s"
    estado: str = "OK"
    productos_nuevos: int = 0
    productos_actualizados: int = 0
    productos_con_cambio_precio: int = 0
    mensaje_error: Optional[str] = None

class PaginatedSyncHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    page: int = 1
    page_size: int = 20
    total_items: int = 0
    total_pages: int = 1
    items: List[SyncHistoryLogItem] = Field(default_factory=list)
    data: List[SyncHistoryLogItem] = Field(default_factory=list)
    historial: List[SyncHistoryLogItem] = Field(default_factory=list)

class MarketStoreDiscountSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nombre: Optional[str] = None
    descuento_promedio_porcentaje: float = 0.0
    total_ofertas_descuento: int = 0
    precio_promedio_kilo: float = 0.0
    cantidad_productos: int = 0

class MarketDistributionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    categoria: str
    cantidad: int
    porcentaje: float
    precio_promedio_kilo: float = 0.0

class MarketAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    precio_promedio_kilo: float = 0.0
    precio_minimo_kilo: float = 0.0
    precio_maximo_kilo: float = 0.0
    precio_promedio_bolsa_clp: int = 0
    total_variantes_analizadas: int = 0
    total_tiendas_activas: int = 0
    tienda_mejor_descuento: MarketStoreDiscountSummary = Field(default_factory=MarketStoreDiscountSummary)
    tiendas_mas_competitivas: List[MarketStoreDiscountSummary] = Field(default_factory=list)
    distribucion_tueste: List[MarketDistributionItem] = Field(default_factory=list)
    distribucion_proceso: List[MarketDistributionItem] = Field(default_factory=list)

# --- TRACCIÓN Y MÉTRICAS COMERCIALES GLOBALES DE TIENDAS ---

class StoreTractionMetricsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tienda_id: int
    nombre: str
    url_base: Optional[str] = None
    logo_url: Optional[str] = None
    telefono_whatsapp: Optional[str] = None
    activo: bool = True
    total_productos: int = 0
    clics_salientes: int = 0
    cafes_favoritos: int = 0
    en_matriz_comparativa: int = 0
    ventas_solicitadas_whatsapp_clp: int = 0
    pedidos_recibidos_whatsapp: int = 0
    ticket_promedio_whatsapp_clp: float = 0.0

class GlobalTractionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_clics_salientes: int = 0
    total_cafes_favoritos: int = 0
    total_en_matriz_comparativa: int = 0
    total_ventas_solicitadas_whatsapp_clp: int = 0
    total_pedidos_recibidos_whatsapp: int = 0
    total_tiendas_activas: int = 0
    tiendas_con_ventas_whatsapp: int = 0
    tiendas_con_clics: int = 0

class GlobalStoreTractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    resumen_global: GlobalTractionSummary = Field(default_factory=GlobalTractionSummary)
    tiendas: List[StoreTractionMetricsItem] = Field(default_factory=list)


class StoreDeleteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    mensaje: str
    tienda_id: int
    tienda_nombre: str
    exito: bool = True
