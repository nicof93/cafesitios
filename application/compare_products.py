"""Caso de Uso: Comparativa Directa Entre Productos (CU-03).

Aplica la regla RN-03 (Deduplicación por Gramaje):
Las variantes de molienda se ignoran y se deduplican por formato_gramos,
seleccionando la opción de menor precio para cada gramaje.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload, selectinload
from db.database import Producto, Tienda, Variante, ProductoNotaCata
from core.normalizer import is_valid_tasting_note


def _compute_organoleptic_intensities(
    notas_cata: List[str],
    proceso: Optional[str],
    tueste: Optional[str],
) -> Dict[str, int]:
    """Calcula la intensidad de atributos organolépticos (escala 1-10) homologada con FlavorWheel."""
    notes_text = " ".join(notas_cata).lower()
    process_text = (proceso or "").lower()
    roast_text = (tueste or "").lower()

    dulzura = 6
    acidez = 6
    frutos_rojos = 5
    floral = 5
    cuerpo = 6
    frutos_secos = 5

    if "lavado" in process_text or "washed" in process_text:
        acidez += 2
        floral += 1
        cuerpo -= 1
    elif "natural" in process_text:
        frutos_rojos += 3
        dulzura += 2
        cuerpo += 1
        acidez -= 1
    elif "honey" in process_text or "miel" in process_text:
        dulzura += 3
        frutos_rojos += 1
        cuerpo += 1
    elif "anaerob" in process_text or "maceracion" in process_text or "ferment" in process_text:
        dulzura += 3
        frutos_rojos += 3
        cuerpo += 2

    if "claro" in roast_text or "light" in roast_text:
        acidez += 2
        floral += 2
        cuerpo -= 1
    elif "oscuro" in roast_text or "dark" in roast_text:
        cuerpo += 3
        frutos_secos += 2
        acidez -= 2

    if re.search(r"(caramel|panela|miel|toffee|vainill|dulce|chancaca|azucar)", notes_text, re.I):
        dulzura += 2
    if re.search(r"(limon|citric|naranja|pomelo|manzana|acidez|lima|bergamota)", notes_text, re.I):
        acidez += 3
    if re.search(r"(frutilla|fresa|frambuesa|mora|arandano|cereza|berry|berries|uva|ciruela|frutos rojos)", notes_text, re.I):
        frutos_rojos += 3
    if re.search(r"(jazmin|floral|flores|azahar|te negro|rosa|lavanda)", notes_text, re.I):
        floral += 3
    if re.search(r"(almendra|nuez|avellana|mani|cacao|chocolate|castana)", notes_text, re.I):
        frutos_secos += 2
        cuerpo += 1

    clamp = lambda v: min(10, max(2, int(v)))
    return {
        "dulzura": clamp(dulzura),
        "acidez": clamp(acidez),
        "frutos_rojos": clamp(frutos_rojos),
        "floral": clamp(floral),
        "cuerpo": clamp(cuerpo),
        "frutos_secos": clamp(frutos_secos),
    }


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
    tueste: Optional[str] = None
    escala_agtron: Optional[int] = None
    elevacion_min_msnm: Optional[int] = None
    elevacion_max_msnm: Optional[int] = None
    altura_msnm: Optional[str] = None
    puntuacion_sca: Optional[float] = None
    atributos_organolepticos: Dict[str, int] = field(default_factory=dict)


class CompareProductsUseCase:
    def __init__(self, session: Session):
        self.session = session

    def execute(self, product_ids: List[int]) -> List[CompareProductItemDTO]:
        if not product_ids:
            return []

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
                Producto.oculto_catalogo.is_(False),
                Tienda.activo.is_(True),
            )
            .all()
        )

        results: List[CompareProductItemDTO] = []
        for prod in products:
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
                if getattr(rel, "nota", None) and is_valid_tasting_note(rel.nota.nombre)
            ]

            texto_completo = f"{prod.nombre} {prod.descripcion or ''}"
            pais_origen = prod.pais_origen
            if not pais_origen:
                for pais, pat in [
                    ("Colombia", r"\bcolombia(?:no)?\b"),
                    ("Etiopía", r"\b(?:etiop[ií]a|ethiopia)\b"),
                    ("Brasil", r"\b(?:brasil|brazil)\b"),
                    ("Guatemala", r"\bguatemala\b"),
                    ("Kenia", r"\b(?:kenia|kenya)\b"),
                    ("Costa Rica", r"\bcosta\s+rica\b"),
                    ("Panamá", r"\b(?:panam[aá]|panama)\b"),
                    ("Perú", r"\b(?:per[uú]|peru)\b"),
                    ("Honduras", r"\bhonduras\b"),
                    ("El Salvador", r"\bel\s+salvador\b"),
                    ("Nicaragua", r"\bnicaragua\b"),
                    ("Ruanda", r"\b(?:ruanda|rwanda)\b"),
                    ("Burundi", r"\bburundi\b"),
                    ("Ecuador", r"\becuador\b"),
                    ("México", r"\b(?:m[eé]xico|mexico)\b"),
                    ("Bolivia", r"\bbolivia\b"),
                    ("Indonesia", r"\bindonesia\b"),
                ]:
                    if re.search(pat, texto_completo, re.I):
                        pais_origen = pais
                        break

            proceso = prod.proceso
            if not proceso:
                for proc, pat in [
                    ("Natural Anaeróbico", r"\b(?:natural\s+anaer[oó]bico|anaer[oó]bico\s+natural)\b"),
                    ("Anaeróbico", r"\banaer[oó]bic[oa]\b"),
                    ("Maceración Carbónica", r"\bmaceraci[oó]n\s+carb[oó]nica\b"),
                    ("Doble Fermentación", r"\bdoble\s+fermentaci[oó]n\b"),
                    ("Honey", r"\b(?:yellow|red|black|white)?\s*honey\b"),
                    ("Lavado", r"\b(?:lavado|washed)\b"),
                    ("Natural", r"\bnatural\b"),
                ]:
                    if re.search(pat, texto_completo, re.I):
                        proceso = proc
                        break

            tueste = prod.tueste
            if not tueste:
                for t_lbl, pat in [
                    ("Claro / Filtro", r"\b(?:tueste\s*claro|light\s*roast|tueste\s*filtro)\b"),
                    ("Medio-Claro", r"\b(?:medio[- ]claro|medium[- ]light)\b"),
                    ("Medio", r"\b(?:tueste\s*medio|medium\s*roast|omni[- ]?roast)\b"),
                    ("Medio-Oscuro", r"\b(?:medio[- ]oscuro|medium[- ]dark)\b"),
                    ("Oscuro / Espresso", r"\b(?:tueste\s*oscuro|dark\s*roast)\b"),
                ]:
                    if re.search(pat, texto_completo, re.I):
                        tueste = t_lbl
                        break

            min_alt = prod.elevacion_min_msnm
            max_alt = prod.elevacion_max_msnm
            if min_alt is None:
                m_alt = re.search(r"\b(1\d{3}|2[0-5]\d{2})\s*(?:[-–a]\s*(1\d{3}|2[0-5]\d{2})\s*)?(?:msnm|m\.s\.n\.m)\b", texto_completo, re.I)
                if m_alt:
                    min_alt = int(m_alt.group(1))
                    max_alt = int(m_alt.group(2)) if m_alt.group(2) else min_alt

            if min_alt:
                altura_msnm = f"{min_alt} - {max_alt} msnm" if (max_alt and max_alt != min_alt) else f"{min_alt} msnm"
            else:
                altura_msnm = None

            caract = prod.caracteristicas_fuente if isinstance(prod.caracteristicas_fuente, dict) else {}
            puntuacion_sca = caract.get("puntuacion_sca")
            escala_agtron = caract.get("escala_agtron")

            organolepticos = _compute_organoleptic_intensities(notas, proceso, tueste)

            results.append(
                CompareProductItemDTO(
                    id=prod.id,
                    nombre=prod.nombre,
                    tienda=(prod.tienda.nombre or "").replace(")", "").strip(),
                    tienda_url=prod.tienda.url_base,
                    url_detalle=prod.url_detalle,
                    imagen=prod.imagen,
                    proceso=proceso,
                    pais_origen=pais_origen,
                    finca=prod.finca,
                    variedad=prod.variedad,
                    notas_cata=notas,
                    variantes_por_gramaje=deduped_variants,
                    tueste=tueste,
                    escala_agtron=escala_agtron,
                    elevacion_min_msnm=min_alt,
                    elevacion_max_msnm=max_alt,
                    altura_msnm=altura_msnm,
                    puntuacion_sca=puntuacion_sca,
                    atributos_organolepticos=organolepticos,
                )
            )

        return results


