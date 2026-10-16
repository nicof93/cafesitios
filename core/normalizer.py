import re
import unicodedata
from typing import List, Dict, Tuple, Optional, Any

# =====================================================================
# DICCIONARIOS DE NORMALIZACIÓN SEGÚN LA RUEDA DE SABORES DE LA SCA
# 5 Macro-familias solicitadas:
# 1. Floral
# 2. Frutal / Cítrico
# 3. Frutal / Frutos Rojos
# 4. Dulce / Chocolate
# 5. Frutos Secos
# =====================================================================

MACRO_FAMILIAS = [
    "Floral",
    "Frutal / Cítrico",
    "Frutal / Frutos Rojos",
    "Dulce / Chocolate",
    "Frutos Secos",
]

# Mapeo de términos individuales o expresiones (en minúsculas, sin tilde) al descriptor canónico y macro-familia
SCA_DESCRIPTOR_MAP: Dict[str, Tuple[str, str]] = {
    # 1. FLORAL
    "floral": ("Floral", "Floral"),
    "flores": ("Floral", "Floral"),
    "flor blanca": ("Flor blanca", "Floral"),
    "flores blancas": ("Flor blanca", "Floral"),
    "jazmin": ("Jazmín", "Floral"),
    "jasmine": ("Jazmín", "Floral"),
    "azahar": ("Azahar", "Floral"),
    "orange blossom": ("Azahar", "Floral"),
    "flor de naranjo": ("Azahar", "Floral"),
    "rosa": ("Rosa", "Floral"),
    "rose": ("Rosa", "Floral"),
    "lavanda": ("Lavanda", "Floral"),
    "lavender": ("Lavanda", "Floral"),
    "manzanilla": ("Manzanilla", "Floral"),
    "chamomile": ("Manzanilla", "Floral"),
    "hibisco": ("Hibisco", "Floral"),
    "hibiscus": ("Hibisco", "Floral"),
    "jamaica": ("Hibisco", "Floral"),
    "te negro": ("Té negro", "Floral"),
    "black tea": ("Té negro", "Floral"),
    "te verde": ("Té verde", "Floral"),
    "green tea": ("Té verde", "Floral"),
    "magnolia": ("Magnolia", "Floral"),
    "bergamota": ("Bergamota", "Floral"), # Bergamota tiene nota floral/cítrica muy compartida

    # 2. FRUTAL / CÍTRICO
    "citrico": ("Cítrico", "Frutal / Cítrico"),
    "citricos": ("Cítrico", "Frutal / Cítrico"),
    "citrus": ("Cítrico", "Frutal / Cítrico"),
    "acidez citrica": ("Cítrico", "Frutal / Cítrico"),
    "limon": ("Limón", "Frutal / Cítrico"),
    "lemon": ("Limón", "Frutal / Cítrico"),
    "lima": ("Lima", "Frutal / Cítrico"),
    "lime": ("Lima", "Frutal / Cítrico"),
    "naranja": ("Naranja", "Frutal / Cítrico"),
    "orange": ("Naranja", "Frutal / Cítrico"),
    "mandarina": ("Mandarina", "Frutal / Cítrico"),
    "tangerine": ("Mandarina", "Frutal / Cítrico"),
    "mandarin": ("Mandarina", "Frutal / Cítrico"),
    "pomelo": ("Pomelo", "Frutal / Cítrico"),
    "grapefruit": ("Pomelo", "Frutal / Cítrico"),
    "toronja": ("Pomelo", "Frutal / Cítrico"),
    "clementina": ("Clementina", "Frutal / Cítrico"),
    "manzana verde": ("Manzana verde", "Frutal / Cítrico"),
    "green apple": ("Manzana verde", "Frutal / Cítrico"),
    "cidra": ("Cidra", "Frutal / Cítrico"),
    "lemongrass": ("Hierba luisa", "Frutal / Cítrico"),

    # 3. FRUTAL / FRUTOS ROJOS (y frutas afines)
    "frutos rojos": ("Frutos rojos", "Frutal / Frutos Rojos"),
    "red berries": ("Frutos rojos", "Frutal / Frutos Rojos"),
    "berries": ("Frutos rojos", "Frutal / Frutos Rojos"),
    "frutilla": ("Frutilla", "Frutal / Frutos Rojos"),
    "frutillas": ("Frutilla", "Frutal / Frutos Rojos"),
    "fresa": ("Frutilla", "Frutal / Frutos Rojos"),
    "fresas": ("Frutilla", "Frutal / Frutos Rojos"),
    "strawberry": ("Frutilla", "Frutal / Frutos Rojos"),
    "frambuesa": ("Frambuesa", "Frutal / Frutos Rojos"),
    "frambuesas": ("Frambuesa", "Frutal / Frutos Rojos"),
    "raspberry": ("Frambuesa", "Frutal / Frutos Rojos"),
    "arandano": ("Arándano", "Frutal / Frutos Rojos"),
    "arandanos": ("Arándano", "Frutal / Frutos Rojos"),
    "blueberry": ("Arándano", "Frutal / Frutos Rojos"),
    "blueberries": ("Arándano", "Frutal / Frutos Rojos"),
    "cereza": ("Cereza", "Frutal / Frutos Rojos"),
    "cerezas": ("Cereza", "Frutal / Frutos Rojos"),
    "cherry": ("Cereza", "Frutal / Frutos Rojos"),
    "mora": ("Mora", "Frutal / Frutos Rojos"),
    "moras": ("Mora", "Frutal / Frutos Rojos"),
    "blackberry": ("Mora", "Frutal / Frutos Rojos"),
    "grosella": ("Grosella", "Frutal / Frutos Rojos"),
    "red currant": ("Grosella", "Frutal / Frutos Rojos"),
    "ciruela": ("Ciruela", "Frutal / Frutos Rojos"),
    "ciruela roja": ("Ciruela", "Frutal / Frutos Rojos"),
    "plum": ("Ciruela", "Frutal / Frutos Rojos"),
    "granada": ("Granada", "Frutal / Frutos Rojos"),
    "pomegranate": ("Granada", "Frutal / Frutos Rojos"),
    "casis": ("Casis", "Frutal / Frutos Rojos"),
    "cassis": ("Casis", "Frutal / Frutos Rojos"),
    "uva": ("Uva", "Frutal / Frutos Rojos"),
    "grape": ("Uva", "Frutal / Frutos Rojos"),
    "vino tinto": ("Vino", "Frutal / Frutos Rojos"),
    "vinico": ("Vino", "Frutal / Frutos Rojos"),

    # 4. DULCE / CHOCOLATE
    "dulce": ("Dulce", "Dulce / Chocolate"),
    "sweet": ("Dulce", "Dulce / Chocolate"),
    "caramelo": ("Caramelo", "Dulce / Chocolate"),
    "caramel": ("Caramelo", "Dulce / Chocolate"),
    "panela": ("Panela", "Dulce / Chocolate"),
    "chancaca": ("Panela", "Dulce / Chocolate"),
    "brown sugar": ("Azúcar morena", "Dulce / Chocolate"),
    "azucar rubia": ("Azúcar morena", "Dulce / Chocolate"),
    "azucar morena": ("Azúcar morena", "Dulce / Chocolate"),
    "azucar de cana": ("Azúcar morena", "Dulce / Chocolate"),
    "melaza": ("Melaza", "Dulce / Chocolate"),
    "molasses": ("Melaza", "Dulce / Chocolate"),
    "miel": ("Miel", "Dulce / Chocolate"),
    "honey": ("Miel", "Dulce / Chocolate"),
    "vainilla": ("Vainilla", "Dulce / Chocolate"),
    "vanilla": ("Vainilla", "Dulce / Chocolate"),
    "chocolate": ("Chocolate", "Dulce / Chocolate"),
    "chocolate de leche": ("Chocolate con leche", "Dulce / Chocolate"),
    "chocolate con leche": ("Chocolate con leche", "Dulce / Chocolate"),
    "milk chocolate": ("Chocolate con leche", "Dulce / Chocolate"),
    "chocolate negro": ("Chocolate amargo", "Dulce / Chocolate"),
    "chocolate amargo": ("Chocolate amargo", "Dulce / Chocolate"),
    "dark chocolate": ("Chocolate amargo", "Dulce / Chocolate"),
    "cacao": ("Cacao", "Dulce / Chocolate"),
    "cocoa": ("Cacao", "Dulce / Chocolate"),
    "cacao amargo": ("Cacao", "Dulce / Chocolate"),
    "toffee": ("Toffee", "Dulce / Chocolate"),
    "butterscotch": ("Butterscotch", "Dulce / Chocolate"),
    "dulce de leche": ("Dulce de leche", "Dulce / Chocolate"),
    "arequipe": ("Dulce de leche", "Dulce / Chocolate"),
    "manjar": ("Dulce de leche", "Dulce / Chocolate"),
    "maple": ("Sirope de arce", "Dulce / Chocolate"),
    "malvavisco": ("Malvavisco", "Dulce / Chocolate"),
    "praline": ("Praliné", "Dulce / Chocolate"),

    # 5. FRUTOS SECOS
    "frutos secos": ("Frutos secos", "Frutos Secos"),
    "nuts": ("Frutos secos", "Frutos Secos"),
    "almendra": ("Almendra", "Frutos Secos"),
    "almendras": ("Almendra", "Frutos Secos"),
    "almond": ("Almendra", "Frutos Secos"),
    "nuez": ("Nuez", "Frutos Secos"),
    "nueces": ("Nuez", "Frutos Secos"),
    "walnut": ("Nuez", "Frutos Secos"),
    "avellana": ("Avellana", "Frutos Secos"),
    "avellanas": ("Avellana", "Frutos Secos"),
    "hazelnut": ("Avellana", "Frutos Secos"),
    "mani": ("Maní", "Frutos Secos"),
    "peanut": ("Maní", "Frutos Secos"),
    "cacahuate": ("Maní", "Frutos Secos"),
    "castana": ("Castaña", "Frutos Secos"),
    "chestnut": ("Castaña", "Frutos Secos"),
    "pistacho": ("Pistacho", "Frutos Secos"),
    "pistachio": ("Pistacho", "Frutos Secos"),
    "pecana": ("Pecana", "Frutos Secos"),
    "pecan": ("Pecana", "Frutos Secos"),
    "macadamia": ("Nuez de macadamia", "Frutos Secos"),
}


