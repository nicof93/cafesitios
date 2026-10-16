"""Caso de Uso: Recomendador Interactivo por Perfil de Taza (CU-07 / Quiz).

Evalúa y puntúa cafés según:
1. Método de preparación (Espresso, Filtro/Goteo, Prensa Francesa, Italiana/Moka)
2. Perfil de sabor (Frutal/Cítrico, Achocolatado/Nuez, Floral, Balanceado)
3. Nivel de tueste (Claro, Medio, Oscuro)
Regla: Penaliza con -50 puntos los productos agotados.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from sqlalchemy.orm import Session, joinedload, selectinload
from db.database import Producto, Tienda, Variante, ProductoNotaCata
from domain.search_normalizer import strip_accents


@dataclass
class RecommendedProductDTO:
    id: int
    nombre: str
    tienda: str
    url_detalle: str
    imagen: Optional[str]
    proceso: Optional[str]
    pais_origen: Optional[str]
    variedad: Optional[str]
    tueste: Optional[str]
    precio_clp: int
    precio_por_kilo: float
    es_estimado: bool
    disponible: bool
    puntaje_coincidencia: int
    motivo_recomendacion: str


FLAVOR_KEYWORDS: Dict[str, List[str]] = {
    "frutal": [
        "frutal", "citrico", "limon", "naranja", "berries", "fruta", "arandanos",
        "manzana", "durazno", "maracuya", "frutos rojos", "cereza", "frambuesa", "uva"
    ],
    "achocolatado": [
        "chocolate", "cacao", "nuez", "avellana", "almendra", "caramelo", "toffee",
        "panela", "chocolatoso", "vainilla", "azucar morena", "melaza"
    ],
    "floral": [
        "floral", "jazmin", "flores", "rosa", "geisha", "gesha", "lavanda", "azahar", "te blanco"
    ],
    "balanceado": [
        "balanceado", "equilibrado", "dulce", "suave", "miel", "honey", "lavado", "redondo"
    ],
}


class RecommendProductsUseCase:
    def __init__(self, session: Session):
        self.session = session

    def execute(
        self,
        metodo: Optional[str] = None,
        perfil_sabor: Optional[str] = None,
        tueste: Optional[str] = None,
        limit: int = 6,
    ) -> List[RecommendedProductDTO]:
        products = (
            self.session.query(Producto)
            .join(Tienda, Producto.tienda_id == Tienda.id)
            .options(
                joinedload(Producto.tienda),
                selectinload(Producto.variantes),
                selectinload(Producto.notas_cata).joinedload(ProductoNotaCata.nota),
            )
            .filter(
                Producto.activo.is_(True),
                Tienda.activo.is_(True),
            )
            .all()
        )

        scored: List[RecommendedProductDTO] = []

        norm_metodo = strip_accents(metodo or "")
        norm_sabor = strip_accents(perfil_sabor or "")
        norm_tueste = strip_accents(tueste or "")

        for prod in products:
            if not prod.variantes:
                continue

            cheapest_var = min(prod.variantes, key=lambda v: (not v.disponible, v.precio_por_kilo))
            has_stock = any(v.disponible for v in prod.variantes)

            score = 50
            reasons = []

            # 1. Disponibilidad (Penalización de -50 si agotado)
            if not has_stock:
                score -= 50
            else:
                score += 10

            # Texto combinado del producto para detección
            notas_text = " ".join(r.nota.nombre for r in prod.notas_cata)
            all_text = strip_accents(f"{prod.nombre} {prod.descripcion or ''} {prod.proceso or ''} {notas_text}")

            # 2. Evaluación Perfil de Sabor (+35 pts)
            matched_flavor = False
            for category_key, keywords in FLAVOR_KEYWORDS.items():
                if category_key in norm_sabor:
                    if any(kw in all_text for kw in keywords):
                        score += 35
                        matched_flavor = True
                        reasons.append(f"Afinidad con perfil {perfil_sabor}")
                        break

            # 3. Evaluación Nivel de Tueste (+25 pts)
            if norm_tueste:
                prod_tueste = strip_accents(prod.tueste or "")
                if norm_tueste in prod_tueste or norm_tueste in all_text:
                    score += 25
                    reasons.append(f"Tueste adecuado ({tueste})")

            # 4. Evaluación Método de Preparación (+20 pts)
            if "espresso" in norm_metodo:
                if any(k in all_text for k in ["espresso", "chocolate", "cremoso", "cacao", "natural", "medio"]):
                    score += 20
                    reasons.append("Ideal para extracción espresso")
            elif any(m in norm_metodo for m in ["filtro", "goteo", "v60", "chemex"]):
                if any(k in all_text for k in ["filtro", "floral", "frutal", "lavado", "claro", "acidez"]):
                    score += 20
                    reasons.append("Excelente claridad para métodos de filtro")
            elif "prensa" in norm_metodo or "french" in norm_metodo:
                if any(k in all_text for k in ["cuerpo", "achocolatado", "medio", "nuez"]):
                    score += 20
                    reasons.append("Buen cuerpo para prensa francesa")
            elif "moka" in norm_metodo or "italiana" in norm_metodo:
                if any(k in all_text for k in ["intenso", "chocolate", "medio", "oscuro"]):
                    score += 20
                    reasons.append("Intensidad adecuada para cafetera italiana")

            motivo = ". ".join(reasons) if reasons else "Café equilibrado con gran perfil de taza"

            scored.append(
                RecommendedProductDTO(
                    id=prod.id,
                    nombre=prod.nombre,
                    tienda=prod.tienda.nombre,
                    url_detalle=prod.url_detalle,
                    imagen=prod.imagen,
                    proceso=prod.proceso,
                    pais_origen=prod.pais_origen,
                    variedad=prod.variedad,
                    tueste=prod.tueste,
                    precio_clp=cheapest_var.precio_clp,
                    precio_por_kilo=float(cheapest_var.precio_por_kilo),
                    es_estimado=bool(getattr(cheapest_var, 'es_estimado', True)),
                    disponible=has_stock,
                    puntaje_coincidencia=max(0, score),
                    motivo_recomendacion=motivo,
                )
            )

        scored.sort(key=lambda p: (p.disponible, p.puntaje_coincidencia, -p.precio_por_kilo), reverse=True)
        return scored[:limit]

