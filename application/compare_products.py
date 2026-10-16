"""Caso de Uso: Comparativa Directa Entre Productos (CU-03).

Aplica la regla RN-03 (Deduplicación por Gramaje):
Las variantes de molienda se ignoran y se deduplican por formato_gramos,
seleccionando la opción de menor precio para cada gramaje.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload, selectinload
from db.database import Producto, Tienda, Variante, ProductoNotaCata


@dataclass
class DeduplicatedVariantDTO:
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


@dataclass
class CompareProductItemDTO:
    id: int
    nombre: str
    tienda: str
    tienda_url: str
    url_detalle: str
    imagen: Optional[str]
    proceso: Optional[str]
    pais_origen: Optional[str]
    finca: Optional[str]
    variedad: Optional[str]
    notas_cata: List[str]
    variantes_por_gramaje: List[DeduplicatedVariantDTO]


class CompareProductsUseCase:
    def __init__(self, session: Session):
        self.session = session

    def execute(self, product_ids: List[int]) -> List[CompareProductItemDTO]:
        if not product_ids:
            return []

        # Limitar a máximo 4 productos para comparación
        ids_to_query = list(dict.fromkeys(product_ids))[:4]

        products = (
            self.session.query(Producto)
            .join(Tienda, Producto.tienda_id == Tienda.id)
            .options(
                joinedload(Producto.tienda),
                selectinload(Producto.variantes),
                selectinload(Producto.notas_cata).joinedload(ProductoNotaCata.nota),
            )
            .filter(
                Producto.id.in_(ids_to_query),
                Producto.activo.is_(True),
                Tienda.activo.is_(True),
            )
            .all()
        )

        results: List[CompareProductItemDTO] = []
        for prod in products:
            # RN-03: Deduplicación por gramaje
            # Agrupar variantes por formato_gramos y seleccionar la más barata
            variantes_por_peso: Dict[int, Variante] = {}
            for var in prod.variantes:
                peso = var.formato_gramos
                if peso not in variantes_por_peso:
                    variantes_por_peso[peso] = var
                else:
                    if var.precio_clp < variantes_por_peso[peso].precio_clp:
                        variantes_por_peso[peso] = var

            deduped_variants = []
            for peso in sorted(variantes_por_peso.keys()):
                v = variantes_por_peso[peso]
                deduped_variants.append(
                    DeduplicatedVariantDTO(
                        id_externo=v.id_variante_externo,
                        formato_gramos=v.formato_gramos,
                        opcion_resumida=f"{v.formato_gramos}g",
                        precio_clp=v.precio_clp,
                        precio_original_clp=v.precio_original_clp,
                        precio_por_kilo=float(v.precio_por_kilo),
                        en_oferta=v.en_oferta,
                        descuento_porcentaje=v.descuento_porcentaje,
                        es_estimado=bool(getattr(v, 'es_estimado', True)),
                        disponible=v.disponible,
                    )
                )

            notas = [
                rel.nota.nombre
                for rel in sorted(prod.notas_cata, key=lambda r: r.nota.clave_normalizada)
            ]

            results.append(
                CompareProductItemDTO(
                    id=prod.id,
                    nombre=prod.nombre,
                    tienda=prod.tienda.nombre,
                    tienda_url=prod.tienda.url_base,
                    url_detalle=prod.url_detalle,
                    imagen=prod.imagen,
                    proceso=prod.proceso,
                    pais_origen=prod.pais_origen,
                    finca=prod.finca,
                    variedad=prod.variedad,
                    notas_cata=notas,
                    variantes_por_gramaje=deduped_variants,
                )
            )

        return results

