import sys
import json
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapper.woocommerce_driver import WooCommerceDriver

class TestWooCommerceDriver(unittest.TestCase):
    def setUp(self):
        self.driver = WooCommerceDriver(
            nombre="Café Altura",
            url_base="https://cafealtura.cl/wp-json/wc/store/v1/products"
        )
        json_path = Path(__file__).resolve().parent.parent / "examples-by-ecommerce-platform" / "woocommerce.json"
        with open(json_path, "r", encoding="utf-8") as f:
            self.sample_data = json.load(f)

    def test_extraer_gramos_variaciones(self):
        self.assertEqual(WooCommerceDriver.extraer_gramos("250-gr"), 250)
        self.assertEqual(WooCommerceDriver.extraer_gramos("1-kilo"), 1000)
        self.assertEqual(WooCommerceDriver.extraer_gramos("1 kilo"), 1000)
        self.assertEqual(WooCommerceDriver.extraer_gramos("Café Lavado 250g Molienda Fina"), 250)
        self.assertEqual(WooCommerceDriver.extraer_gramos("Bolsa Sin Peso", default=250), 250)

    def test_calcular_precio_por_kilo(self):
        precio_kilo = WooCommerceDriver.calcular_precio_por_kilo(13300, 250)
        self.assertEqual(precio_kilo, 53200.0)

        precio_kilo_1kg = WooCommerceDriver.calcular_precio_por_kilo(36900, 1000)
        self.assertEqual(precio_kilo_1kg, 36900.0)

        self.assertEqual(WooCommerceDriver.calcular_precio_por_kilo(0, 250), 0.0)

    def test_normalizar_producto_variable_completo(self):
        prod_raw = self.sample_data[0]  # Perú Finca Esperanza
        normalized = self.driver.normalizar_producto(prod_raw)

        self.assertEqual(normalized['tienda'], "Café Altura")
        self.assertEqual(normalized['nombre'], "Perú Finca Esperanza")
        self.assertEqual(normalized['url_detalle'], "https://cafealtura.cl/productos/peru-finca-esperanza/")
        self.assertTrue(normalized['imagen'].startswith("http"))
        self.assertEqual(len(normalized['variantes']), 10)

        # Variantes de 250g (precio mínimo del rango)
        var_250 = next(v for v in normalized['variantes'] if v['id_variante_externo'] == '68059')
        self.assertEqual(var_250['formato_gramos'], 250)
        self.assertEqual(var_250['precio_clp'], 13300)
        self.assertEqual(var_250['precio_por_kilo'], 53200.0)
        self.assertTrue(var_250['disponible'])
        self.assertIn("250 gr.", var_250['opcion'])

        # Variantes de 1kg (precio máximo del rango)
        var_1kg = next(v for v in normalized['variantes'] if v['id_variante_externo'] == '68063')
        self.assertEqual(var_1kg['formato_gramos'], 1000)
        self.assertEqual(var_1kg['precio_clp'], 36900)
        self.assertEqual(var_1kg['precio_por_kilo'], 36900.0)
        self.assertTrue(var_1kg['disponible'])
        self.assertIn("1 kilo", var_1kg['opcion'])

    def test_normalizar_producto_agotado_sin_variantes(self):
        prod_raw = self.sample_data[3]  # Pack 4: Perú el Pedregal 1 kg. + Cafetera...
        normalized = self.driver.normalizar_producto(prod_raw)

        self.assertEqual(len(normalized['variantes']), 1)
        var = normalized['variantes'][0]
        self.assertEqual(var['id_variante_externo'], '57014')
        self.assertEqual(var['formato_gramos'], 1000)
        self.assertFalse(var['disponible'])

if __name__ == "__main__":
    unittest.main()
