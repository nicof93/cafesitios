from dataclasses import dataclass
from typing import Optional

@dataclass
class VariantDomain:
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

@dataclass
class CoffeeProductDomain:
    id: int
    tienda: str
    nombre: str
    url_detalle: str
    imagen: Optional[str]
    descripcion: Optional[str]
    variante_mas_barata: VariantDomain
    categoria: str = 'cafe'
    oculto_catalogo: bool = False
    tienda_id: Optional[int] = None
    tienda_telefono_whatsapp: Optional[str] = None
    envio_gratis_monto: Optional[int] = None
    retiro_en_tienda: bool = False
    dias_tueste: Optional[str] = None
    fecha_ultimo_tueste: Optional[str] = None


@dataclass
class TiendaCatalogoDomain:
    id: Optional[int]
    tienda_id: int
    url_catalogo: str
    etiqueta: Optional[str] = None
    activa: bool = True


@dataclass
class TiendaDomain:
    id: int
    nombre: str
    url_base: str
    plataforma: str
    activo: bool = True
    catalogos: list[TiendaCatalogoDomain] = None

    def __post_init__(self):
        if self.catalogos is None:
            self.catalogos = []


