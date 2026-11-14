import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import core.extractor as extractor_module
from core.extractor import CoffeeAttributesExtractor


class TestGlinerCircuitBreaker(unittest.TestCase):
    def setUp(self):
        # Resetear estado global del circuit breaker antes de cada prueba
        extractor_module._GLINER_INSTANCE = None
        extractor_module._GLINER_DISABLED = False

    def tearDown(self):
        extractor_module._GLINER_INSTANCE = None
        extractor_module._GLINER_DISABLED = False

    def test_default_model_repo_id(self):
        """Verifica que el modelo por defecto sea urchade/gliner_multi-v2.1 o respete GLINER_MODEL_ID."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GLINER_MODEL_ID", None)
            extractor = CoffeeAttributesExtractor()
            self.assertEqual(extractor.gliner_model_name, "urchade/gliner_multi-v2.1")

        with patch.dict(os.environ, {"GLINER_MODEL_ID": "custom/gliner-test"}, clear=False):
            extractor = CoffeeAttributesExtractor()
            self.assertEqual(extractor.gliner_model_name, "custom/gliner-test")

    def test_circuit_breaker_on_401_error(self):
        """
        Simula error 401 Unauthorized al inicializar GLiNER.
        Verifica que solo se hace 1 intento de carga y el circuit breaker
        deshabilita la Capa 2 para todas las subsiguientes llamadas.
        """
        mock_gliner_class = MagicMock()
        mock_gliner_class.from_pretrained.side_effect = RuntimeError("HTTP 401 Unauthorized: Repository Not Found")

        # Texto que necesita Capa 2 (incompleto en Capa 1)
        unstructured_text = "Café delicioso tostado artesanalmente en Santiago con notas frutales exquisitas."

        extractor = CoffeeAttributesExtractor()

        with patch.dict("sys.modules", {"gliner": MagicMock(GLiNER=mock_gliner_class)}):
            # Primera llamada: falla e inicializa el circuit breaker
            res1 = extractor.extract(unstructured_text, nombre_producto="Café Desconocido 1")
            self.assertEqual(mock_gliner_class.from_pretrained.call_count, 1)
            self.assertTrue(extractor_module._GLINER_DISABLED)

            # Segunda llamada con otra instancia/producto: no debe intentar llamar a from_pretrained
            extractor2 = CoffeeAttributesExtractor()
            res2 = extractor2.extract(unstructured_text, nombre_producto="Café Desconocido 2")
            self.assertEqual(mock_gliner_class.from_pretrained.call_count, 1, "No debe repetir llamadas tras circuit breaker")

            # Tercera llamada directa a _extract_layer_2
            res3 = extractor2._extract_layer_2(unstructured_text, {"origen": None, "variedad": None, "proceso": None, "notas_cata": []})
            self.assertEqual(mock_gliner_class.from_pretrained.call_count, 1)

    def test_hf_token_handling(self):
        """Verifica que si HF_TOKEN está vacío no se envía token inválido."""
        mock_gliner_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.predict_entities.return_value = []
        mock_gliner_class.from_pretrained.return_value = mock_instance

        # Sin token
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HF_TOKEN", None)
            extractor = CoffeeAttributesExtractor()
            with patch.dict("sys.modules", {"gliner": MagicMock(GLiNER=mock_gliner_class)}):
                extractor._extract_layer_2("texto", {})
                mock_gliner_class.from_pretrained.assert_called_with("urchade/gliner_multi-v2.1")

        # Reset
        extractor_module._GLINER_INSTANCE = None
        extractor_module._GLINER_DISABLED = False
        mock_gliner_class.reset_mock()

        # Con token
        with patch.dict(os.environ, {"HF_TOKEN": "hf_secret_12345"}, clear=False):
            extractor = CoffeeAttributesExtractor()
            with patch.dict("sys.modules", {"gliner": MagicMock(GLiNER=mock_gliner_class)}):
                extractor._extract_layer_2("texto", {})
                mock_gliner_class.from_pretrained.assert_called_with("urchade/gliner_multi-v2.1", token="hf_secret_12345")


if __name__ == "__main__":
    unittest.main()
