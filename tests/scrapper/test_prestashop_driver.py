import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scrapper.prestashop_driver import PrestaShopDriver


class TestPrestaShopDriver(unittest.TestCase):
    def setUp(self):
        self.driver = PrestaShopDriver(
            nombre="Renacuajo Coffee Roaster",
            url_base="https://renacuajocoffeeroaster.cl/7-granos"
        )
        self.sample_html = """
        <div id="products">
            <article class="product-miniature js-product-miniature" data-id-product="42">
                <div class="thumbnail-container">
                    <a href="https://renacuajocoffeeroaster.cl/granos/42-bourbon-rojo.html" class="thumbnail product-thumbnail">
                        <img data-full-size-image-url="https://renacuajocoffeeroaster.cl/img/p/42-large_default.jpg" src="https://renacuajocoffeeroaster.cl/img/p/42-home_default.jpg" alt="Bourbon Rojo" />
                    </a>
                </div>
                <div class="product-description">
                    <h3 class="h3 product-title"><a href="https://renacuajocoffeeroaster.cl/granos/42-bourbon-rojo.html">Bourbon Rojo Anaeróbico 250g</a></h3>
                    <div class="product-price-and-shipping">
                        <span class="price current-price">$11.500 CLP</span>
                        <span class="regular-price">$13.000 CLP</span>
                    </div>
                </div>
            </article>
            <article class="product-miniature js-product-miniature" data-id-product="88">
                <div class="thumbnail-container">
                    <a href="https://renacuajocoffeeroaster.cl/granos/88-geisha-panama.html">
                        <img src="https://renacuajocoffeeroaster.cl/img/p/88-home.jpg" alt="Geisha" />
                    </a>
                </div>
                <div class="product-description">
                    <h3 class="h3 product-title"><a href="https://renacuajocoffeeroaster.cl/granos/88-geisha-panama.html">Geisha Panamá Boquete</a></h3>
                    <div class="product-description-short">Formato disponible en bolsa hermética de 500g</div>
                    <div class="product-price-and-shipping">
                        <span class="price current-price">$22.000</span>
                    </div>
                    <ul class="product-flags">
                        <li class="product-flag out-of-stock">Agotado</li>
                    </ul>
                </div>
            </article>
        </div>
        """

    def test_parse_html_productos(self):
        productos = self.driver.parse_html_productos(self.sample_html, "https://renacuajocoffeeroaster.cl/7-granos")
        self.assertEqual(len(productos), 2)

        p1 = productos[0]
        self.assertEqual(p1['nombre'], "Bourbon Rojo Anaeróbico 250g")
        self.assertEqual(p1['id_externo'], "42")
        self.assertEqual(p1['imagen'], "https://renacuajocoffeeroaster.cl/img/p/42-large_default.jpg")
        v1 = p1['variantes'][0]
        self.assertEqual(v1['precio_clp'], 11500)
        self.assertEqual(v1['precio_original_clp'], 13000)
        self.assertTrue(v1['en_oferta'])
        self.assertEqual(v1['formato_gramos'], 250)
        self.assertEqual(v1['precio_por_kilo'], 46000.0)
        self.assertTrue(v1['disponible'])

        p2 = productos[1]
        self.assertEqual(p2['id_externo'], "88")
        v2 = p2['variantes'][0]
        self.assertEqual(v2['precio_clp'], 22000)
        self.assertEqual(v2['formato_gramos'], 500)
        self.assertEqual(v2['precio_por_kilo'], 44000.0)
        self.assertFalse(v2['disponible'])

    def test_extraer_ofertas_contract(self):
        self.driver.consumir_productos = lambda max_pages=1: self.driver.parse_html_productos(
            self.sample_html, "https://renacuajocoffeeroaster.cl/7-granos"
        )
        ofertas = self.driver.extraer_ofertas()
        self.assertEqual(len(ofertas), 2)
        self.assertEqual(ofertas[0]['plataforma'], "prestashop")
        self.assertEqual(ofertas[0]['precio_actual'], 11500)


if __name__ == '__main__':
    unittest.main()

