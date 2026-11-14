import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scrapper.jumpseller_driver import JumpsellerDriver


class TestJumpsellerDriver(unittest.TestCase):
    def setUp(self):
        self.driver = JumpsellerDriver(
            nombre="Tres Cordilleras",
            url_base="https://trescordilleras.cl/cafe"
        )
        self.sample_html = """
        <div class="products-grid">
            <div class="product-block" data-product-id="101">
                <a href="/cafe-colombia-250g" class="product-link">
                    <img src="/img/colombia.jpg" alt="Café Colombia" />
                    <h2 class="product-block-title"><a>Café Colombia Huila 250g</a></h2>
                </a>
                <span class="product-block-price">$ 9.990</span>
                <span class="product-block-price-old">$ 11.990</span>
            </div>
            <div class="product-block" data-product-id="102">
                <a href="/cafe-etiopia-1kg">
                    <img data-src="https://trescordilleras.cl/img/etiopia.jpg" alt="Café Etiopía" />
                    <div class="product-title"><a>Etiopía Yirgacheffe 1kg</a></div>
                </a>
                <span class="product-price">$ 34.000</span>
                <span class="sold-out">Agotado</span>
            </div>
        </div>
        """

    def test_parse_html_productos(self):
        productos = self.driver.parse_html_productos(self.sample_html, "https://trescordilleras.cl/cafe")
        self.assertEqual(len(productos), 2)

        p1 = productos[0]
        self.assertEqual(p1['nombre'], "Café Colombia Huila 250g")
        self.assertEqual(p1['url_detalle'], "https://trescordilleras.cl/cafe-colombia-250g")
        self.assertEqual(p1['id_externo'], "101")
        self.assertEqual(len(p1['variantes']), 1)

        v1 = p1['variantes'][0]
        self.assertEqual(v1['precio_clp'], 9990)
        self.assertEqual(v1['precio_original_clp'], 11990)
        self.assertTrue(v1['en_oferta'])
        self.assertEqual(v1['formato_gramos'], 250)
        self.assertEqual(v1['precio_por_kilo'], 39960.0)
        self.assertTrue(v1['disponible'])

        p2 = productos[1]
        self.assertEqual(p2['nombre'], "Etiopía Yirgacheffe 1kg")
        self.assertEqual(p2['imagen'], "https://trescordilleras.cl/img/etiopia.jpg")
        v2 = p2['variantes'][0]
        self.assertEqual(v2['precio_clp'], 34000)
        self.assertEqual(v2['formato_gramos'], 1000)
        self.assertEqual(v2['precio_por_kilo'], 34000.0)
        self.assertFalse(v2['disponible'])

    def test_extraer_ofertas_contract(self):
        # Mock de consumir_productos usando el parser
        self.driver.consumir_productos = lambda max_pages=1: self.driver.parse_html_productos(
            self.sample_html, "https://trescordilleras.cl/cafe"
        )
        ofertas = self.driver.extraer_ofertas()
        self.assertEqual(len(ofertas), 2)
        o1 = ofertas[0]
        self.assertEqual(o1['nombre_producto'], "Café Colombia Huila 250g")
        self.assertEqual(o1['precio_actual'], 9990)
        self.assertEqual(o1['formato_gramos'], 250)
        self.assertEqual(o1['precio_por_kilo'], 39960.0)
        self.assertEqual(o1['plataforma'], "jumpseller")
        self.assertTrue(o1['disponible'])

    def test_parse_html_peregrino_theme(self):
        peregrino_html = """
        <div class="product-block" data-product-id="999">
            <a class="product-block__anchor" href="/cafe-colombia-jeepao">
                <div class="product-block__discount">-10% OFF</div>
                <img class="lazyload" src="/placeholder.png" data-src="https://cdn.jumpseller.com/peregrino/jeepao.jpg" />
            </a>
            <div class="product-block__info">
                <a class="product-block__name" href="/cafe-colombia-jeepao">Colombia Jeepao 250g</a>
                <span class="product-block-price">$ 10.990</span>
                <span class="product-block-price-old">$ 12.211</span>
            </div>
        </div>
        """
        productos = self.driver.parse_html_productos(peregrino_html, "https://peregrinocoffee.cl")
        self.assertEqual(len(productos), 1)
        p = productos[0]
        self.assertEqual(p['nombre'], "Colombia Jeepao 250g")
        self.assertEqual(p['url_detalle'], "https://peregrinocoffee.cl/cafe-colombia-jeepao")
        self.assertEqual(p['imagen'], "https://cdn.jumpseller.com/peregrino/jeepao.jpg")
        self.assertEqual(p['variantes'][0]['precio_clp'], 10990)
        self.assertEqual(p['variantes'][0]['precio_original_clp'], 12211)
        self.assertTrue(p['variantes'][0]['en_oferta'])

    def test_anti_loop_and_max_pages_limit(self):
        """Verifica que el driver previene bucles infinitos, no sigue rutas cruzadas/idiomas y respeta MAX_PAGES."""
        import time
        from unittest.mock import patch

        driver = JumpsellerDriver(
            nombre="Primates Tostadores",
            url_base="https://www.primatestostadores.cl/cafe"
        )

        # Simular HTML con enlaces circulares en el header/menú y paginación
        mock_html_page = """
        <html>
            <head><title>Primates Tostadores</title></head>
            <body>
                <nav>
                    <a href="/en/cafe">English</a>
                    <a href="/cart">Carrito</a>
                    <a href="/checkout">Pagar</a>
                    <a href="/cafe?page=1">Página 1</a>
                    <a href="/cafe?page=2">Página 2</a>
                    <a href="https://www.primatestostadores.cl/cafe">Inicio Colección</a>
                </nav>
                <div class="products-grid">
                    <div class="product-block" data-product-id="501">
                        <a href="/producto-cafe-501" class="product-link">Café Especial 501 250g</a>
                        <span class="product-block-price">$ 8.990</span>
                    </div>
                </div>
            </body>
        </html>
        """

        call_urls = []

        def mock_get(url, headers=None, timeout=None):
            call_urls.append(url)
            resp = MagicMock()
            resp.status_code = 200
            resp.text = mock_html_page
            return resp

        t0 = time.time()
        with patch("scrapper.jumpseller_driver.requests.get", side_effect=mock_get):
            productos = driver.consumir_productos(max_pages=20)
        duration = time.time() - t0

        self.assertLess(duration, 1.0, "La ejecución debe terminar en menos de 1 segundo")
        self.assertGreater(len(productos), 0)
        # MAX_PAGES es 10, por lo que nunca debe exceder 10 llamadas
        self.assertLessEqual(len(call_urls), 10)
        self.assertLessEqual(len(driver.visited_urls), 10)
        # No debe haber URLs duplicadas visitadas
        self.assertEqual(len(call_urls), len(set(call_urls)))
        # No debe haber visitado /en/, /cart, o /checkout
        for visited in call_urls:
            self.assertNotIn("/en/", visited)
            self.assertNotIn("/cart", visited)
            self.assertNotIn("/checkout", visited)


if __name__ == '__main__':
    unittest.main()