def sanitize_text(text: Optional[str]) -> str:
    """Elimina acentos y normaliza a minúsculas para comparaciones semánticas deterministas."""
    if not text:
        return ""
    text_clean = re.sub(r"\s+", " ", str(text)).strip()
    return "".join(
        c for c in unicodedata.normalize("NFKD", text_clean.lower())
        if not unicodedata.combining(c)
    )


class SCAFlavorWheelNormalizer:
    """Normalizador determinista según la Rueda de Sabores de la SCA (Specialty Coffee Association)."""

    @classmethod
    def normalizar_nota(cls, nota_cruda: str) -> Optional[Tuple[str, str]]:
        """
        Retorna (descriptor_canonico, macro_familia) para una nota cruda.
        Si la nota contiene múltiples sub-descriptores, busca la mejor coincidencia.
        """
        sanitized = sanitize_text(nota_cruda)
        if not sanitized:
            return None

        # 1. Coincidencia directa
        if sanitized in SCA_DESCRIPTOR_MAP:
            return SCA_DESCRIPTOR_MAP[sanitized]

        # 2. Búsqueda de subcadenas ordenadas por longitud (greedy match)
        for key in sorted(SCA_DESCRIPTOR_MAP.keys(), key=len, reverse=True):
            pattern = rf"\b{re.escape(key)}\b"
            if re.search(pattern, sanitized):
                return SCA_DESCRIPTOR_MAP[key]

        return None

    @classmethod
    def clasificar_notas(cls, notas_crudas: List[str]) -> Dict[str, Any]:
        """
        Procesa una lista de notas de cata y retorna:
        - notas_originales: lista limpia de notas crudas
        - notas_normalizadas: lista única de descriptores SCA canónicos
        - macro_familias: lista única de las 5 familias presentes
        """
        notas_orig = []
        notas_norm = []
        familias = set()

        seen_orig = set()
        seen_norm = set()

        for raw in notas_crudas:
            raw_clean = re.sub(r"[.;,]+$", "", raw.strip())
            if not raw_clean or raw_clean.lower() in seen_orig:
                continue
            seen_orig.add(raw_clean.lower())
            notas_orig.append(raw_clean)

            match = cls.normalizar_nota(raw_clean)
            if match:
                canonico, familia = match
                if canonico not in seen_norm:
                    seen_norm.add(canonico)
                    notas_norm.append(canonico)
                familias.add(familia)
            else:
                # Si no está en el mapa estricto, conservar la versión capitalizada limpia
                canonico = raw_clean.capitalize()
                if canonico not in seen_norm:
                    seen_norm.add(canonico)
                    notas_norm.append(canonico)

        return {
            "notas_originales": notas_orig,
            "notas_normalizadas": notas_norm,
            "macro_familias": sorted(list(familias)),
        }


def calcular_precio_kilo(
    precio_clp: int,
    formato_gramos: int,
    unit_price: Optional[float] = None,
) -> Tuple[float, bool]:
    """
    Homologa el precio por kilo según regla de negocio RN-02:
    - Si el e-commerce (Shopify/WooCommerce) expone unit_price oficial > 0:
      se toma directamente y es_estimado = False.
    - Si no, se calcula a partir de los gramos y precio_clp:
      round((precio_clp / formato_gramos) * 1000, 2) y es_estimado = True.
    - Si faltan datos válidos, retorna (0.0, True).
    """
    if unit_price is not None and float(unit_price) > 0:
        return round(float(unit_price), 2), False

    if precio_clp > 0 and formato_gramos > 0:
        precio_calculado = round((float(precio_clp) / float(formato_gramos)) * 1000.0, 2)
        return precio_calculado, True

    return 0.0, True

