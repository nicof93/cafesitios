import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scrapper.odoo_driver import OdooDriver


class TestOdooDriver(unittest.TestCase):
    def setUp(self):
        self.driver = OdooDriver(
            nombre="Colibrí Coffee Roasters",
            url_base="https://www.colibricoffee.cl/shop/category/cafe-9"
        )
        self.sample_html = """
        <table id="products_grid">
            <tr>
                <td class="oe_product" data-oe-id="501">
                    <div class="oe_product_image">
                        <a href="/shop/colombia-supremo-501">
                            <img src="/web/image/product.template/501/image_1024" class="o_wsale_product_images" itemprop="image" />
                        </a>
                    </div>
                    <div class="oe_product_cart">
                        <h6 class="o_wsale_products_item_title">
                            <a href="/shop/colombia-supremo-501" itemprop="name">Café Colombia Supremo 250g</a>
                        </h6>
                        <div class="oe_subdescription">Notas de caramelo y cítricos</div>
                        <div class="product_price">
                            <span class="oe_price">
                                <span class="oe_currency_value">10.990</span>
                            </span>
                        </div>
                    </div>
                </td>
                <td class="oe_product" data-oe-id="502">
                    <div class="oe_product_image">
                        <a href="/shop/brasil-cerrado-502">
                            <img src="/web/image/product.template/502/image_1024" />
                        </a>
                    </div>
                    <div class="oe_product_cart">
                        <h6 class="o_wsale_products_item_title">
                            <a href="/shop/brasil-cerrado-502" itemprop="name">Brasil Cerrado 1kg</a>
                        </h6>
                        <div class="product_price">
                            <span class="oe_currency_value">29.900</span>
                        </div>
                        <span class="oe_out_of_stock">Agotado</span>
                    </div>
                </td>
            </tr>
        </table>
        """

    def test_parse_html_productos(self):
        productos = self.driver.parse_html_productos(self.sample_html, "https://www.colibricoffee.cl/shop/category/cafe-9")
        self.assertEqual(len(productos), 2)

        p1 = productos[0]
        self.assertEqual(p1['nombre'], "Café Colombia Supremo 250g")
        self.assertEqual(p1['id_externo'], "501")
        self.assertEqual(p1['url_detalle'], "https://www.colibricoffee.cl/shop/colombia-supremo-501")
        self.assertEqual(p1['imagen'], "https://www.colibricoffee.cl/web/image/product.template/501/image_1024")
        v1 = p1['variantes'][0]
        self.assertEqual(v1['precio_clp'], 10990)
        self.assertEqual(v1['formato_gramos'], 250)
        self.assertEqual(v1['precio_por_kilo'], 43960.0)
        self.assertTrue(v1['disponible'])

        p2 = productos[1]
        self.assertEqual(p2['id_externo'], "502")
        v2 = p2['variantes'][0]
        self.assertEqual(v2['precio_clp'], 29900)
        self.assertEqual(v2['formato_gramos'], 1000)
        self.assertEqual(v2['precio_por_kilo'], 29900.0)
        self.assertFalse(v2['disponible'])

    def test_pagination_url(self):
        url_p1 = self.driver._construir_url_pagina("https://colibri.cl/shop/category/cafe-9", 1)
        self.assertEqual(url_p1, "https://colibri.cl/shop/category/cafe-9")

        url_p2 = self.driver._construir_url_pagina("https://colibri.cl/shop/category/cafe-9", 2)
        self.assertEqual(url_p2, "https://colibri.cl/shop/category/cafe-9/page/2")


if __name__ == '__main__':
    unittest.main()

