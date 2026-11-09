import re
import unicodedata
from typing import Optional


def slugify(text: Optional[str]) -> str:
    """Convierte texto en un slug URL seguro y amigable.
    
    Ejemplos:
        'Café Altura (Santiago)' -> 'cafe-altura-santiago'
        'Singularity Coffee Roasters!' -> 'singularity-coffee-roasters'
    """
    if not text:
        return ""
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '-', text)


def is_valid_slug(slug: Optional[str]) -> bool:
    """Valida que un slug solo contenga letras minúsculas, números y guiones, sin guiones repetidos ni extremos."""
    if not slug:
        return False
    return bool(re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug))
