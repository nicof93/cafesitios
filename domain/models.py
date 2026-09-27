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

@dataclass
class CoffeeProductDomain:
    id: int
    tienda: str
    nombre: str
    url_detalle: str
    imagen: Optional[str]
    descripcion: Optional[str]
    variante_mas_barata: VariantDomain
