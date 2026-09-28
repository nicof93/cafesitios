import re
import logging
import requests
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def extraer_gramos(texto: Optional[str], default: int = 250) -> int:
    """Extrae el formato en gramos a partir de un texto (ej. '250g', '250-gr', '1-kilo', '1kg')."""
    if not texto:
        return default
    match = re.search(r'(\d+(?:\.\d+)?)\s*[-_]?\s*(g|gr|grs|gramos|k|kg|kgs|kilo|kilos)\b', str(texto), re.IGNORECASE)
    if match:
        valor = float(match.group(1))
        unidad = match.group(2).lower()
        return int(valor * 1000) if unidad in ['k', 'kg', 'kgs', 'kilo', 'kilos'] else int(valor)
    return default

def calcular_precio_por_kilo(precio_clp: int, formato_gramos: int) -> float:
    """Calcula el precio proporcional por kilogramo."""
    if formato_gramos > 0 and precio_clp > 0:
        return round((precio_clp / formato_gramos) * 1000, 2)
    return 0.0

class WooCommerceDriver:
    """Driver para consumir y normalizar productos de tiendas bajo la plataforma WooCommerce."""

    def __init__(self, nombre: str, url_base: str):
        self.nombre = nombre
        self.url_base = url_base

    @staticmethod
    def extraer_gramos(texto: Optional[str], default: int = 250) -> int:
        return extraer_gramos(texto, default=default)

    @staticmethod
    def calcular_precio_por_kilo(precio_clp: int, formato_gramos: int) -> float:
        return calcular_precio_por_kilo(precio_clp, formato_gramos)

    def _obtener_base_site(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _parse_price(self, raw_val: Any, minor_unit: int = 0) -> int:
        if raw_val is None:
            return 0
        try:
            val = float(raw_val)
            if minor_unit > 0:
                val = val / (10 ** minor_unit)
            return int(round(val))
        except (ValueError, TypeError):
            return 0

    def normalizar_producto(self, prod: Dict[str, Any], base_site: str = "") -> Dict[str, Any]:
        """Normaliza un producto crudo proveniente de la WooCommerce Store API."""
        titulo_prod = prod.get('name', '').strip()
        permalink = prod.get('permalink') or f"{base_site}/productos/{prod.get('slug', '')}"

        images = prod.get('images', [])
        imagen_url = None
        if isinstance(images, list) and len(images) > 0:
            imagen_url = images[0].get('src') if isinstance(images[0], dict) else None

        descripcion = prod.get('description') or prod.get('short_description') or ''

        # Mapeo de términos de atributos para resolver slugs: (nombre_attr, slug) -> nombre_legible
        terms_map = {}
        for attr in prod.get('attributes', []):
            attr_name = attr.get('name')
            for term in attr.get('terms', []):
                terms_map[(attr_name, term.get('slug'))] = term.get('name')

        prices = prod.get('prices', {})
        minor_unit = prices.get('currency_minor_unit', 0)
        prod_price = self._parse_price(prices.get('price'), minor_unit)
        prod_regular = self._parse_price(prices.get('regular_price'), minor_unit) or prod_price
        price_range = prices.get('price_range')

        range_min = self._parse_price(price_range.get('min_amount'), minor_unit) if price_range else prod_price
        range_max = self._parse_price(price_range.get('max_amount'), minor_unit) if price_range else prod_price

        raw_variations = prod.get('variations', [])
        variantes_normalizadas = []

        prod_in_stock = prod.get('is_in_stock', True)
        prod_purchasable = prod.get('is_purchasable', True)
        prod_disponible = prod_in_stock and prod_purchasable

        if raw_variations:
            var_info = []
            distinct_gramos = set()
            for var in raw_variations:
                opt_parts = []
                var_gramos = None
                for a in var.get('attributes', []):
                    attr_name = a.get('name')
                    val_slug = a.get('value')
                    if not val_slug:
                        continue
                    legible = terms_map.get((attr_name, val_slug), val_slug)
                    opt_parts.append(legible)
                    g = self.extraer_gramos(legible, default=0) or self.extraer_gramos(val_slug, default=0)
                    if g > 0 and not var_gramos:
                        var_gramos = g

                if not var_gramos:
                    var_gramos = self.extraer_gramos(titulo_prod, default=250)

                distinct_gramos.add(var_gramos)
                titulo_var = " / ".join(opt_parts) if opt_parts else f"Variación {var.get('id')}"
                var_info.append((var, titulo_var, var_gramos))

            min_g = min(distinct_gramos) if distinct_gramos else 250
            max_g = max(distinct_gramos) if distinct_gramos else 250

            for var, titulo_var, var_gramos in var_info:
                # Si la variante incluye precio directo
                if var.get('price') is not None:
                    precio_clp = self._parse_price(var.get('price'), minor_unit)
                elif range_min != range_max and min_g < max_g:
                    if var_gramos == min_g:
                        precio_clp = range_min
                    elif var_gramos == max_g:
                        precio_clp = range_max
                    else:
                        ratio = (var_gramos - min_g) / (max_g - min_g)
                        precio_clp = int(round(range_min + ratio * (range_max - range_min)))
                else:
                    precio_clp = range_min or prod_price

                # Detección de oferta y precio original
                if prod_regular > prod_price and prod_regular > 0:
                    descuento_ratio = (prod_regular - prod_price) / prod_regular
                    precio_orig_clp = int(round(precio_clp / (1.0 - descuento_ratio)))
                else:
                    precio_orig_clp = precio_clp

                en_oferta = precio_orig_clp > precio_clp
                descuento_pct = (
                    round(((precio_orig_clp - precio_clp) / precio_orig_clp) * 100)
                    if en_oferta and precio_orig_clp > 0
                    else 0
                )

                precio_kilo = self.calcular_precio_por_kilo(precio_clp, var_gramos)
                disponible = var.get('is_in_stock', prod_disponible)

                variantes_normalizadas.append({
                    'id_variante_externo': str(var.get('id')),
                    'opcion': titulo_var,
                    'formato_gramos': var_gramos,
                    'precio_clp': precio_clp,
                    'precio_original_clp': precio_orig_clp,
                    'en_oferta': en_oferta,
                    'descuento_porcentaje': descuento_pct,
                    'precio_por_kilo': precio_kilo,
                    'disponible': disponible
                })
        else:
            # Producto simple o sin variaciones activas
            gramos = self.extraer_gramos(titulo_prod, default=250)
            precio_clp = prod_price
            precio_orig_clp = prod_regular
            en_oferta = precio_orig_clp > precio_clp
            descuento_pct = (
                round(((precio_orig_clp - precio_clp) / precio_orig_clp) * 100)
                if en_oferta and precio_orig_clp > 0
                else 0
            )
            precio_kilo = self.calcular_precio_por_kilo(precio_clp, gramos)

            variantes_normalizadas.append({
                'id_variante_externo': str(prod.get('id')),
                'opcion': 'Estándar',
                'formato_gramos': gramos,
                'precio_clp': precio_clp,
                'precio_original_clp': precio_orig_clp,
                'en_oferta': en_oferta,
                'descuento_porcentaje': descuento_pct,
                'precio_por_kilo': precio_kilo,
                'disponible': prod_disponible
            })

        return {
            'tienda': self.nombre,
            'nombre': titulo_prod,
            'url_detalle': permalink,
            'imagen': imagen_url,
            'descripcion': descripcion,
            'variantes': variantes_normalizadas
        }

    def consumir_productos(self) -> List[Dict[str, Any]]:
        """Consume el catálogo completo desde los endpoints de la API de WooCommerce Store."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        logging.info(f"Escaneando tienda WooCommerce '{self.nombre}' en {self.url_base}...")

        base_site = self._obtener_base_site(self.url_base)
        urls_a_probar = [self.url_base]

        fallback_store_v1 = f"{base_site}/wp-json/wc/store/v1/products"
        fallback_store = f"{base_site}/wp-json/wc/store/products"

        if fallback_store_v1 not in urls_a_probar:
            urls_a_probar.append(fallback_store_v1)
        if fallback_store not in urls_a_probar:
            urls_a_probar.append(fallback_store)

        productos_raw = []
        url_exitosa = None

        for base_url in urls_a_probar:
            page = 1
            max_pages = 1
            url_funciona = False

            while page <= max_pages:
                try:
                    sep = '&' if '?' in base_url else '?'
                    paginated_url = f"{base_url}{sep}page={page}&per_page=100" if 'per_page=' not in base_url else base_url

                    response = requests.get(paginated_url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 0:
                            productos_raw.extend(data)
                            url_funciona = True
                            url_exitosa = base_url

                            total_pages_header = response.headers.get('X-WP-TotalPages')
                            if total_pages_header and total_pages_header.isdigit():
                                max_pages = int(total_pages_header)
                            elif len(data) == 100:
                                max_pages = page + 1
                            else:
                                break

                            page += 1
                        else:
                            break
                    else:
                        logging.warning(f"[{self.nombre}] Respuesta HTTP {response.status_code} en {paginated_url}.")
                        break
                except Exception as e:
                    logging.warning(f"[{self.nombre}] Error al conectar a {base_url} (página {page}): {e}")
                    break

            if url_funciona:
                break

        if not productos_raw:
            logging.error(f"❌ [{self.nombre}] No se pudo obtener catálogo en ningún endpoint de WooCommerce.")
            return []

        productos_normalizados = [
            self.normalizar_producto(prod, base_site=base_site)
            for prod in productos_raw
        ]

        logging.info(f"✅ [{self.nombre}] {len(productos_normalizados)} productos obtenidos desde {url_exitosa}.")
        return productos_normalizados
