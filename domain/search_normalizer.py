"""Módulo de normalización de sinónimos y variaciones ortográficas del café (RN-01).

Soporta equivalencias bidireccionales canónicas:
- geisha <-> gesha
- borbón <-> bourbon (y borbon)
- anaeróbico <-> anaerobio (y variantes con/sin tilde)
- lavado <-> washed
"""

import re
import unicodedata
from typing import List, Set

SYNONYM_CLUSTERS = [
    {"geisha", "gesha"},
    {"borbon", "borbón", "bourbon"},
    {"anaerobico", "anaeróbico", "anaerobio", "anaeróbio"},
    {"lavado", "washed"},
]


def strip_accents(text: str) -> str:
    """Elimina tildes y diacríticos preservando caracteres base en minúsculas."""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFD', text)
    stripped = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return stripped.lower()


def get_synonym_group(term: str) -> Set[str]:
    """Obtiene el conjunto de sinónimos si el término pertenece a un grupo conocido."""
    cleaned = term.strip().lower()
    cleaned_stripped = strip_accents(cleaned)
    for cluster in SYNONYM_CLUSTERS:
        cluster_stripped = {strip_accents(item) for item in cluster}
        if cleaned in cluster or cleaned_stripped in cluster_stripped:
            return set(cluster)
    return {cleaned}


def expand_search_terms(search_query: str) -> List[str]:
    """Expande una consulta de búsqueda incluyendo variaciones sinónimas.

    Ejemplo: 'geisha' -> ['geisha', 'gesha']
             'bourbon lote 3' -> ['bourbon lote 3', 'borbón lote 3', 'borbon lote 3']
    """
    if not search_query or not search_query.strip():
        return []

    tokens = search_query.strip().split()
    # Genera combinaciones reemplazando tokens que tengan sinónimos
    token_variations = [list(get_synonym_group(t)) for t in tokens]

    results: List[str] = []
    
    def backtrack(idx: int, current: List[str]):
        if idx == len(token_variations):
            results.append(" ".join(current))
            return
        for var in token_variations[idx]:
            backtrack(idx + 1, current + [var])

    backtrack(0, [])
    # Garantizar que el término original quede primero y sin duplicados
    original = search_query.strip()
    ordered_unique: List[str] = [original]
    for r in results:
        if r not in ordered_unique:
            ordered_unique.append(r)
    return ordered_unique


# Patrones semánticos para clasificar productos ajenos al café en grano/molido
NON_COFFEE_PATTERNS = [
    # Ropa, Merchandising textil y Souvenirs (poleras, imanes, relojes, pines, llaveros, stickers)
    r'\b(?:polera|poleras|poleron|polerones|hoodie|t-shirt|shirt|camiseta|camisa|chaqueta|delantal|pechera|apron|calcetin|calcetines|gorro|gorros|jockey|cap|beanie|tote\s*bag|tote|bolso|bolsos|mochila|mochilas|iman|imanes|magnet|reloj|relojes|clock|watch|pin|pines|llavero|llaveros|sticker|stickers|calcomania|parche|merch)\b',
    # Vajilla y Accesorios de consumo
    r'\b(?:taza|tazas|tacita|tacitas|mug|mugs|vaso|vasos|copa|copas|termo|termos|botella|tumbler|keepcup|cuchara|cucharas|cucharilla|platillo)\b',
    # Cajas de regalo, sets de regalo y gift cards
    r'\b(?:caja\s+de\s+regalo|caja\s+regalo|set\s+regalo|box\s+regalo|gift\s*box|gift\s*card|tarjeta\s+de\s+regalo|el\s+regalo\s+perfecto|voucher|bono\s+de\s+regalo)\b',
    # Suscripciones y membresías periódicas
    r'\b(?:suscripcion|suscripciones|subscripcion|subscription|membresia)\b',
    # Molinos y muelas
    r'\b(?:molino|molinos|molinillo|molinillos|grinder|muela|muelas|comandante\s+c40|timemore\s+chestnut)\b',
    # Máquinas comerciales y cafeteras espresso
    r'\b(?:la\s+marzocco|marzocco|appartamento|mozzafiato|linea\s+classic|linea\s+pb|strada\s+[sx]|kb90|leva\s+[sx]|gs3|cafetera|cafeteras|mokapot|moka\s+italiana|brita)\b',
    # Métodos de extracción, cafeteras filtradas, barismo y limpieza
    r'\b(?:filtro\s+v60|filtros\s+v60|filtro\s+aeropress|filtros\s+aeropress|filtro\s+de\s+papel|filtros\s+de\s+papel|filtros\b|aeropress\s+(?:clear|go|original)|chemex|kettle|tetera|balanza|gramera|bascula|prensa\s+francesa|dripper|portafiltro|tamper|pitcher|jarra\s+barista|server\s+hario|knock\s*box|puck\s*screen|cafiza|rinza|descalcificador|limpiador)\b',
    # Prints, libros, ilustraciones y arte
    r'\b(?:print\s+cafe|poster|posters|cuadro|lamina|libro|libros|revista|magazine|libreta|cuaderno)\b',
    # Talleres, cursos, catas y otros alimentos/bebidas no-café
    r'\b(?:taller\s+de|taller\b|curso\s+de|curso\b|workshop|sesion\s+de\s+cata|clase\s+de|matcha|chai\s+latte|infusion|chocolate\s+en\s+barra|sirope|syrup|galletas|alfajor)\b',
]


