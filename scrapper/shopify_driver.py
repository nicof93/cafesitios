import re
import logging
import requests
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def extraer_gramos(texto: Optional[str], default: Optional[int] = None) -> Optional[int]:
    if not texto:
        return default
    match = re.search(r'(\d+(?:\.\d+)?)\s*[-_]?\s*(g|gr|grs|gramos|k|kg|kgs|kilo|kilos)\b', str(texto), re.IGNORECASE)
    if match:
        valor = float(match.group(1))
        unidad = match.group(2).lower()
        return int(valor * 1000) if unidad in ['k', 'kg', 'kgs', 'kilo', 'kilos'] else int(valor)
    return default

def calcular_precio_por_kilo(precio_clp: int, formato_gramos: int) -> float:
    if formato_gramos and formato_gramos > 0 and precio_clp > 0:
        return round((precio_clp / formato_gramos) * 1000, 2)
    return 0.0

class ShopifyDriver:
    @staticmethod
    def extraer_gramos(texto: Optional[str], default: int = 250) -> int:
        return extraer_gramos(texto, default=default) or default

    @staticmethod
    def calcular_precio_por_kilo(precio_clp: int, formato_gramos: int) -> float:
        return calcular_precio_por_kilo(precio_clp, formato_gramos)

    def __init__(self, nombre: str, url_base: str, shopify_default: bool = True):
        self.nombre = nombre
        self.url_base = url_base
        self.shopify_default = shopify_default

    def _obtener_base_site(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def consumir_productos(self) -> List[Dict[str, Any]]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        logging.info(f"Escaneando tienda '{self.nombre}' en {self.url_base}...")

        base_site = self._obtener_base_site(self.url_base)
        urls_a_probar = [self.url_base]
        fallback_all = f"{base_site}/collections/all/products.json"
        fallback_root = f"{base_site}/products.json"

        if fallback_all not in urls_a_probar:
            urls_a_probar.append(fallback_all)
        if fallback_root not in urls_a_probar:
            urls_a_probar.append(fallback_root)

        data = None
        url_exitosa = None

        for url in urls_a_probar:
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    url_exitosa = url
                    break
                else:
                    logging.warning(f"[{self.nombre}] Respuesta HTTP {response.status_code} en {url}. Probando fallback...")
            except Exception as e:
                logging.warning(f"[{self.nombre}] Error al conectar a {url}: {e}")

        if not data or 'products' not in data:
            raise RuntimeError(f"No se pudo obtener catálogo en ningún endpoint de Shopify para '{self.nombre}'.")

        productos_raw = data.get('products', [])
        productos_normalizados = []

        for prod in productos_raw:
            titulo_prod = prod.get('title', '').strip()
            handle = prod.get('handle', '')
            url_detalle = f"{base_site}/products/{handle}" if handle else base_site

            images = prod.get('images', [])
            imagen_url = None
            if isinstance(images, list) and len(images) > 0:
                imagen_url = images[0].get('src') if isinstance(images[0], dict) else None

            variantes_normalizadas = []
            for var in prod.get('variants', []):
                titulo_var = var.get('title', '')

                try:
                    precio_clp = int(float(var.get('price', 0)))
                except (ValueError, TypeError):
                    precio_clp = 0

                compare_at = var.get('compare_at_price')
                try:
                    precio_orig_clp = int(float(compare_at)) if compare_at else precio_clp
                except (ValueError, TypeError):
                    precio_orig_clp = precio_clp

                en_oferta = precio_orig_clp > precio_clp
                descuento_pct = (
                    round(((precio_orig_clp - precio_clp) / precio_orig_clp) * 100)
                    if en_oferta and precio_orig_clp > 0
                    else 0
                )

                gramos_shopify = var.get('grams')
                gramos = (
                    (int(gramos_shopify) if gramos_shopify and int(gramos_shopify) > 0 else None)
                    or extraer_gramos(titulo_var)
                    or extraer_gramos(titulo_prod)
                    or 250
                )

                precio_por_kilo = round((precio_clp / gramos) * 1000, 2) if gramos > 0 else 0

                variantes_normalizadas.append({
                    'id_variante_externo': str(var.get('id')),
                    'opcion': titulo_var,
                    'formato_gramos': gramos,
                    'precio_clp': precio_clp,
                    'precio_original_clp': precio_orig_clp,
                    'en_oferta': en_oferta,
                    'descuento_porcentaje': descuento_pct,
                    'precio_por_kilo': precio_por_kilo,
                    'disponible': var.get('available', True)
                })

            productos_normalizados.append({
                'tienda': self.nombre,
                'id_externo': str(prod.get('id') or prod.get('sku')) if prod.get('id') or prod.get('sku') else None,
                'nombre': titulo_prod,
                'url_detalle': url_detalle,
                'imagen': imagen_url,
                'descripcion': prod.get('body_html', ''),
                'variantes': variantes_normalizadas
            })

        logging.info(f"✅ [{self.nombre}] {len(productos_normalizados)} productos obtenidos desde {url_exitosa}.")
        return productos_normalizados
