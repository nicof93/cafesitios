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
    # Ropa y Merchandising textil
    r'\b(?:polera|poleron|hoodie|t-shirt|shirt|calcetin|calcetines|gorro|jockey|tote\s*bag|bolso|mochila)\b',
    # Vajilla y Accesorios de consumo
    r'\b(?:taza|tazas|tacita|tacitas|mug|mugs|vaso|vasos|termo|tumbler|keepcup)\b',
    # Cajas de regalo, sets de regalo y gift cards
    r'\b(?:caja\s+de\s+regalo|caja\s+regalo|set\s+regalo|box\s+regalo|gift\s*box|gift\s*card|tarjeta\s+de\s+regalo|el\s+regalo\s+perfecto)\b',
    # Suscripciones y membresías periódicas
    r'\b(?:suscripcion|suscripciones|subscripcion|subscription)\b',
    # Molinos y muelas
    r'\b(?:molino|molinillo|grinder|muela|muelas)\b',
    # Máquinas comerciales y cafeteras espresso
    r'\b(?:la\s+marzocco|marzocco|appartamento|mozzafiato|linea\s+classic|linea\s+pb|strada\s+[sx]|kb90|leva\s+[sx]|gs3)\b',
    # Métodos de extracción, cafeteras filtradas y accesorios mecánicos
    r'\b(?:filtro\s+v60|filtros\s+v60|filtro\s+aeropress|filtros\s+aeropress|filtro\s+de\s+papel|filtros\s+de\s+papel|filtros\b|aeropress\s+(?:clear|go|original)|chemex|kettle|tetera\s+cuello|balanza|gramera|bascula|prensa\s+francesa)\b',
    # Prints, ilustraciones y arte
    r'\b(?:print\s+cafe|poster)\b',
    # Talleres, cursos y catas
    r'\b(?:taller\s+de|curso\s+de|workshop|sesion\s+de\s+cata|clase\s+de)\b',
]


# Palabras clave normalizadas para filtrado directo en SQLAlchemy (compatible con SQLite y PostgreSQL)
NON_COFFEE_KEYWORDS_SQL = [
    'polera', 'poleron', 'hoodie', 'calcetin', 'gorro', 'jockey', 'tote', 'bolso', 'mochila',
    'taza', 'tacita', 'mug', 'vaso', 'termo', 'tumbler', 'keepcup',
    'caja regalo', 'caja de regalo', 'set regalo', 'box regalo', 'gift box', 'gift card', 'tarjeta de regalo', 'el regalo perfecto',
    'suscripcion', 'suscripción', 'subscripcion', 'subscription',
    'molino', 'molinillo', 'grinder', 'muela',
    'marzocco', 'appartamento', 'mozzafiato', 'linea classic', 'linea pb', 'strada', 'kb90', 'leva s', 'leva x', 'gs3',
    'filtro', 'aeropress', 'chemex', 'kettle', 'tetera', 'balanza', 'gramera', 'bascula', 'prensa francesa',
    'print cafe', 'print caf', 'poster',
    'taller', 'curso', 'workshop', 'cata en', 'sesion de cata', 'sesión de cata',
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



