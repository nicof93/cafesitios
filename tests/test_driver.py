import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapper.shopify_driver import ShopifyDriver

class TestShopifyDriver(unittest.TestCase):
    def test_consumir_productos_preserves_external_product_id(self):
        driver = ShopifyDriver('Tienda Demo', 'https://example.com/products.json')
        response = Mock(status_code=200)
        response.json.return_value = {
            'products': [{
                'id': 456,
                'title': 'Café Demo',
                'handle': 'cafe-demo',
                'variants': [{
                    'id': 789,
                    'title': '250g',
                    'price': '10000',
                    'grams': 250,
                    'available': True,
                }],
            }],
        }

        with patch('scrapper.shopify_driver.requests.get', return_value=response):
            products = driver.consumir_productos()

        self.assertEqual(products[0]['id_externo'], '456')

    def test_extraer_gramos_250g(self):
        gramos = ShopifyDriver.extraer_gramos("Café Lavado 250g Molienda Fina")
        self.assertEqual(gramos, 250)

    def test_extraer_gramos_1kg(self):
        gramos = ShopifyDriver.extraer_gramos("Bolsa Formato 1kg Grano Entero")
        self.assertEqual(gramos, 1000)

    def test_extraer_gramos_default(self):
        gramos = ShopifyDriver.extraer_gramos("Bolsa Especialidad Sin Peso Especificado")
        self.assertEqual(gramos, 250)

    def test_calcular_precio_por_kilo(self):
        precio_kilo = ShopifyDriver.calcular_precio_por_kilo(10000, 250)
        self.assertEqual(precio_kilo, 40000.0)

    def test_calcular_precio_por_kilo_regalo(self):
        precio_kilo = ShopifyDriver.calcular_precio_por_kilo(0, 250)
        self.assertEqual(precio_kilo, 0.0)

if __name__ == "__main__":
    unittest.main()
