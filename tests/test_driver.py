import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapper.shopify_driver import ShopifyDriver
import scrapper_application

class TestShopifyDriver(unittest.TestCase):
    def test_unknown_legacy_platform_tries_supported_drivers(self):
        class FailingDriver:
            def __init__(self, nombre, url_base):
                pass

            def consumir_productos(self):
                raise RuntimeError('Shopify endpoint not found')

        class WooCommerceFallbackDriver:
            def __init__(self, nombre, url_base):
                pass

            def consumir_productos(self):
                return [{'nombre': 'Producto Woo detectado'}]

        tienda = {
            'nombre': 'Tienda heredada',
            'url_base': 'https://example.com/producto',
            'plataforma': 'desconocida',
        }
        with patch.dict(
            scrapper_application.drivers_por_plataforma,
            {'shopify': FailingDriver, 'woocommerce': WooCommerceFallbackDriver},
            clear=True,
        ):
            products = scrapper_application.consumir_productos_tienda(tienda)

        self.assertEqual(products, [{'nombre': 'Producto Woo detectado'}])

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

    def test_configured_platform_falls_back_when_primary_driver_fails(self):
        class FailingShopifyDriver:
            def __init__(self, nombre, url_base):
                pass

            def consumir_productos(self):
                raise RuntimeError('No Shopify endpoints responded')

        class WorkingWooDriver:
            def __init__(self, nombre, url_base):
                pass

            def consumir_productos(self):
                return [{'nombre': 'Café recuperado por WooCommerce'}]

        tienda = {
            'nombre': 'Tienda mal etiquetada',
            'url_base': 'https://example.com',
            'plataforma': 'shopify',
        }
        with patch.dict(
            scrapper_application.drivers_por_plataforma,
            {'shopify': FailingShopifyDriver, 'woocommerce': WorkingWooDriver},
            clear=True,
        ):
            products = scrapper_application.consumir_productos_tienda(tienda)

        self.assertEqual(products, [{'nombre': 'Café recuperado por WooCommerce'}])

    def test_shopify_driver_ignores_200_json_without_products_key_and_tries_next_endpoint(self):
        driver = ShopifyDriver('Apricot', 'https://apricot.cl/collections/cafe')
        invalid_resp = Mock(status_code=200)
        invalid_resp.json.return_value = {'collection': {'title': 'Café'}}
        valid_resp = Mock(status_code=200)
        valid_resp.json.return_value = {
            'products': [{
                'id': 101,
                'title': 'Etiopía Guji',
                'handle': 'etiopia-guji',
                'variants': [{
                    'id': 202,
                    'title': '250g',
                    'price': '14500',
                    'grams': 250,
                    'available': True,
                }],
            }],
        }

        with patch('scrapper.shopify_driver.requests.get', side_effect=[invalid_resp, valid_resp]):
            products = driver.consumir_productos()

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['nombre'], 'Etiopía Guji')

if __name__ == "__main__":
    unittest.main()

