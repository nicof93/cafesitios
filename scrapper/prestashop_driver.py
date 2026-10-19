import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from scrapper.base_driver import BaseDriver

logger = logging.getLogger(__name__)


class PrestaShopDriver(BaseDriver):
    """Driver para tiendas en plataforma PrestaShop (ej: Renacuajo Coffee Roaster)."""

    def __init__(self, nombre: str, url_base: str):
        super().__init__(nombre=nombre, url_base=url_base, plataforma="prestashop")

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
        """Extrae productos a partir de HTML estándar de PrestaShop 1.7 / 8."""
        soup = BeautifulSoup(html_content, "html.parser")
        productos: List[Dict[str, Any]] = []

        contenedores = soup.select(
            "article.product-miniature, .js-product-miniature, .product-container, .ajax_block_product"
        )
        seen_urls = set()

        for c in contenedores:
            # Título y enlace
            link_tag = c.select_one(
                ".product-title a, .product-name a, h2.product-title a, h3.product-title a, h2 a, h3 a, a.product-thumbnail"
            )
            if not link_tag or not link_tag.get("href"):
                continue

            href = link_tag.get("href")
            url_detalle = urljoin(url_origen, href)
            if url_detalle in seen_urls:
                continue
            seen_urls.add(url_detalle)

            # Nombre
            nombre_tag = c.select_one(".product-title a, .product-name a, h2.product-title, h3.product-title")
            nombre = (
                nombre_tag.get_text(strip=True)
                if nombre_tag
                else link_tag.get_text(strip=True)
            )
            if not nombre:
                continue

            # Imagen
            img_tag = c.select_one("img[data-full-size-image-url], img[src]")
            imagen_url = ""
            if img_tag:
                img_src = (
                    img_tag.get("data-full-size-image-url")
                    or img_tag.get("src")
                    or ""
                )
                if img_src:
                    imagen_url = urljoin(url_origen, img_src)

            # Precio actual
            price_tag = c.select_one(
                ".current-price .price, .price, span[itemprop='price'], .product-price"
            )
            precio_texto = price_tag.get_text(strip=True) if price_tag else ""
            precio_clp = self.limpiar_precio(precio_texto)

            # Precio anterior (oferta)
            old_price_tag = c.select_one(".regular-price, .old-price, .has-discount .regular-price")
            precio_orig_clp = (
                self.limpiar_precio(old_price_tag.get_text(strip=True))
                if old_price_tag
                else precio_clp
            )
            en_oferta = precio_orig_clp > precio_clp if precio_orig_clp > 0 else False

            # Descripción corta o atributos
            desc_tag = c.select_one(".product-description-short, .product-description, .product-desc")
            desc_texto = desc_tag.get_text(strip=True) if desc_tag else ""

            # Gramos
            formato_gramos = self.extraer_gramos(f"{nombre} {desc_texto}", default=250)
            precio_kilo = self.calcular_precio_por_kilo(precio_clp, formato_gramos)

            # Disponibilidad
            disponible = True
            flags = c.select(".product-flags li, .product-flag, .product-availability")
            flags_texto = " ".join(f.get_text(strip=True).lower() for f in flags)
            if "agotado" in flags_texto or "out of stock" in flags_texto:
                disponible = False

            # ID externo
            id_externo = None
            if c.get("data-id-product"):
                id_externo = str(c.get("data-id-product"))
            else:
                m_id = re.search(r'/(\d+)-[a-zA-Z0-9_\-]+\.html', url_detalle)
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
                    f"[{self.nombre}] Error obteniendo página {pagina} de PrestaShop ({url_pagina}): {e}"
                )
                break

        if not todos_los_productos:
            # Si no encontró productos en la URL raíz, intentar descubrir categorías en el menú
            try:
                resp = requests.get(self.url_base, headers=headers, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    cat_links = soup.select(
                        "a[href*='granos'], a[href*='cafe'], a[href*='cafes'], a[href*='coffee'], a[href*='origenes'], a[href*='especialidad'], a[href*='catalogo']"
                    )
                    parsed_root = urlparse(self.url_base)
                    for cl in cat_links:
                        href = cl.get("href")
                        if not href:
                            continue
                        cat_url = urljoin(self.url_base, href)
                        parsed_cat = urlparse(cat_url)
                        if parsed_cat.netloc == parsed_root.netloc and parsed_cat.path != parsed_root.path:
                            # Probar esta categoría
                            sub_driver = PrestaShopDriver(nombre=self.nombre, url_base=cat_url)
                            prods = sub_driver.consumir_productos(max_pages=max_pages)
                            if prods:
                                return prods
            except Exception as e:
                logger.debug(f"[{self.nombre}] Error explorando categorías en PrestaShop: {e}")

        return todos_los_productos

