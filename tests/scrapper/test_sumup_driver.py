import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scrapper.sumup_driver import SumUpDriver


class TestSumUpDriver(unittest.TestCase):
    def setUp(self):
        self.driver = SumUpDriver(
            nombre="Café Cabra",
            url_base="https://tienda.cafecabra.cl/productos?category=21026d6d-56dc-41a9-ba19-6996da877e9f"
        )
        self.sample_json = {
            "items": [
                {
                    "id": "cabra-blend-casa",
                    "name": "Blend de la Casa 250g",
                    "slug": "blend-casa",
                    "price": 8500,
                    "description": "Notas dulces a chocolate y nuez",
                    "images": [{"url": "https://cdn.sumup.store/img/blend.jpg"}],
                    "in_stock": True,
                    "variants": [
                        {
                            "id": "var-250",
                            "name": "250g",
                            "price": 8500,
                            "in_stock": True,
                        },
                        {
                            "id": "var-1000",
                            "name": "1kg",
                            "price": 26000,
                            "in_stock": True,
                        }
                    ]
                },
                {
                    "id": "cabra-kenya",
                    "name": "Kenia Nyeri 250g",
                    "slug": "kenia-nyeri",
                    "price": 12000,
                    "images": ["https://cdn.sumup.store/img/kenia.jpg"],
                    "in_stock": False,
                }
            ]
        }

    def test_parse_json_productos(self):
        productos = self.driver.parse_json_productos(self.sample_json, "https://tienda.cafecabra.cl")
        self.assertEqual(len(productos), 2)

        p1 = productos[0]
        self.assertEqual(p1['nombre'], "Blend de la Casa 250g")
        self.assertEqual(p1['id_externo'], "cabra-blend-casa")
        self.assertEqual(p1['url_detalle'], "https://tienda.cafecabra.cl/productos/blend-casa")
        self.assertEqual(p1['imagen'], "https://cdn.sumup.store/img/blend.jpg")
        self.assertEqual(len(p1['variantes']), 2)

        v1 = p1['variantes'][0]
        self.assertEqual(v1['formato_gramos'], 250)
        self.assertEqual(v1['precio_clp'], 8500)
        self.assertEqual(v1['precio_por_kilo'], 34000.0)

        v2 = p1['variantes'][1]
        self.assertEqual(v2['formato_gramos'], 1000)
        self.assertEqual(v2['precio_clp'], 26000)
        self.assertEqual(v2['precio_por_kilo'], 26000.0)

        p2 = productos[1]
        self.assertEqual(p2['nombre'], "Kenia Nyeri 250g")
        v_p2 = p2['variantes'][0]
        self.assertFalse(v_p2['disponible'])

    def test_extraer_ofertas_contract(self):
        self.driver.consumir_productos = lambda: self.driver.parse_json_productos(
            self.sample_json, "https://tienda.cafecabra.cl"
        )
        ofertas = self.driver.extraer_ofertas()
        self.assertEqual(len(ofertas), 3)  # 2 variantes del primer producto + 1 del segundo
        self.assertEqual(ofertas[0]['plataforma'], "sumup")
        self.assertEqual(ofertas[0]['formato_gramos'], 250)
        self.assertEqual(ofertas[1]['formato_gramos'], 1000)

    def test_parse_html_nextjs_dom(self):
        html = """
        <html>
        <body>
            <a data-analytics="product-list-item" data-item-id="item-cabra-1" data-item-name="Café Etiopía Yirgacheffe 250g" href="/product/etiopia-yirgacheffe">
                <img src="https://cdn.sumup.store/img/etiopia.jpg" />
                <span data-selector="os-theme-product-list-name">Café Etiopía Yirgacheffe 250g</span>
                <span data-selector="price">$ 9.990</span>
            </a>
            <a data-analytics="product-list-item" data-item-id="item-cabra-2" data-item-name="Café Colombia Geisha 250g" href="/product/colombia-geisha">
                <img src="https://cdn.sumup.store/img/geisha.jpg" />
                <span data-selector="os-theme-product-list-name">Café Colombia Geisha 250g</span>
                <span data-selector="price">$ 14.500</span>
                <span class="product-sold-out-label">Agotado</span>
            </a>
        </body>
        </html>
        """
        productos = self.driver.parse_html_productos(html, "https://tienda.cafecabra.cl")
        self.assertEqual(len(productos), 2)
        p1 = productos[0]
        self.assertEqual(p1['nombre'], "Café Etiopía Yirgacheffe 250g")
        self.assertEqual(p1['id_externo'], "item-cabra-1")
        self.assertEqual(p1['url_detalle'], "https://tienda.cafecabra.cl/product/etiopia-yirgacheffe")
        self.assertEqual(p1['variantes'][0]['precio_clp'], 9990)
        self.assertTrue(p1['variantes'][0]['disponible'])

        p2 = productos[1]
        self.assertEqual(p2['nombre'], "Café Colombia Geisha 250g")
        self.assertEqual(p2['variantes'][0]['precio_clp'], 14500)
        self.assertFalse(p2['variantes'][0]['disponible'])


if __name__ == '__main__':
    unittest.main()

