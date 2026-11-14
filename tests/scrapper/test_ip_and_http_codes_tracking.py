"""
Pruebas unitarias para trazabilidad de IP saliente y códigos HTTP de respuesta
en el pipeline de sincronización y registros de base de datos.
"""
import unittest
from unittest.mock import MagicMock, patch

from core.error_classifier import clasificar_error_sincronizacion, extraer_codigo_http
from scrapper_application import sincronizar_tienda, sincronizar_multiples_tiendas


class TestIpAndHttpCodesTracking(unittest.TestCase):

    def test_extraer_codigo_http_de_varias_fuentes(self):
        # 1. Sin error -> 200
        self.assertEqual(extraer_codigo_http(None), 200)

        # 2. Excepción con response.status_code (estilo requests.HTTPError)
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        err_with_resp = Exception("Too Many Requests")
        err_with_resp.response = mock_resp
        self.assertEqual(extraer_codigo_http(err_with_resp), 429)

        # 3. Excepción con status_code directo
        err_direct = Exception("Server Error")
        err_direct.status_code = 503
        self.assertEqual(extraer_codigo_http(err_direct), 503)

        # 4. Mensajes con texto explícito de código HTTP
        self.assertEqual(extraer_codigo_http("HTTP 404: Not Found"), 404)
        self.assertEqual(extraer_codigo_http("Client Error: 429 Too Many Requests"), 429)
        self.assertEqual(extraer_codigo_http("500 Internal Server Error"), 500)
        self.assertEqual(extraer_codigo_http("Status 502 Bad Gateway"), 502)
        self.assertEqual(extraer_codigo_http("Error 401 Unauthorized"), 401)

        # 5. Error sin código HTTP identificable
        self.assertIsNone(extraer_codigo_http("Conexión rechazada por timeout"))

    def test_clasificar_error_sincronizacion_incluye_codigo_http(self):
        # Éxito
        res_ok = clasificar_error_sincronizacion(None)
        self.assertEqual(res_ok["codigo_http"], 200)
        self.assertEqual(res_ok["codigo"], "OK")

        # 429
        res_429 = clasificar_error_sincronizacion("HTTP 429: Too Many Requests")
        self.assertEqual(res_429["codigo_http"], 429)
        self.assertEqual(res_429["codigo"], "BLOQUEO_BOT_O_RATE_LIMIT")

        # 500
        res_500 = clasificar_error_sincronizacion("500 Internal Server Error")
        self.assertEqual(res_500["codigo_http"], 500)
        self.assertEqual(res_500["codigo"], "ERROR_SERVIDOR_TIENDA")

    @patch("scrapper_application.consumir_productos_tienda")
    def test_sincronizar_tienda_exito_registra_ip_y_codigo_200(self, mock_consumir):
        mock_consumir.return_value = []
        mock_db = MagicMock()
        mock_db.obtener_tienda_por_id.return_value = {
            "id": 1,
            "nombre": "Café Test",
            "url_base": "https://cafetest.cl",
            "logo_url": "https://cafetest.cl/logo.png",
        }
        mock_db.iniciar_sincronizacion.return_value = 99
        mock_db.guardar_catalogo.return_value = {"agregados": 0, "eliminados": 0, "actualizados": 0}

        res = sincronizar_tienda(
            tienda={"id": 1, "nombre": "Café Test", "url_base": "https://cafetest.cl", "logo_url": "https://cafetest.cl/logo.png"},
            db=mock_db,
            ip_origen="200.1.2.3",
        )

        self.assertTrue(res["exito"])
        self.assertEqual(res["codigo_http"], 200)
        self.assertEqual(res["ip_origen"], "200.1.2.3")

        mock_db.iniciar_sincronizacion.assert_called_with(1, ip_origen="200.1.2.3")
        mock_db.finalizar_sincronizacion.assert_called_with(
            99,
            "exitoso",
            productos_agregados=0,
            productos_eliminados=0,
            productos_actualizados=0,
            codigo_http=200,
            ip_origen="200.1.2.3",
        )

    @patch("scrapper_application.consumir_productos_tienda")
    def test_sincronizar_tienda_error_429_registra_codigo_429_e_ip(self, mock_consumir):
        mock_consumir.side_effect = Exception("HTTP 429 Too Many Requests")
        mock_db = MagicMock()
        mock_db.iniciar_sincronizacion.return_value = 101

        res = sincronizar_tienda(
            tienda={"id": 2, "nombre": "Café 429", "url_base": "https://cafe429.cl", "logo_url": "logo.png"},
            db=mock_db,
            ip_origen="186.20.10.5",
        )

        self.assertFalse(res["exito"])
        self.assertEqual(res["codigo_http"], 429)
        self.assertEqual(res["ip_origen"], "186.20.10.5")

        mock_db.finalizar_sincronizacion.assert_called_with(
            101,
            "fallido",
            detalle_error="[BLOQUEO_BOT_O_RATE_LIMIT] [HTTP 429] HTTP 429 Too Many Requests",
            codigo_http=429,
            ip_origen="186.20.10.5",
        )

    @patch("scrapper_application.obtener_diagnostico_red")
    @patch("scrapper_application.sincronizar_tienda")
    def test_sincronizar_multiples_tiendas_agrega_resumen_codigos(self, mock_sync_tienda, mock_diag):
        mock_diag.return_value = {"ip_publica": "190.10.20.30", "headers": {}}
        mock_db = MagicMock()

        # Simular 2 tiendas: una 200 OK y una 429 Rate Limit
        mock_sync_tienda.side_effect = [
            {"tienda_id": 1, "nombre": "T1", "exito": True, "total_productos": 5, "productos_nuevos": 1, "productos_actualizados": 4, "codigo_http": 200, "ip_origen": "190.10.20.30"},
            {"tienda_id": 2, "nombre": "T2", "exito": False, "total_productos": 0, "productos_nuevos": 0, "productos_actualizados": 0, "error": "429", "codigo_http": 429, "ip_origen": "190.10.20.30"},
        ]

        tiendas = [{"id": 1, "nombre": "T1"}, {"id": 2, "nombre": "T2"}]
        batch_res = sincronizar_multiples_tiendas(tiendas, db=mock_db, max_workers=1, registrar_log_global=True)

        self.assertEqual(batch_res["ip_origen"], "190.10.20.30")
        self.assertEqual(batch_res["resumen_codigos"], {"200": 1, "429": 1})

        # Verificar que se llamó registrar_sincronizacion_log con ip_origen y resumen_codigos
        mock_db.registrar_sincronizacion_log.assert_called_once()
        _, kwargs = mock_db.registrar_sincronizacion_log.call_args
        self.assertEqual(kwargs["ip_origen"], "190.10.20.30")
        self.assertEqual(kwargs["resumen_codigos"], {"200": 1, "429": 1})


if __name__ == "__main__":
    unittest.main()
