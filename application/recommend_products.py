"""Caso de Uso: Recomendador Interactivo por Perfil de Taza (CU-07 / Quiz).

Evalúa y puntúa cafés según:
1. Método de preparación (Espresso, Filtro/Goteo, Prensa Francesa, Italiana/Moka)
2. Perfil de sabor (Frutal/Cítrico, Achocolatado/Nuez, Floral, Balanceado)
3. Nivel de tueste (Claro, Medio, Oscuro)
Regla: Penaliza con -50 puntos los productos agotados.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload, selectinload
from db.database import Producto, Tienda, Variante, ProductoNotaCata
from domain.search_normalizer import classify_product_category, strip_accents
from core.normalizer import is_valid_tasting_note


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
    formato_gramos: int = 250
    match_score: float = 0.85
    notas_cata: List[str] = field(default_factory=list)


FLAVOR_KEYWORDS: Dict[str, List[str]] = {
    "frutal_floral": [
        "floral", "jazmin", "flores", "rosa", "geisha", "gesha", "lavanda", "azahar",
        "te blanco", "hibisco", "bergamota", "frutal", "berries", "frutos rojos",
        "frutilla", "frambuesa", "arandano", "mora", "cereza", "durazno", "maracuya",
        "mango", "tropical", "etiopia", "kenia", "natural", "anaerobico",
    ],
    "chocolate_nueces": [
        "chocolate", "cacao", "nuez", "nueces", "avellana", "almendra", "mani",
        "castana", "caramelo", "toffee", "panela", "chocolatoso", "vainilla",
        "azucar morena", "melaza", "dulce de leche", "manjar", "praline",
        "brasil", "colombia", "bourbon", "caturra",
    ],
    "citrico_balanceado": [
        "citrico", "limon", "lima", "naranja", "mandarina", "pomelo", "manzana",
        "balanceado", "equilibrado", "dulce", "suave", "miel", "honey", "lavado",
        "washed", "redondo", "limpio", "peru", "guatemala", "costa rica", "honduras",
    ],
    "especiado_intenso": [
        "especiado", "canela", "clavo", "cardamomo", "pimienta", "nuez moscada",
        "tabaco", "cedro", "madera", "vino", "vinico", "intenso", "cuerpo",
        "oscuro", "dark", "chocolate amargo", "cacao amargo", "ferment",
        "anaerobico", "maceracion", "blend", "espresso",
    ],
    "frutal": [
        "frutal", "citrico", "limon", "naranja", "berries", "fruta", "arandanos",
        "manzana", "durazno", "maracuya", "frutos rojos", "cereza", "frambuesa", "uva",
    ],
    "achocolatado": [
        "chocolate", "cacao", "nuez", "avellana", "almendra", "caramelo", "toffee",
        "panela", "chocolatoso", "vainilla", "azucar morena", "melaza",
    ],
    "floral": [
        "floral", "jazmin", "flores", "rosa", "geisha", "gesha", "lavanda", "azahar", "te blanco",
    ],
    "balanceado": [
        "balanceado", "equilibrado", "dulce", "suave", "miel", "honey", "lavado", "redondo",
    ],
}

ACIDITY_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "alta": {
        "positive": [
            "limon", "lima", "pomelo", "naranja", "mandarina", "citrico", "acidez",
            "brillante", "jugoso", "frambuesa", "arandano", "mora", "frutos rojos",
            "hibisco", "manzana verde", "lavado", "washed", "claro", "etiopia",
            "kenia", "geisha", "gesha", "sl28", "sidra",
        ],
        "negative": ["oscuro", "dark", "baja acidez", "intenso", "robusta", "italiano"],
    },
    "media": {
        "positive": [
            "balanceado", "equilibrado", "medio", "omni", "honey", "miel", "caramelo",
            "panela", "durazno", "naranja", "manzana", "cereza", "colombia", "peru",
            "guatemala", "costa rica", "honduras", "caturra", "bourbon", "castillo",
        ],
        "negative": ["muy oscuro"],
    },
    "baja": {
        "positive": [
            "chocolate", "cacao", "nuez", "avellana", "almendra", "mani", "toffee",
            "melaza", "cuerpo", "cremoso", "intenso", "oscuro", "dark", "medio-oscuro",
            "brasil", "blend", "espresso", "baja acidez", "suave",
        ],
        "negative": ["limon", "pomelo", "acidez brillante", "acidez alta", "muy claro"],
    },
}


class RecommendProductsUseCase:
    def __init__(self, session: Session):
        self.session = session

    def execute(
        self,
        metodo: Optional[str] = None,
        perfil_sabor: Optional[str] = None,
        tueste: Optional[str] = None,
        acidez: Optional[str] = None,
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
                Producto.oculto_catalogo.is_(False),
                Tienda.activo.is_(True),
            )
            .all()
        )

        norm_metodo = strip_accents(metodo or "")
        norm_sabor = strip_accents(perfil_sabor or "")
        norm_tueste = strip_accents(tueste or "")
        norm_acidez = strip_accents(acidez or "")

        profile_seed = sum(
            (idx + 1) * ord(ch)
            for idx, ch in enumerate(f"{norm_metodo}|{norm_sabor}|{norm_acidez}|{norm_tueste}")
        )

        scored_with_tiebreak: List[tuple[tuple, RecommendedProductDTO]] = []

        for prod in products:
            if not prod.variantes:
                continue
            if getattr(prod, "oculto_catalogo", False):
                continue
            if classify_product_category(prod.nombre) != "cafe":
                continue

            cheapest_var = min(prod.variantes, key=lambda v: (not v.disponible, v.precio_por_kilo))
            has_stock = any(v.disponible for v in prod.variantes)

            score = 45
            reasons: List[str] = []

            # 1. Disponibilidad (Penalización de -50 si agotado)
            if not has_stock:
                score -= 50
            else:
                score += 10

            valid_notes = [
                r.nota.nombre
                for r in prod.notas_cata
                if getattr(r, "nota", None) and is_valid_tasting_note(r.nota.nombre)
            ]
            notas_text = " ".join(valid_notes)
            all_text = strip_accents(
                f"{prod.nombre} {prod.descripcion or ''} {prod.proceso or ''} "
                f"{prod.pais_origen or ''} {prod.variedad or ''} {prod.tueste or ''} {notas_text}"
            )

            # 2. Evaluación Perfil de Sabor (hasta +38 pts por coincidencias múltiples)
            if norm_sabor:
                matched_keywords: List[str] = []
                for category_key, keywords in FLAVOR_KEYWORDS.items():
                    if category_key == norm_sabor or category_key in norm_sabor:
                        matched_keywords = [kw for kw in keywords if kw in all_text]
                        if matched_keywords:
                            break
                if matched_keywords:
                    bonus = min(38, 22 + len(matched_keywords) * 4)
                    score += bonus
                    reasons.append(f"Notas afines ({', '.join(matched_keywords[:2])})")
                else:
                    score -= 12

            # 3. Evaluación Nivel de Acidez (+26 pts)
            if norm_acidez and norm_acidez in ACIDITY_KEYWORDS:
                acid_cfg = ACIDITY_KEYWORDS[norm_acidez]
                pos_hits = [kw for kw in acid_cfg["positive"] if kw in all_text]
                neg_hits = [kw for kw in acid_cfg["negative"] if kw in all_text]
                if pos_hits:
                    score += min(26, 14 + len(pos_hits) * 4)
                    reasons.append(f"Acidez {acidez} ({pos_hits[0]})")
                if neg_hits:
                    score -= min(18, len(neg_hits) * 6)

            # 4. Evaluación Nivel de Tueste (+25 pts)
            if norm_tueste:
                prod_tueste = strip_accents(prod.tueste or "")
                if norm_tueste in prod_tueste or norm_tueste in all_text:
                    score += 25
                    reasons.append(f"Tueste adecuado ({tueste})")

            # 5. Evaluación Método de Preparación (+22 pts)
            if "espresso" in norm_metodo:
                hits = [k for k in ["espresso", "chocolate", "cremoso", "cacao", "caramelo", "nuez", "natural", "medio", "oscuro", "blend"] if k in all_text]
                if hits:
                    score += min(22, 12 + len(hits) * 3)
                    reasons.append("Ideal para extracción espresso")
                elif "filtro" in all_text and "claro" in all_text:
                    score -= 8
            elif any(m in norm_metodo for m in ["filtro", "filtrado", "goteo", "v60", "chemex"]):
                hits = [k for k in ["filtro", "filtrado", "floral", "frutal", "citrico", "jazmin", "lavado", "washed", "claro", "acidez", "geisha", "etiopia", "kenia"] if k in all_text]
                if hits:
                    score += min(22, 12 + len(hits) * 3)
                    reasons.append("Excelente claridad para métodos de filtro")
                elif "oscuro" in all_text or "italian" in all_text:
                    score -= 10
            elif "prensa" in norm_metodo or "french" in norm_metodo:
                hits = [k for k in ["prensa", "cuerpo", "achocolatado", "chocolate", "medio", "nuez", "almendra", "caramelo", "panela", "natural", "brasil"] if k in all_text]
                if hits:
                    score += min(22, 12 + len(hits) * 3)
                    reasons.append("Buen cuerpo para prensa francesa")
            elif "cold" in norm_metodo or "hielo" in norm_metodo:
                hits = [k for k in ["cold brew", "natural", "honey", "miel", "frutal", "berries", "chocolate", "caramelo", "dulce", "naranja", "etiopia", "colombia"] if k in all_text]
                if hits:
                    score += min(22, 12 + len(hits) * 3)
                    reasons.append("Dulzor y frescura ideales para Cold Brew")
            elif "moka" in norm_metodo or "italiana" in norm_metodo:
                hits = [k for k in ["intenso", "chocolate", "cacao", "medio", "oscuro", "cuerpo", "avellana"] if k in all_text]
                if hits:
                    score += min(22, 12 + len(hits) * 3)
                    reasons.append("Intensidad adecuada para cafetera italiana")

            motivo = ". ".join(reasons) if reasons else "Café equilibrado con gran perfil de taza"
            clamped_score = max(10, min(99, score))
            match_ratio = round(clamped_score / 100.0, 2)

            dto = RecommendedProductDTO(
                id=prod.id,
                nombre=prod.nombre,
                tienda=(prod.tienda.nombre or "").replace(")", "").strip(),
                url_detalle=prod.url_detalle,
                imagen=prod.imagen,
                proceso=prod.proceso,
                pais_origen=prod.pais_origen,
                variedad=prod.variedad,
                tueste=prod.tueste,
                precio_clp=cheapest_var.precio_clp,
                precio_por_kilo=float(cheapest_var.precio_por_kilo),
                es_estimado=bool(getattr(cheapest_var, "es_estimado", True)),
                disponible=has_stock,
                puntaje_coincidencia=clamped_score,
                motivo_recomendacion=motivo,
                formato_gramos=cheapest_var.formato_gramos,
                match_score=match_ratio,
                notas_cata=valid_notes[:4],
            )
            tie_hash = ((prod.id * 73) ^ profile_seed) % 97 if profile_seed else -float(cheapest_var.precio_por_kilo)
            sort_key = (
                dto.disponible,
                dto.puntaje_coincidencia,
                tie_hash,
                -dto.precio_por_kilo,
            )
            scored_with_tiebreak.append((sort_key, dto))

        scored_with_tiebreak.sort(key=lambda item: item[0], reverse=True)

        # Diversificar por tienda (máximo 2 cafés de la misma tienda en la primera pasada)
        diversified: List[RecommendedProductDTO] = []
        overflow: List[RecommendedProductDTO] = []
        store_counts: Dict[str, int] = {}

        for _, dto in scored_with_tiebreak:
            cnt = store_counts.get(dto.tienda, 0)
            if cnt < 2:
                diversified.append(dto)
                store_counts[dto.tienda] = cnt + 1
            else:
                overflow.append(dto)
            if len(diversified) >= limit:
                break

        if len(diversified) < limit:
            diversified.extend(overflow[: limit - len(diversified)])

        return diversified[:limit]


