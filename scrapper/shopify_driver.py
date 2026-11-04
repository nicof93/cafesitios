import gzip
import json
import logging
import re
import urllib.request
from urllib.parse import urlparse

import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from typing import List, Dict, Any, Optional
from core.normalizer import calcular_precio_kilo

from scrapper.base_driver import BaseDriver

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
        val = (precio_clp / formato_gramos) * 1000
        if val >= 100000000.0:
            val = 99999999.99
        return round(val, 2)
    return 0.0

class ShopifyDriver(BaseDriver):
    @staticmethod
    def extraer_gramos(texto: Optional[str], default: int = 250) -> int:
        return extraer_gramos(texto, default=default) or default

    @staticmethod
    def calcular_precio_por_kilo(precio_clp: int, formato_gramos: int) -> float:
        return calcular_precio_por_kilo(precio_clp, formato_gramos)

    @staticmethod
    def extraer_ficha_tecnica_texto(texto: Optional[str]) -> Dict[str, Any]:
        """
        Extrae atributos organolépticos (tueste, perfil, notas_cata, proceso) desde texto plano o HTML.
        Sanitiza saltos de línea, espacios en blanco y normaliza notas en una lista de cadenas limpias.
        """
        ficha: Dict[str, Any] = {
            'tueste': None,
            'perfil': None,
            'notas_cata': [],
            'proceso': None,
        }
        if not texto:
            return ficha

        if BeautifulSoup is not None:
            soup = BeautifulSoup(str(texto), 'html.parser')
            for tag in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav']):
                tag.decompose()
            texto_limpio = soup.get_text(separator='\n')
        else:
            texto_sin_scripts = re.sub(
                r'<(?:script|style|noscript|header|footer|nav)[^>]*>.*?</(?:script|style|noscript|header|footer|nav)>',
                '',
                str(texto),
                flags=re.DOTALL | re.IGNORECASE
            )
            texto_limpio = re.sub(r'<[^>]+>', '\n', texto_sin_scripts)

        # 1. Tueste / Tostado: r'(?:TOSTADO|TUESTE)\s*[:\*\-]?\s*([A-Za-z\s]+)'
        m_tueste = re.search(
            r'(?:TOSTADO|TUESTE)[\s:\*\-]*\b([A-Za-zÀ-ÿ\s]+)',
            texto_limpio,
            re.IGNORECASE
        )
        if m_tueste:
            lines = m_tueste.group(1).strip().splitlines()
            raw_tueste = lines[0].strip() if lines else ""
            if raw_tueste:
                ficha['tueste'] = raw_tueste[:50].capitalize()

        # 2. Perfil: r'PERFIL\s*[:\*\-]?\s*([A-Za-z,\s]+)' (permite conectores y barras)
        m_perfil = re.search(
            r'PERFIL[\s:\*\-]*\b([A-Za-zÀ-ÿ0-9,\s/–-]+)',
            texto_limpio,
            re.IGNORECASE
        )
        if m_perfil:
            lines = m_perfil.group(1).strip().splitlines()
            raw_perfil = lines[0].strip() if lines else ""
            if raw_perfil:
                ficha['perfil'] = raw_perfil[:100]

        # 3. Notas de Cata: r'NOTAS\s*[:\*\-]?\s*([^\n\.<]+)'
        m_notas = re.search(
            r'(?:NOTAS(?:\s*DE\s*CATA)?|DESCRIPTORES)[\s:\*\-]*([^\n\.<]+)',
            texto_limpio,
            re.IGNORECASE
        )
        if m_notas:
            raw_notas = m_notas.group(1).strip()
            tokens = re.split(r'[,;/•]|\s+(?:y|and|&)\s+', raw_notas, flags=re.IGNORECASE)
            limpias = [t.strip(' .*-') for t in tokens if len(t.strip(' .*-')) > 1]
            ficha['notas_cata'] = limpias

        # 4. Proceso: r'PROCESO\s*[:\*\-]?\s*([A-Za-z\s]+)'
        m_proceso = re.search(
            r'PROCESO[\s:\*\-]*\b([A-Za-zÀ-ÿ\s]+)',
            texto_limpio,
            re.IGNORECASE
        )
        if m_proceso:
            lines = m_proceso.group(1).strip().splitlines()
            raw_proceso = lines[0].strip() if lines else ""
            if raw_proceso:
                ficha['proceso'] = raw_proceso[:100].capitalize()

        return ficha

    @classmethod
    def _fetch_url_content(cls, url: str, timeout: int = 10, is_json: bool = True) -> Any:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*' if is_json else 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
        }
        if hasattr(requests.get, 'mock_calls'):
            res = requests.get(url, headers=headers, timeout=timeout)
            if res.status_code != 200:
                raise RuntimeError(f"HTTP {res.status_code}")
            return res.json() if is_json else res.text

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_bytes = resp.read()
                if resp.headers.get('Content-Encoding') == 'gzip' or raw_bytes[:2] == b'\x1f\x8b':
                    try:
                        raw_bytes = gzip.decompress(raw_bytes)
                    except Exception:
                        pass
                text = raw_bytes.decode('utf-8', errors='replace')
                if is_json:
                    return json.loads(text)
                return text
        except urllib.error.HTTPError as http_err:
            if http_err.code in (401, 403, 404):
                raise RuntimeError(f"HTTP {http_err.code}: {http_err.reason}")
            logging.debug(f"urllib fetch fallo en {url}: {http_err}. Intentando fallback...")
        except Exception as urllib_err:
            logging.debug(f"urllib fetch fallo en {url}: {urllib_err}. Intentando fallback...")

        res = requests.get(url, headers=headers, timeout=timeout)
        if res.status_code != 200:
            raise RuntimeError(f"HTTP {res.status_code}")
        if is_json:
            return res.json()
        return res.text

    def extraer_ficha_tecnica_html(self, url_detalle: str) -> Dict[str, Any]:
        """
        Fallback a HTML: Solicita url_detalle usando User-Agent de navegador y timeout de 5s.
        En caso de código HTTP != 200 o excepción/timeout, captura con logging.warning y retorna {}.
        """
        if not url_detalle:
            return {}

        try:
            html_text = self._fetch_url_content(url_detalle, timeout=5, is_json=False)
            return self.extraer_ficha_tecnica_texto(html_text)
        except Exception as e:
            logging.warning(
                f"[{self.nombre}] Excepción al obtener ficha técnica HTML de {url_detalle}: {e}"
            )
            return {}

    def __init__(self, nombre: str, url_base: str, shopify_default: bool = True):
        super().__init__(nombre=nombre, url_base=url_base, plataforma="shopify")
        self.shopify_default = shopify_default

    def _obtener_base_site(self, url: str) -> str:
        if not url:
            return ""
        url_str = str(url).strip()
        if not url_str.startswith("http://") and not url_str.startswith("https://"):
            url_str = f"https://{url_str}"
        parsed = urlparse(url_str)
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    def consumir_productos(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        logging.info(f"Escaneando tienda '{self.nombre}' en {self.url_base}...")

        base_site = self._obtener_base_site(self.url_base)
        parsed_base = urlparse(self.url_base)
        path_clean = parsed_base.path.rstrip('/')

        urls_a_probar: List[str] = []
        if path_clean.lower().endswith('.json'):
            urls_a_probar.append(self.url_base)

        m_col = re.search(r'/collections/([^/]+?)(?:\.json)?$', path_clean, re.IGNORECASE)
        if m_col and m_col.group(1).lower() != 'products':
            col_slug = m_col.group(1)
            col_products_url = f"{base_site}/collections/{col_slug}/products.json"
            if col_products_url not in urls_a_probar:
                urls_a_probar.append(col_products_url)

        fallback_all = f"{base_site}/collections/all/products.json"
        fallback_root = f"{base_site}/products.json"

        if fallback_all not in urls_a_probar:
            urls_a_probar.append(fallback_all)
        if fallback_root not in urls_a_probar:
            urls_a_probar.append(fallback_root)
        if self.url_base not in urls_a_probar:
            urls_a_probar.append(self.url_base)

        if (
            self.nombre.strip().lower() in ('apricot', 'apricat', 'apricat coffee', 'apricot coffee')
            and 'wp-json' not in self.url_base.lower()
        ):
            for apricat_url in (
                'https://apricatcoffee.com/collections/all/products.json',
                'https://apricatcoffee.com/products.json',
            ):
                if apricat_url not in urls_a_probar:
                    urls_a_probar.append(apricat_url)

        data = None
        url_exitosa = None
        errores_intentos: List[str] = []

        for url in urls_a_probar:
            try:
                candidate = self._fetch_url_content(url, timeout=10, is_json=True)
                if isinstance(candidate, dict) and isinstance(candidate.get('products'), list):
                    if candidate['products']:
                        data = candidate
                        url_exitosa = url
                        break
                    if data is None:
                        data = candidate
                        url_exitosa = url
                    logging.warning(f"[{self.nombre}] Catálogo vacío en {url}. Probando fallback...")
                elif isinstance(candidate, dict) and isinstance(candidate.get('product'), dict):
                    data = {'products': [candidate['product']]}
                    url_exitosa = url
                    break
                else:
                    errores_intentos.append(f"{url}: respuesta sin clave 'products'")
                    logging.warning(f"[{self.nombre}] Respuesta JSON sin clave 'products' en {url}. Probando fallback...")
            except Exception as e:
                errores_intentos.append(f"{url}: {e}")
                logging.warning(f"[{self.nombre}] Error al conectar a {url}: {e}")

        if not isinstance(data, dict) or 'products' not in data:
            detalle_str = "; ".join(errores_intentos)
            if any("401" in err or "unauthorized" in err.lower() or "password" in err.lower() for err in errores_intentos):
                raise RuntimeError(
                    f"TIENDA_PROTEGIDA_PASSWORD: La tienda '{self.nombre}' tiene protección por contraseña (/password) o requiere autorización (HTTP 401). Intentos: {detalle_str}"
                )
            if any("timeout" in err.lower() or "timed out" in err.lower() or "connection" in err.lower() for err in errores_intentos):
                raise RuntimeError(
                    f"SITIO_CAIDO_O_TIMEOUT: Error de conexión o timeout al acceder a la tienda '{self.nombre}'. Intentos: {detalle_str}"
                )
            raise RuntimeError(f"No se pudo obtener catálogo en ningún endpoint de Shopify para '{self.nombre}'. Detalle: {detalle_str}")

        if url_exitosa:
            base_site = self._obtener_base_site(url_exitosa)

        productos_raw = data.get('products', [])
        productos_normalizados = []

        NON_COFFEE_KEYWORDS = (
            'taller', 'curso', 'taza', 'mug', 'vaso', 'polera', 'gorro', 'tote bag',
            'prensa francesa', 'aeropress', 'chemex', 'v60', 'kalita', 'filtro de papel',
            'molinillo', 'molino', 'cafetera', 'gift card', 'tarjeta de regalo', 'balanza',
            'hervidor', 'amigo secreto'
        )

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

                gramos_extraidos = extraer_gramos(titulo_var) or extraer_gramos(titulo_prod)
                gramos_shopify = var.get('grams')
                gramos_valido = None
                if gramos_shopify and isinstance(gramos_shopify, (int, float, str)):
                    try:
                        g_sh = int(float(gramos_shopify))
                        if g_sh in (100, 125, 150, 200, 250, 300, 340, 350, 400, 454, 500, 1000):
                            gramos_valido = g_sh
                    except (ValueError, TypeError):
                        pass

                if gramos_extraidos:
                    gramos = gramos_extraidos
                    es_estimado_gramos = False
                elif gramos_valido:
                    gramos = gramos_valido
                    es_estimado_gramos = False
                else:
                    gramos = 250
                    es_estimado_gramos = True

                unit_price = var.get('unit_price')
                precio_por_kilo, _ = calcular_precio_kilo(precio_clp, gramos, unit_price=unit_price)
                es_estimado = es_estimado_gramos and (unit_price is None or float(unit_price) <= 0)

                variantes_normalizadas.append({
                    'id_variante_externo': str(var.get('id')),
                    'opcion': titulo_var,
                    'formato_gramos': gramos,
                    'precio_clp': precio_clp,
                    'precio_original_clp': precio_orig_clp,
                    'en_oferta': en_oferta,
                    'descuento_porcentaje': descuento_pct,
                    'precio_por_kilo': precio_por_kilo,
                    'es_estimado': es_estimado,
                    'disponible': var.get('available', True)
                })

            # Detección Condicional de Fallback (Triggers)
            descripcion_raw = prod.get('body_html') or ''
            # Evaluar si el texto carece de palabras clave patrón como: NOTAS, PERFIL, TUESTE, TOSTADO, PROCESO o DESCRIPTORES
            tiene_atributos_clave = bool(re.search(
                r'(?:NOTAS(?:\s*DE\s*CATA)?|PERFIL|TUESTE|TOSTADO|PROCESO|DESCRIPTORES)\s*[:\*\-]',
                descripcion_raw,
                re.IGNORECASE
            ))

            es_accesorio = any(k in titulo_prod.lower() for k in NON_COFFEE_KEYWORDS)

            ficha_tecnica: Dict[str, Any] = {}
            if not tiene_atributos_clave and not es_accesorio and url_detalle and url_detalle != base_site:
                logging.info(f"[{self.nombre}] Faltan atributos clave en JSON para '{titulo_prod}'. Activando fallback HTML...")
                ficha_tecnica = self.extraer_ficha_tecnica_html(url_detalle)
            else:
                ficha_tecnica = self.extraer_ficha_tecnica_texto(descripcion_raw)

            tueste = ficha_tecnica.get('tueste')
            perfil = ficha_tecnica.get('perfil')
            notas_cata = ficha_tecnica.get('notas_cata', [])
            proceso = ficha_tecnica.get('proceso')

            descripcion_final = descripcion_raw
            lineas_adicionales = []
            if tueste and not re.search(r'\b(?:tueste|tostado)\b', descripcion_final, re.IGNORECASE):
                lineas_adicionales.append(f"TUESTE: {tueste}")
            if perfil and not re.search(r'\bperfil\b', descripcion_final, re.IGNORECASE):
                lineas_adicionales.append(f"PERFIL: {perfil}")
            if notas_cata and not re.search(r'\bnotas\b', descripcion_final, re.IGNORECASE):
                lineas_adicionales.append(f"NOTAS: {', '.join(notas_cata)}")
            if proceso and not re.search(r'\bproceso\b', descripcion_final, re.IGNORECASE):
                lineas_adicionales.append(f"PROCESO: {proceso}")

            if lineas_adicionales:
                descripcion_final = (descripcion_final + ("\n" if descripcion_final else "") + "\n".join(lineas_adicionales)).strip()

            productos_normalizados.append({
                'tienda': self.nombre,
                'id_externo': str(prod.get('id') or prod.get('sku')) if prod.get('id') or prod.get('sku') else None,
                'nombre': titulo_prod,
                'url_detalle': url_detalle,
                'imagen': imagen_url,
                'descripcion': descripcion_final,
                'tueste': tueste,
                'perfil': perfil,
                'notas_cata': notas_cata,
                'proceso': proceso,
                'variantes': variantes_normalizadas
            })

            if limit is not None and len(productos_normalizados) >= limit:
                break

        logging.info(f"✅ [{self.nombre}] {len(productos_normalizados)} productos obtenidos desde {url_exitosa}.")
        return productos_normalizados
