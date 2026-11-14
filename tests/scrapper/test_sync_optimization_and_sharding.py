import unittest
from unittest.mock import MagicMock, patch
from scrapper_application import (
    obtener_diagnostico_red,
    sincronizar_multiples_tiendas,
    sincronizar_tienda,
)
from scrapper.shopify_driver import ShopifyDriver
from scrapper.woocommerce_driver import WooCommerceDriver
from core.error_classifier import clasificar_error_sincronizacion


class TestSyncOptimizationAndSharding(unittest.TestCase):
    def test_obtener_diagnostico_red(self):
        """Verifica que el diagnóstico de red retorne IP y headers base válidos."""
        diag = obtener_diagnostico_red()
        self.assertIn("ip_publica", diag)
        self.assertIn("headers", diag)
        self.assertIn("User-Agent", diag["headers"])
        self.assertTrue(len(diag["ip_publica"]) > 0)

    def test_sharding_distribution(self):
        """Verifica que el particionamiento uniforme distribuya 42 tiendas equitativamente en 2 shards sin solapamiento."""
        total_tiendas = 42
        tiendas_simuladas = [{"id": i, "nombre": f"Tienda {i}"} for i in range(1, total_tiendas + 1)]

        total_shards = 2
        shard_1 = [t for idx, t in enumerate(tiendas_simuladas) if (idx % total_shards) == 0]
        shard_2 = [t for idx, t in enumerate(tiendas_simuladas) if (idx % total_shards) == 1]

        self.assertEqual(len(shard_1), 21)
        self.assertEqual(len(shard_2), 21)

        ids_1 = {t["id"] for t in shard_1}
        ids_2 = {t["id"] for t in shard_2}

        # Sin intersección y cubriendo el 100% de las tiendas
        self.assertEqual(len(ids_1.intersection(ids_2)), 0)
        self.assertEqual(ids_1.union(ids_2), {t["id"] for t in tiendas_simuladas})

    @patch("scrapper_application.sincronizar_tienda")
    def test_sincronizar_multiples_tiendas_concurrent(self, mock_sincronizar):
        """Verifica que sincronizar_multiples_tiendas procese en hilos concurrentes y agregue métricas."""
        mock_sincronizar.side_effect = [
            {
                "tienda_id": 1,
                "nombre": "Tienda 1",
                "exito": True,
                "total_productos": 10,
                "productos_nuevos": 2,
                "productos_actualizados": 8,
                "productos_eliminados": 0,
                "duracion_segundos": 0.5,
                "error": None,
                "codigo_error": "OK",
            },
            {
                "tienda_id": 2,
                "nombre": "Tienda 2",
                "exito": False,
                "total_productos": 0,
                "productos_nuevos": 0,
                "productos_actualizados": 0,
                "productos_eliminados": 0,
                "duracion_segundos": 0.3,
                "error": "HTTP 429 Too Many Requests: Rate limit excedido",
                "codigo_error": "BLOQUEO_BOT_O_RATE_LIMIT",
                "categoria_error": "Bloqueo Anti-Bot o Límite de Peticiones (429/403)",
                "mensaje_amigable": "Rate limit alcanzado",
            },
        ]

        mock_db = MagicMock()
        tiendas = [{"id": 1, "nombre": "Tienda 1"}, {"id": 2, "nombre": "Tienda 2"}]

        res = sincronizar_multiples_tiendas(
            tiendas=tiendas,
            db=mock_db,
            max_workers=2,
            registrar_log_global=False,
        )

        self.assertEqual(res["total_tiendas"], 2)
        self.assertEqual(res["tiendas_exitosas"], 1)
        self.assertEqual(res["tiendas_fallidas"], 1)
        self.assertEqual(res["total_productos_sincronizados"], 10)
        self.assertEqual(res["total_productos_nuevos"], 2)
        self.assertEqual(res["total_productos_actualizados"], 8)
        self.assertEqual(len(res["detalles"]), 2)

    def test_rate_limit_429_classification(self):
        """Verifica que cualquier excepción con código 429 se clasifique como BLOQUEO_BOT_O_RATE_LIMIT."""
        err1 = RuntimeError("HTTP 429 Too Many Requests: Rate limit excedido")
        diag1 = clasificar_error_sincronizacion(err1)
        self.assertEqual(diag1["codigo"], "BLOQUEO_BOT_O_RATE_LIMIT")
        self.assertTrue(diag1["es_error"])

        err2 = "429 Client Error: Too Many Requests for url: https://ejemplo.cl/products.json"
        diag2 = clasificar_error_sincronizacion(err2)
        self.assertEqual(diag2["codigo"], "BLOQUEO_BOT_O_RATE_LIMIT")
        self.assertTrue(diag2["es_error"])

    @patch.object(ShopifyDriver, "_fetch_url_content")
    def test_shopify_driver_rate_limit_429_stops_immediately(self, mock_fetch):
        """Verifica que si Shopify responde con 429, se eleve inmediatamente el error de rate limit."""
        mock_fetch.side_effect = RuntimeError("HTTP 429 Too Many Requests: Rate limit excedido")

        driver = ShopifyDriver(nombre="Tienda 429", url_base="https://tienda429.cl/products.json")
        with self.assertRaises(RuntimeError) as ctx:
            driver.consumir_productos()

        self.assertIn("429", str(ctx.exception))
        self.assertIn("Rate limit", str(ctx.exception))

    @patch.object(ShopifyDriver, "_fetch_url_content")
    @patch.object(ShopifyDriver, "extraer_ficha_tecnica_html")
    def test_shopify_driver_html_fallback_capped_at_three(self, mock_html, mock_fetch):
        """Verifica que el fallback HTML no supere el límite de 3 llamadas por tienda."""
        # Mock de catálogo con 10 productos sin notas ni atributos clave
        productos_mock = [
            {
                "id": i,
                "title": f"Café Especial #{i}",
                "handle": f"cafe-{i}",
                "body_html": f"<p>Café de origen {i}</p>",
                "variants": [{"id": 100 + i, "title": "250g", "price": "12000", "grams": 250}],
            }
            for i in range(1, 11)
        ]
        mock_fetch.return_value = {"products": productos_mock}
        mock_html.return_value = {"notas_cata": ["Frutal"]}

        driver = ShopifyDriver(nombre="Tienda Muchos Cafés", url_base="https://tienda.cl/products.json")
        prods = driver.consumir_productos()

        self.assertEqual(len(prods), 10)
        # Debe haberse llamado máximo 3 veces a extraer_ficha_tecnica_html
        self.assertEqual(mock_html.call_count, 3)


if __name__ == "__main__":
    unittest.main()
