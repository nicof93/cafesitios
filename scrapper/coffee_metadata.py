import re
import unicodedata
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple


EXTRACTOR_VERSION = 'rules-v1'
EXTRACTED_FIELDS = (
    'notas_cata', 'proceso', 'finca', 'variedad', 'elevacion', 'cosecha',
    'fermentacion_tipo', 'fermentacion_horas',
)

_FIELD_LABELS = {
    'notas_cata': (
        'notas de cata', 'notas cata', 'perfil de taza', 'perfil en taza',
        'tasting notes', 'flavor notes', 'flavour notes', 'cup profile', 'notas',
    ),
    'proceso': ('proceso', 'process', 'processing method', 'beneficio'),
    'finca': ('finca', 'farm', 'fazenda', 'estate'),
    'variedad': ('variedad', 'varietal', 'variety', 'cultivar'),
    'elevacion': ('elevacion', 'elevación', 'elevation', 'altitud', 'altitude', 'altura'),
    'cosecha': ('cosecha', 'harvest', 'crop year', 'year'),
    'fermentacion': (
        'tiempo de fermentacion', 'tiempo de fermentación', 'horas de fermentacion',
        'horas de fermentación', 'fermentacion', 'fermentación', 'fermentation time', 'fermentation',
    ),
}

_NOTE_ALIASES = {
    'frutos rojos': 'frutos rojos',
    'red berries': 'frutos rojos',
    'berries': 'frutos rojos',
    'cacao': 'cacao',
    'cocoa': 'cacao',
    'chocolate': 'chocolate',
    'chocolate amargo': 'chocolate amargo',
    'arandano': 'arandano',
    'blueberry': 'arandano',
    'blueberries': 'arandano',
    'frambuesa': 'frambuesa',
    'raspberry': 'frambuesa',
    'mora': 'mora',
    'blackberry': 'mora',
    'naranja': 'naranja',
    'orange': 'naranja',
    'citricos': 'citricos',
    'citrus': 'citricos',
    'limon': 'limon',
    'lemon': 'limon',
    'miel': 'miel',
    'honey': 'miel',
    'panela': 'panela',
    'brown sugar': 'panela',
    'caramelo': 'caramelo',
    'caramel': 'caramelo',
    'almendra': 'almendra',
    'almond': 'almendra',
    'vainilla': 'vainilla',
    'vanilla': 'vainilla',
    'floral': 'floral',
    'jazmin': 'jazmin',
    'jasmine': 'jazmin',
}

_PROCESS_ALIASES = {
    'lavado': 'lavado',
    'washed': 'lavado',
    'wash': 'lavado',
    'natural': 'natural',
    'honey': 'honey',
    'miel': 'honey',
    'anaerobic': 'anaeróbica',
    'anaerobico': 'anaeróbica',
    'anaerobica': 'anaeróbica',
}

_BLOCK_TAGS = {
    'address', 'article', 'blockquote', 'br', 'div', 'footer', 'h1', 'h2',
    'h3', 'h4', 'h5', 'h6', 'header', 'li', 'ol', 'p', 'section', 'tr', 'ul',
}
_SKIP_TAGS = {'script', 'style', 'svg'}


class _DescriptionTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.skip_depth:
            if tag in _SKIP_TAGS:
                self.skip_depth += 1
            return
        if tag in _SKIP_TAGS:
            self.skip_depth = 1
        elif tag in _BLOCK_TAGS:
            self.parts.append('\n')
        elif tag in {'td', 'th'}:
            self.parts.append(' | ')
        elif tag in {'strong', 'b'}:
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if self.skip_depth:
            if tag in _SKIP_TAGS:
                self.skip_depth -= 1
            return
        if tag in _BLOCK_TAGS:
            self.parts.append('\n')
        elif tag in {'td', 'th'}:
            self.parts.append(' | ')
        elif tag in {'strong', 'b'}:
            self.parts.append(' ')

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)