# Palabras clave normalizadas para filtrado directo en SQLAlchemy (compatible con SQLite y PostgreSQL)
NON_COFFEE_KEYWORDS_SQL = [
    'polera', 'poleron', 'polerón', 'hoodie', 't-shirt', 'camiseta', 'delantal', 'pechera', 'apron',
    'calcetin', 'calcetín', 'gorro', 'jockey', 'tote', 'bolso', 'mochila',
    'iman', 'imán', 'imanes', 'magnet', 'reloj', 'relojes', 'llavero', 'sticker',
    'taza', 'tacita', 'mug', 'vaso', 'termo', 'botella', 'tumbler', 'keepcup', 'cuchara',
    'caja regalo', 'caja de regalo', 'set regalo', 'box regalo', 'gift box', 'gift card', 'tarjeta de regalo', 'el regalo perfecto',
    'suscripcion', 'suscripción', 'subscripcion', 'subscription', 'membresia', 'membresía',
    'molino', 'molinillo', 'grinder', 'muela',
    'marzocco', 'appartamento', 'mozzafiato', 'linea classic', 'linea pb', 'strada', 'kb90', 'leva s', 'leva x', 'gs3',
    'cafetera', 'mokapot', 'moka italiana', 'brita',
    'filtro', 'aeropress', 'chemex', 'kettle', 'tetera', 'balanza', 'gramera', 'bascula', 'báscula', 'prensa francesa',
    'dripper', 'portafiltro', 'tamper', 'pitcher', 'jarra', 'knock box', 'puck screen', 'cafiza', 'rinza', 'descalcificador',
    'print cafe', 'print caf', 'poster', 'póster', 'libro', 'revista', 'libreta', 'cuaderno',
    'taller', 'curso', 'workshop', 'cata en', 'sesion de cata', 'sesión de cata',
    'matcha', 'chai', 'sirope', 'syrup', 'galleta', 'alfajor',
]

SUSPICIOUS_PRODUCT_PATTERNS = [
    (r'\b(?:pack|kit|combo|duo|dúo|trio|trío|box|set| degustacion|degustación|muestrario|sampler)\b', "Posible pack, kit o set combinado"),
    (r'\b(?:accesorio|repuesto|soporte|base|bandeja|estuche|funda|limpieza|cepillo|toalla|paño|dosificador)\b', "Posible accesorio o insumo de barismo"),
    (r'\b(?:capsula|cápsula|capsulas|cápsulas|nespresso|drip\s+bag|sachet|instantaneo|instantáneo|soluble)\b', "Formato cápsula, drip bag o soluble"),
    (r'\b(?:te\b|té\b|infusion|infusión|cacao|chocolate|barra|dulce|mermelada|miel)\b', "Posible producto de confitería o infusión"),
]


def classify_product_category(nombre: str) -> str:
    """Clasifica si un producto es café ('cafe') o pertenece a merchandising/accesorios ('no_cafe')."""
    if not nombre:
        return 'cafe'
    nombre_norm = strip_accents(nombre)
    for pattern in NON_COFFEE_PATTERNS:
        if re.search(pattern, nombre_norm):
            return 'no_cafe'
    return 'cafe'


def detect_non_coffee_suspicion(
    nombre: str,
    descripcion: str = "",
    has_coffee_metadata: bool = True,
) -> Optional[str]:
    """Retorna el motivo por el cual un producto parece no ser café de especialidad, o None si no es sospechoso."""
    if not nombre or not str(nombre).strip():
        return "Nombre vacío"
    nombre_norm = strip_accents(str(nombre))
    for pattern in NON_COFFEE_PATTERNS:
        m = re.search(pattern, nombre_norm)
        if m:
            return f"Detectado como no-café / merchandising ('{m.group(0)}')"

    for pattern, reason in SUSPICIOUS_PRODUCT_PATTERNS:
        m = re.search(pattern, nombre_norm)
        if m:
            return f"{reason} ('{m.group(0)}')"

    if not has_coffee_metadata:
        return "Sin atributos botánicos detectados (sin origen, proceso, variedad ni notas)"

    return None




