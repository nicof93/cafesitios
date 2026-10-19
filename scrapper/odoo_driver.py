import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from scrapper.base_driver import BaseDriver

logger = logging.getLogger(__name__)


class OdooDriver(BaseDriver):
    """Driver para tiendas en plataforma Odoo eCommerce (ej: Colibrí Coffee Roasters)."""

    def __init__(self, nombre: str, url_base: str):
        super().__init__(nombre=nombre, url_base=url_base, plataforma="odoo")

    def _construir_url_pagina(self, url: str, pagina: int) -> str:
        if pagina <= 1:
            return url
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        if '/page/' in path:
            path = re.sub(r'/page/\d+', f'/page/{pagina}', path)
        else:
            path = f"{path}/page/{pagina}"
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

    def parse_html_productos(
        self, html_content: str, url_origen: str
    ) -> List[Dict[str, Any]]:
        """Extrae productos a partir de HTML estándar de Odoo eCommerce (v14/v15/v16/v17)."""
        soup = BeautifulSoup(html_content, "html.parser")
        productos: List[Dict[str, Any]] = []

        contenedores = soup.select(
            ".oe_product, table#products_grid td, .o_wsale_product_grid_wrapper, .oe_product_cart, div.oe_subdescription"
        )
        if not contenedores:
            contenedores = soup.select(".card, div[itemtype*='Product']")

        seen_urls = set()

        for c in contenedores:
            link_tag = (
                c.select_one(
                    "a[itemprop='name'], .o_wsale_products_item_title a, h6 a, h5 a, .oe_product_image_link, a.o_product_link"
                )
                or c.find("a")
            )
            if not link_tag or not link_tag.get("href"):
                continue

            href = link_tag.get("href")
            url_detalle = urljoin(url_origen, href)
            if url_detalle in seen_urls:
                continue
            seen_urls.add(url_detalle)

            # Nombre
            nombre_tag = c.select_one(
                "a[itemprop='name'], .o_wsale_products_item_title a, h6 a, h5 a, [itemprop='name']"
            )
            nombre = (
                nombre_tag.get_text(strip=True)
                if nombre_tag
                else link_tag.get_text(strip=True)
            )
            if not nombre:
                continue

            # Imagen
            img_tag = c.select_one(
                "img[itemprop='image'], img.o_wsale_product_images, .oe_product_image img, img[src]"
            )
            imagen_url = ""
            if img_tag and img_tag.get("src"):
                imagen_url = urljoin(url_origen, img_tag.get("src"))

            # Precio
            price_val_tag = c.select_one(
                "span.oe_currency_value, span[itemprop='price'], .oe_price, .o_wsale_price span"
            )
            precio_texto = (
                price_val_tag.get_text(strip=True)
                if price_val_tag
                else (c.select_one(".oe_price") and c.select_one(".oe_price").get_text(strip=True)) or ""
            )
            precio_clp = self.limpiar_precio(precio_texto)

            # Gramos
            desc_tag = c.select_one(".oe_subdescription, .text-muted, p")
            desc_texto = desc_tag.get_text(strip=True) if desc_tag else ""
            formato_gramos = self.extraer_gramos(f"{nombre} {desc_texto}", default=250)
            precio_kilo = self.calcular_precio_por_kilo(precio_clp, formato_gramos)

            # Disponibilidad
            disponible = True
            if c.select_one(".oe_out_of_stock, .out_of_stock") or "agotado" in c.get_text(strip=True).lower():
                disponible = False

            # ID externo
            id_externo = None
            if c.get("data-oe-id"):
                id_externo = str(c.get("data-oe-id"))
            else:
                m_id = re.search(r'-(\d+)(?:\?.*)?$', url_detalle)
                id_externo = m_id.group(1) if m_id else url_detalle

            productos.append({
                "tienda": self.nombre,
                "id_externo": id_externo,
                "nombre": nombre,
                "url_detalle": url_detalle,
                "imagen": imagen_url or None,
                "descripcion": desc_texto or None,
                "variantes": [
                    {
                        "id_variante_externo": f"{id_externo}-default",
                        "opcion": f"{formato_gramos}g",
                        "formato_gramos": formato_gramos,
                        "precio_clp": precio_clp,
                        "precio_original_clp": precio_clp,
                        "en_oferta": False,
                        "descuento_porcentaje": 0,
                        "precio_por_kilo": precio_kilo,
                        "disponible": disponible,
                        "es_estimado": True,
                    }
                ],
            })

        return productos

    def consumir_productos(self, max_pages: int = 5) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        todos_los_productos: List[Dict[str, Any]] = []
        urls_vistas = set()

        for pagina in range(1, max_pages + 1):
            url_pagina = self._construir_url_pagina(self.url_base, pagina)
            try:
                response = requests.get(url_pagina, headers=headers, timeout=10)
                if response.status_code != 200:
                    break
                productos_pagina = self.parse_html_productos(response.text, url_pagina)
                if not productos_pagina:
                    break

                nuevos = 0
                for p in productos_pagina:
                    if p["url_detalle"] not in urls_vistas:
                        urls_vistas.add(p["url_detalle"])
                        todos_los_productos.append(p)
                        nuevos += 1

                if nuevos == 0:
                    break
            except Exception as e:
                logger.warning(
                    f"[{self.nombre}] Error obteniendo página {pagina} de Odoo ({url_pagina}): {e}"
                )
                break

        return todos_los_productos