def _description_lines(description: Optional[str]) -> List[str]:
    parser = _DescriptionTextParser()
    parser.feed(description or '')
    parser.close()
    text = ''.join(parser.parts).replace('\xa0', ' ')
    return [re.sub(r'\s+', ' ', line).strip(' |\t') for line in text.splitlines() if line.strip(' |\t')]


def _label_pattern(labels: Tuple[str, ...]) -> re.Pattern:
    labels_pattern = '|'.join(re.escape(label) for label in sorted(labels, key=len, reverse=True))
    return re.compile(
        rf'^\s*(?:\|\s*)?(?P<label>{labels_pattern})'
        rf'(?:(?:\s*[:：]\s*|\s*\|\s*|\s*[–—-]\s*)(?P<value>.*)|\s+(?P<plain>\S.*))?\s*(?:\|\s*)?$',
        re.IGNORECASE,
    )


_ALL_LABELS = tuple(label for aliases in _FIELD_LABELS.values() for label in aliases)
_ALL_LABEL_PATTERN = _label_pattern(_ALL_LABELS)


def _find_labeled_value(
    lines: List[str], labels: Tuple[str, ...]
) -> Tuple[Optional[str], Optional[str], bool]:
    pattern = _label_pattern(labels)
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if not match:
            continue
        inline_value = match.group('value') or match.group('plain') or ''
        value = inline_value.strip(' |\t')
        if value:
            return value, line, True
        for next_line in lines[index + 1:]:
            candidate = next_line.strip(' |\t')
            if (
                not candidate
                or re.fullmatch(r'[_=~*•·.\-–—\s]+', candidate)
                or _ALL_LABEL_PATTERN.match(candidate)
            ):
                continue
            return candidate, next_line, True
        return None, line, True
    return None, None, False


def _fold(value: str) -> str:
    return ''.join(
        character for character in unicodedata.normalize('NFKD', value.lower())
        if not unicodedata.combining(character)
    )


def _note_identity(raw_note: str) -> Tuple[str, str]:
    cleaned = re.sub(r'\s+', ' ', raw_note).strip(' .:;–—-')
    folded = _fold(cleaned)
    canonical = _NOTE_ALIASES.get(folded, folded)
    key = re.sub(r'[^a-z0-9]+', '-', canonical).strip('-')
    display_name = canonical
    return key, display_name


