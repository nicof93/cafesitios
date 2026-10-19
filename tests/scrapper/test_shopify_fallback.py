import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scrapper.shopify_driver import ShopifyDriver
from core.extractor import CoffeeAttributesExtractor
from core.normalizer import SCAFlavorWheelNormalizer


class TestShopifyHybridFallback(unittest.TestCase):
    def setUp(self):
        self.driver = ShopifyDriver('Blackdrop Coffee', 'https://blackdrop.cl/products.json')

    def test_extraer_ficha_tecnica_texto_blackdrop_html(self):
        html_sample = """
        <div class="product-tabs">
            <div class="tab-pane active" id="tab-specs">
                <p><strong>TUESTE:</strong> Light</p>
                <p><strong>PERFIL:</strong> Floral y Frutal / Dulce</p>
                <p><strong>NOTAS:</strong> Cereza, ciruela, arandanos</p>
                <p><strong>PROCESO:</strong> Lavado</p>
            </div>
        </div>
        """
        ficha = ShopifyDriver.extraer_ficha_tecnica_texto(html_sample)
        self.assertEqual(ficha['tueste'], 'Light')
        self.assertEqual(ficha['perfil'], 'Floral y Frutal / Dulce')
        self.assertEqual(ficha['notas_cata'], ['Cereza', 'ciruela', 'arandanos'])
        self.assertEqual(ficha['proceso'], 'Lavado')

    def test_extraer_ficha_tecnica_html_http_error_returns_empty_and_does_not_crash(self):
        mock_response = Mock(status_code=429)
        with patch('scrapper.shopify_driver.requests.get', return_value=mock_response):
            with patch('scrapper.shopify_driver.logging.warning') as mock_warn:
                ficha = self.driver.extraer_ficha_tecnica_html('https://blackdrop.cl/products/cafe-grano-drip-etiopia')
                self.assertEqual(ficha, {})
                mock_warn.assert_called()

    def test_extraer_ficha_tecnica_html_timeout_returns_empty_and_does_not_crash(self):
        with patch('scrapper.shopify_driver.requests.get', side_effect=TimeoutError('Connection timed out')):
            with patch('scrapper.shopify_driver.logging.warning') as mock_warn:
                ficha = self.driver.extraer_ficha_tecnica_html('https://blackdrop.cl/products/cafe-grano-drip-etiopia')
                self.assertEqual(ficha, {})
                mock_warn.assert_called()

    def test_fallback_triggered_when_json_lacks_sensory_attributes(self):
        json_response = {
            'products': [{
                'id': 101,
                'title': 'Caja 5 Drip Coffee Etiopía',
                'handle': 'cafe-grano-drip-etiopia',
                'body_html': '<p>Drip coffee innovador para llevar. Café de origen Etiopía con 5 sobres.</p>',
                'images': [{'src': 'https://example.com/drip.jpg'}],
                'variants': [{
                    'id': 201,
                    'title': '5 sobres',
                    'price': '8990',
                    'grams': 50,
                    'available': True,
                }]
            }]
        }

        html_detail = """
        <div class="technical-sheet">
            <p><strong>TUESTE:</strong> Light</p>
            <p><strong>PERFIL:</strong> Floral y Frutal / Dulce</p>
            <p><strong>NOTAS:</strong> Cereza, ciruela, arandanos</p>
            <p><strong>PROCESO:</strong> Lavado</p>
        </div>
        """

        def mock_get(url, *args, **kwargs):
            if 'products.json' in url:
                resp = Mock(status_code=200)
                resp.json.return_value = json_response
                return resp
            elif 'cafe-grano-drip-etiopia' in url:
                resp = Mock(status_code=200, text=html_detail)
                return resp
            return Mock(status_code=404)

        with patch('scrapper.shopify_driver.requests.get', side_effect=mock_get):
            productos = self.driver.consumir_productos()

        self.assertEqual(len(productos), 1)
        p = productos[0]
        self.assertEqual(p['nombre'], 'Caja 5 Drip Coffee Etiopía')
        self.assertEqual(p['tueste'], 'Light')
        self.assertEqual(p['perfil'], 'Floral y Frutal / Dulce')
        self.assertEqual(p['notas_cata'], ['Cereza', 'ciruela', 'arandanos'])
        self.assertEqual(p['proceso'], 'Lavado')
        self.assertIn('NOTAS: Cereza, ciruela, arandanos', p['descripcion'])

        # Integración con normalizador SCA
        clasificacion = SCAFlavorWheelNormalizer.clasificar_notas(p['notas_cata'])
        self.assertIn('Frutal / Frutos Rojos', clasificacion['macro_familias'])

    def test_fallback_not_invoked_when_json_already_has_technical_attributes(self):
        driver_singular = ShopifyDriver('Singular Coffee', 'https://singularcoffee.cl/products.json')
        json_response = {
            'products': [{
                'id': 301,
                'title': 'Brasil Boa Vista',
                'handle': 'brasil-boa-vista',
                'body_html': """
                <p><strong>Proceso:</strong> Natural</p>
                <p><strong>Notas de cata:</strong> Chocolate, Caramelo y Avellana</p>
                <p><strong>Tueste:</strong> Medio</p>
                """,
                'images': [{'src': 'https://example.com/brasil.jpg'}],
                'variants': [{
                    'id': 401,
                    'title': '250g',
                    'price': '11990',
                    'grams': 250,
                    'available': True,
                }]
            }]
        }

        mock_resp_json = Mock(status_code=200)
        mock_resp_json.json.return_value = json_response

        with patch('scrapper.shopify_driver.requests.get', return_value=mock_resp_json) as mock_get:
            with patch.object(driver_singular, 'extraer_ficha_tecnica_html') as mock_fallback_html:
                productos = driver_singular.consumir_productos()

        # Verifica que extraer_ficha_tecnica_html NO fue llamada
        mock_fallback_html.assert_not_called()

        self.assertEqual(len(productos), 1)
        p = productos[0]
        self.assertEqual(p['tueste'], 'Medio')
        self.assertEqual(p['proceso'], 'Natural')
        self.assertEqual(p['notas_cata'], ['Chocolate', 'Caramelo', 'Avellana'])


if __name__ == '__main__':
    unittest.main()
