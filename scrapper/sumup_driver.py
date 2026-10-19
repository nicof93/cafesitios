import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from scrapper.base_driver import BaseDriver

logger = logging.getLogger(__name__)


class SumUpDriver(BaseDriver):
    """Driver para tiendas en plataforma SumUp Storefront (ej: Café Cabra)."""

    def __init__(self, nombre: str, url_base: str):
        super().__init__(nombre=nombre, url_base=url_base, plataforma="sumup")

    def _extraer_category_id(self, url: str) -> Optional[str]:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        cat = query.get("category")
        return cat[0] if cat else None

    def parse_json_productos(
        self, data: Any, base_url: str
    ) -> List[Dict[str, Any]]:
        """Extrae productos a partir de payload JSON de SumUp Storefront API."""
        productos: List[Dict[str, Any]] = []
        items = []

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # SumUp puede devolver {"items": [...]} o {"products": [...]} o {"data": [...]}
            items = (
                data.get("items")
                or data.get("products")
                or data.get("data")
                or data.get("results")
                or []
            )

        for item in items:
            if not isinstance(item, dict):
                continue
            nombre = item.get("name") or item.get("title") or ""
            if not nombre:
                continue

            id_externo = str(item.get("id") or item.get("uid") or "")
            slug = item.get("slug") or id_externo
            url_detalle = urljoin(base_url, f"/productos/{slug}" if slug else "")

            # Imagen
            images = item.get("images") or item.get("media") or []
            imagen_url = None
            if isinstance(images, list) and images:
                first_img = images[0]
                if isinstance(first_img, dict):
                    imagen_url = first_img.get("url") or first_img.get("src")
                elif isinstance(first_img, str):
                    imagen_url = first_img
            elif isinstance(item.get("image"), str):
                imagen_url = item.get("image")

            # Precio
            # SumUp a veces expone centavos (minor units) o precio directo
            precio_raw = item.get("price") or item.get("amount") or 0
            if isinstance(precio_raw, dict):
                precio_raw = precio_raw.get("value") or precio_raw.get("amount") or 0
            precio_clp = self.limpiar_precio(precio_raw)

            # Si viene en centavos mayores a 1000000 para café regular
            if precio_clp > 100000 and item.get("currency") in ("CLP", None):
                # Caso extremo de minor units si existiese
                pass

            descripcion = item.get("description") or None
            formato_gramos = self.extraer_gramos(
                f"{nombre} {descripcion or ''}", default=250
            )
            precio_kilo = self.calcular_precio_por_kilo(precio_clp, formato_gramos)

            # Variantes de SumUp
            variants_raw = item.get("variants") or []
            variantes: List[Dict[str, Any]] = []

            if isinstance(variants_raw, list) and variants_raw:
                for v in variants_raw:
                    if not isinstance(v, dict):
                        continue
                    v_name = v.get("name") or v.get("title") or f"{formato_gramos}g"
                    v_price_raw = v.get("price") or precio_clp
                    v_price_clp = self.limpiar_precio(v_price_raw)
                    v_gramos = self.extraer_gramos(v_name, default=formato_gramos)
                    v_id = str(v.get("id") or f"{id_externo}-{v_gramos}")
                    variantes.append({
                        "id_variante_externo": v_id,
                        "opcion": v_name,
                        "formato_gramos": v_gramos,
                        "precio_clp": v_price_clp,
                        "precio_original_clp": v_price_clp,
                        "en_oferta": False,
                        "descuento_porcentaje": 0,
                        "precio_por_kilo": self.calcular_precio_por_kilo(v_price_clp, v_gramos),
                        "disponible": v.get("in_stock", True) if "in_stock" in v else True,
                        "es_estimado": True,
                    })

            if not variantes:
                variantes.append({
                    "id_variante_externo": f"{id_externo}-default",
                    "opcion": f"{formato_gramos}g",
                    "formato_gramos": formato_gramos,
                    "precio_clp": precio_clp,
                    "precio_original_clp": precio_clp,
                    "en_oferta": False,
                    "descuento_porcentaje": 0,
                    "precio_por_kilo": precio_kilo,
                    "disponible": item.get("in_stock", True) if "in_stock" in item else True,
                    "es_estimado": True,
                })

            productos.append({
                "tienda": self.nombre,
                "id_externo": id_externo or url_detalle,
                "nombre": nombre,
                "url_detalle": url_detalle or base_url,
                "imagen": imagen_url,
                "descripcion": descripcion,
                "variantes": variantes,
            })

        return productos

    def parse_html_productos(
        self, html_content: str, url_origen: str
    ) -> List[Dict[str, Any]]:
        """Extrae productos a partir de HTML o script embebido NEXT_DATA de SumUp Storefront."""
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Intentar extraer __NEXT_DATA__ o state JSON si existe en el HTML
        script_next = soup.select_one("script#__NEXT_DATA__")
        if script_next and script_next.string:
            try:
                next_json = json.loads(script_next.string)
                page_props = next_json.get("props", {}).get("pageProps", {})
                products = (
                    page_props.get("products")
                    or page_props.get("items")
                    or page_props.get("catalog", {}).get("products")
                )
                if products:
                    return self.parse_json_productos(products, url_origen)
            except Exception as e:
                logger.debug(f"Error parseando __NEXT_DATA__ en SumUp: {e}")

        # 2. Extracción DOM tradicional y Next.js Storefront
        productos: List[Dict[str, Any]] = []
        contenedores = soup.select(
            "a[data-analytics='product-list-item'], a[data-selector='list-product-view'], a[href*='/product/'], [data-testid*='product'], .product-card, .card, div[class*='ProductCard'], div[class*='list-product'], article"
        )
        seen_urls = set()

        for c in contenedores:
            if c.name == "a" and c.get("href"):
                link_tag = c
            else:
                link_tag = c.select_one("a[href*='/producto'], a[href*='/product'], a[href]")

            if not link_tag or not link_tag.get("href"):
                continue

            href = link_tag.get("href")
            url_detalle = urljoin(url_origen, href)
            if url_detalle in seen_urls:
                continue
            seen_urls.add(url_detalle)

            # Nombre
            nombre = c.get("data-item-name")
            if not nombre:
                nombre_tag = c.select_one(
                    "[data-selector='os-theme-product-list-name'], [data-testid*='title'], [data-testid*='name'], h2, h3, h4, .title"
                )
                nombre = (
                    nombre_tag.get_text(strip=True)
                    if nombre_tag
                    else link_tag.get_text(strip=True)
                )
            if not nombre:
                continue

            # Imagen
            img_tag = c.select_one("img[src], img[data-src]")
            imagen_url = None
            if img_tag:
                raw_src = img_tag.get("src") or img_tag.get("data-src")
                if raw_src and not raw_src.startswith("data:"):
                    imagen_url = urljoin(url_origen, raw_src)

            # Precio
            price_tag = c.select_one(
                "[data-selector*='price'], .list-product-discount, [data-testid*='price'], .price, span[class*='Price']"
            )
            precio_texto = price_tag.get_text(strip=True) if price_tag else ""
            if not precio_texto:
                m_precio = re.search(r'\$\s*([\d\.\,]+)', c.get_text())
                if m_precio:
                    precio_texto = m_precio.group(0)

            precio_clp = self.limpiar_precio(precio_texto)

            formato_gramos = self.extraer_gramos(nombre, default=250)
            precio_kilo = self.calcular_precio_por_kilo(precio_clp, formato_gramos)

            disponible = True
            sold_out_tag = c.select_one(".product-sold-out-label, .sold-out, [data-selector*='sold-out']")
            if sold_out_tag or "agotado" in c.get_text(strip=True).lower():
                disponible = False

            id_externo = c.get("data-item-id") or url_detalle.split("/")[-1].split("?")[0]

            productos.append({
                "tienda": self.nombre,
                "id_externo": id_externo,
                "nombre": nombre,
                "url_detalle": url_detalle,
                "imagen": imagen_url,
                "descripcion": None,
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

    def consumir_productos(self) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/html, */*",
        }

        # Intentar llamada directa a la URL provista
        try:
            response = requests.get(self.url_base, headers=headers, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()
                if "application/json" in content_type:
                    return self.parse_json_productos(response.json(), self.url_base)
                return self.parse_html_productos(response.text, self.url_base)
        except Exception as e:
            logger.warning(f"[{self.nombre}] Error al consumir tienda SumUp ({self.url_base}): {e}")

        return []