def _extract_notes(value: str, source: str) -> List[Dict[str, Any]]:
    candidates = re.split(r'\s*(?:[,;|/•]|\s+(?:y|and|& )\s+)\s*', value, flags=re.IGNORECASE)
    notes = []
    seen = set()
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        key, display_name = _note_identity(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        notes.append({
            'nombre': display_name,
            'clave_normalizada': key,
            'texto_origen': source,
            'confianza': 0.9,
            'version_extractor': EXTRACTOR_VERSION,
        })
    return notes


def _parse_elevation(value: str) -> List[int]:
    numbers = re.findall(r'\d[\d.,]*', value)
    elevations = []
    for number in numbers:
        normalized = number
        if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+', number):
            normalized = re.sub(r'[.,]', '', number)
        elif normalized.count(',') == 1 and len(normalized.rsplit(',', 1)[1]) == 3:
            normalized = normalized.replace(',', '')
        elif normalized.count('.') == 1 and len(normalized.rsplit('.', 1)[1]) == 3:
            normalized = normalized.replace('.', '')
        try:
            elevation = int(float(normalized.replace(',', '.')))
        except ValueError:
            continue
        if 0 < elevation < 10000:
            elevations.append(elevation)
    return elevations


def _clean_characteristic(value: str) -> str:
    return re.sub(r'\s+', ' ', value.strip(' |\t:;,.–—-')).strip()


def _source(value: Any, text: Optional[str], confidence: float = 0.95) -> Optional[Dict[str, Any]]:
    if value is None or not text:
        return None
    return {'texto': text.strip(), 'confianza': confidence, 'version': EXTRACTOR_VERSION}


def extract_coffee_characteristics(description: Optional[str]) -> Dict[str, Any]:
    lines = _description_lines(description)
    result: Dict[str, Any] = {
        'proceso': None,
        'finca': None,
        'variedad': None,
        'elevacion_min_msnm': None,
        'elevacion_max_msnm': None,
        'cosecha': None,
        'fermentacion_tipo': None,
        'fermentacion_horas': None,
        'fuentes': {},
        'notas_cata': [],
        'notas_cata_mencionadas': False,
        'version': EXTRACTOR_VERSION,
    }

    value, source, found = _find_labeled_value(lines, _FIELD_LABELS['notas_cata'])
    result['notas_cata_mencionadas'] = found
    if value and source:
        result['notas_cata'] = _extract_notes(value, source)

    for field in ('proceso', 'finca', 'variedad', 'cosecha'):
        value, source, _ = _find_labeled_value(lines, _FIELD_LABELS[field])
        if not value:
            continue
        cleaned = _clean_characteristic(value)
        if field == 'proceso':
            result[field] = _PROCESS_ALIASES.get(_fold(cleaned), cleaned.lower())
        else:
            result[field] = cleaned
        result['fuentes'][field] = _source(result[field], source)

    value, source, _ = _find_labeled_value(lines, _FIELD_LABELS['elevacion'])
    if value:
        elevations = _parse_elevation(value)
        if elevations:
            result['elevacion_min_msnm'] = min(elevations)
            result['elevacion_max_msnm'] = max(elevations)
            result['fuentes']['elevacion_min_msnm'] = _source(result['elevacion_min_msnm'], source)
            result['fuentes']['elevacion_max_msnm'] = _source(result['elevacion_max_msnm'], source)

    value, source, _ = _find_labeled_value(lines, _FIELD_LABELS['fermentacion'])
    if value:
        hours_match = re.search(r'\b(\d+(?:[.,]\d+)?)\s*(?:horas?|hrs?\.?|h)\b', value, re.IGNORECASE)
        if hours_match:
            result['fermentacion_horas'] = float(hours_match.group(1).replace(',', '.'))
            result['fuentes']['fermentacion_horas'] = _source(result['fermentacion_horas'], source)
        fermentation_type = re.sub(
            r'\b\d+(?:[.,]\d+)?\s*(?:horas?|hrs?\.?|h)\b', '', value, flags=re.IGNORECASE
        )
        fermentation_type = _clean_characteristic(fermentation_type)
        fermentation_type = re.sub(r'^(?:por|durante|for|of)\s+', '', fermentation_type, flags=re.IGNORECASE)
        fermentation_type = fermentation_type.strip(' ,;:-')
        if fermentation_type:
            result['fermentacion_tipo'] = _PROCESS_ALIASES.get(
                _fold(fermentation_type), fermentation_type.lower()
            )
            result['fuentes']['fermentacion_tipo'] = _source(result['fermentacion_tipo'], source)

    return result


def summarize_extraction_coverage(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    if not total:
        return {'total': 0, 'con_datos': 0, 'porcentaje_con_datos': 0.0, 'campos': {}}

    def has_value(result: Dict[str, Any], field: str) -> bool:
        if field == 'notas_cata':
            return bool(result.get('notas_cata'))
        if field == 'elevacion':
            return result.get('elevacion_min_msnm') is not None
        return result.get(field) is not None

    field_counts = {
        field: sum(has_value(result, field) for result in results)
        for field in EXTRACTED_FIELDS
    }
    with_data = sum(any(has_value(result, field) for field in EXTRACTED_FIELDS) for result in results)
    return {
        'total': total,
        'con_datos': with_data,
        'porcentaje_con_datos': round(with_data * 100 / total, 1),
        'campos': {
            field: {
                'detectados': count,
                'porcentaje': round(count * 100 / total, 1),
            }
            for field, count in field_counts.items()
        },
    }