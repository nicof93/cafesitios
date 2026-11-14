import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from scrapper.base_driver import BaseDriver

logger = logging.getLogger(__name__)


class JumpsellerDriver(BaseDriver):
    """Driver para tiendas en plataforma Jumpseller (ej: Tres Cordilleras, Primates)."""

    MAX_PAGES: int = 10

    def __init__(self, nombre: str, url_base: str):
        super().__init__(nombre=nombre, url_base=url_base, plataforma="jumpseller")
        self.visited_urls: set[str] = set()

    def _construir_url_pagina(self, url: str, pagina: int) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query['page'] = [str(pagina)]
        new_query = urlencode(query, doseq=True)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

    def parse_html_productos(
        self, html_content: str, url_origen: str
    ) -> List[Dict[str, Any]]:
        """Extrae los productos a partir de un fragmento o documento HTML de Jumpseller."""
        soup = BeautifulSoup(html_content, "html.parser")
        productos: List[Dict[str, Any]] = []

        # Contenedores comunes en temas de Jumpseller
        contenedores = soup.select(
            ".product-block, .product-item, .product-card, .product, div[itemtype*='Product'], .product-box"
        )
        if not contenedores:
            # Fallback a contenedores genéricos con enlaces a productos
            contenedores = [
                a.parent
                for a in soup.select("a[href*='/producto/'], a[href*='/product/'], a[href*='/cafe/']")
                if a.parent
            ]

        seen_urls = set()

        for c in contenedores:
            # Título y enlace
            link_tag = (
                c.select_one(
                    "a.product-block__name[href], a[class*='name'][href], .product-block-title a[href], .product-item-title a[href], .product-title a[href], a[itemprop='name'][href], h2 a[href], h3 a[href], .name a[href], a.product-link[href]"
                )
                or c.select_one("a[href*='/producto/'], a[href*='/product/'], a[href*='/cafe/']")
                or c.select_one("a[href]")
            )
            if not link_tag or not link_tag.get("href"):
                continue

            href = str(link_tag.get("href") or "").strip()
            # Descartar rutas de idioma /en/, carrito, cuenta o checkout
            if not href or href.startswith("#") or "/en/" in href or "/cart" in href or "/checkout" in href:
                continue

            url_detalle = str(urljoin(url_origen, href))
            if url_detalle in seen_urls:
                continue
            seen_urls.add(url_detalle)

            # Extraer nombre del producto evitando badges de descuento
            nombre_tag = c.select_one(
                "a.product-block__name, [class*='product-block__name'], .product-block-title, .product-item-title, .product-title, [itemprop='name'], h2, h3, .name"
            )
            nombre = ""
            if nombre_tag:
                nombre = str(nombre_tag.get_text(strip=True))
            elif link_tag.get("title"):
                nombre = str(re.sub(r"^Ir a\s+", "", str(link_tag.get("title")).strip(), flags=re.IGNORECASE))
            else:
                clone = BeautifulSoup(str(link_tag), "html.parser")
                for badge in clone.select(".product-block__discount, .discount, .badge, [class*='discount']"):
                    badge.decompose()
                nombre = str(clone.get_text(strip=True))

            # Limpiar posible residuo de porcentaje/descuento que haya quedado al inicio
            nombre = re.sub(r"^-\d+%\s*(?:OFF)?\s*", "", nombre, flags=re.IGNORECASE).strip()

            if not nombre:
                continue

            # Imagen (priorizar URLs reales de CDN sobre placeholders de lazyload)
            img_tag = c.select_one("img[data-src], img[data-original], img[data-lazy-src], img[src]")
            imagen_url = ""
            if img_tag:
                img_src = (
                    img_tag.get("data-src")
                    or img_tag.get("data-original")
                    or img_tag.get("data-lazy-src")
                    or img_tag.get("src")
                    or ""
                )
                img_src = str(img_src)
                if img_src and "placeholder" in img_src.lower():
                    for attr in ["data-src", "data-original", "data-lazy-src"]:
                        val = str(img_tag.get(attr) or "")
                        if val and "placeholder" not in val.lower():
                            img_src = val
                            break
                if img_src and not img_src.startswith("data:"):
                    imagen_url = str(urljoin(url_origen, img_src))

            # Precio
            price_tag = (
                c.select_one(
                    ".product-block-price, .product-price, .price, span[itemprop='price'], .price-standard, .current-price, .money"
                )
                or c.find(string=re.compile(r'\$\s*\d+'))
            )
            precio_texto = str(price_tag.get_text(strip=True)) if hasattr(price_tag, "get_text") else str(price_tag or "")
            precio_clp = int(self.limpiar_precio(precio_texto))

            # Precio original / oferta
            old_price_tag = c.select_one(".product-block-price-old, .old-price, .price-old, .compare-price, del")
            precio_orig_clp = (
                int(self.limpiar_precio(str(old_price_tag.get_text(strip=True))))
                if old_price_tag
                else precio_clp
            )
            en_oferta = precio_orig_clp > precio_clp if precio_orig_clp > 0 else False

            # Formato gramos
            formato_gramos = int(self.extraer_gramos(nombre, default=250))
            precio_kilo = float(self.calcular_precio_por_kilo(precio_clp, formato_gramos))

            # Disponibilidad
            sold_out_tag = c.select_one(".sold-out, .out-of-stock, .badge-sold-out, .product-sold-out")
            disponible = True
            c_text = str(c.get_text(strip=True)).lower()
            if sold_out_tag or "agotado" in c_text:
                disponible = False

            # ID externo
            id_externo = None
            if c.get("data-product-id"):
                id_externo = str(c.get("data-product-id"))
            else:
                m_id = re.search(r'/(\d+)[^/]*$', url_detalle)
                id_externo = str(m_id.group(1)) if m_id else url_detalle

            productos.append({
                "tienda": str(self.nombre),
                "id_externo": str(id_externo),
                "nombre": str(nombre),
                "url_detalle": str(url_detalle),
                "imagen": str(imagen_url) if imagen_url else None,
                "descripcion": None,
                "variantes": [
                    {
                        "id_variante_externo": f"{id_externo}-default",
                        "opcion": f"{formato_gramos}g",
                        "formato_gramos": formato_gramos,
                        "precio_clp": precio_clp,
                        "precio_original_clp": precio_orig_clp if precio_orig_clp > 0 else precio_clp,
                        "en_oferta": en_oferta,
                        "descuento_porcentaje": (
                            round(((precio_orig_clp - precio_clp) / precio_orig_clp) * 100)
                            if en_oferta and precio_orig_clp > 0
                            else 0
                        ),
                        "precio_por_kilo": precio_kilo,
                        "disponible": disponible,
                        "es_estimado": True,
                    }
                ],
            })

        return productos

    def consumir_productos(self, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Consume productos limitándose exclusivamente a la URL de catálogo configurada
        y su paginación directa (?page=2, etc.) sin seguir menús externos ni enlaces cruzados.
        Garantiza tope duro de MAX_PAGES y conjunto visited_urls para evitar bucles.
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        todos_los_productos: List[Dict[str, Any]] = []
        urls_vistas_detalle: set[str] = set()

        limite_paginas = min(max(1, max_pages), self.MAX_PAGES)

        for pagina in range(1, limite_paginas + 1):
            url_pagina = self._construir_url_pagina(self.url_base, pagina)
            if url_pagina in self.visited_urls:
                break
            self.visited_urls.add(url_pagina)

            try:
                response = requests.get(url_pagina, headers=headers, timeout=10)
                if response.status_code != 200:
                    break
                productos_pagina = self.parse_html_productos(response.text, url_pagina)
                if not productos_pagina:
                    break

                nuevos = 0
                for p in productos_pagina:
                    u_det = p.get("url_detalle")
                    if u_det and u_det not in urls_vistas_detalle:
                        urls_vistas_detalle.add(u_det)
                        todos_los_productos.append(p)
                        nuevos += 1

                if nuevos == 0:
                    # Todos los productos ya fueron vistos (redirección a página 1 o fin de catálogo)
                    break
            except Exception as e:
                logger.warning(
                    f"[{self.nombre}] Error obteniendo página {pagina} de Jumpseller ({url_pagina}): {e}"
                )
                break

        return todos_los_productos
