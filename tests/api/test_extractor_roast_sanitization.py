import unittest
from core.extractor import CoffeeAttributesExtractor, clean_html_to_text, normalize_roast_level


class TestExtractorRoastSanitization(unittest.TestCase):
    """Valida la sanitización estricta de HTML y URLs al extraer el nivel de tueste y escala Agtron."""

    def setUp(self):
        self.extractor = CoffeeAttributesExtractor()

    def test_clean_html_removes_attributes_and_links(self):
        raw_html = (
            '<li><strong>Tueste:</strong> Medio, tostado en Santiago de Chile</li>'
            '<p><a href="https://cafesinfiltro.cl/blogs/tipos-de-tueste-de-cafe" '
            'rel="noopener noreferrer" target="_blank">guía sobre los tipos de tueste del café</a></p>'
        )
        cleaned = clean_html_to_text(raw_html)
        self.assertNotIn('rel="noopener noreferrer"', cleaned)
        self.assertNotIn('target="_blank"', cleaned)
        self.assertNotIn('href=', cleaned)
        self.assertIn('Tueste: Medio, tostado en Santiago de Chile', cleaned)

    def test_extract_roast_from_sin_filtro_html(self):
        desc = (
            '<div class="product-content">'
            '<ul>'
            '<li><strong>Proceso:</strong> Lavado</li>'
            '<li><strong>Tueste:</strong> Medio, tostado en Santiago de Chile</li>'
            '<li><strong>Notas de cata:</strong> avellana, caramelo y chocolate</li>'
            '</ul>'
            '<p>Revisa nuestra <a href="https://cafesinfiltro.cl/blogs/blogsinfiltro/tipos-de-tueste-de-cafe" '
            'rel="noopener noreferrer" target="_blank">guía sobre los tipos de tueste del café</a>.</p>'
            '</div>'
        )
        res = self.extractor.extract(desc, nombre_producto="Café Bolivia Catuai")
        self.assertEqual(res.get("tueste"), "Medio")
        self.assertNotIn("rel=", str(res.get("tueste")))
        self.assertNotIn("guía", str(res.get("tueste")).lower())

    def test_normalize_roast_level_rejects_dirty_strings(self):
        dirty_samples = [
            'De-cafe" rel="noopener noreferrer" target="_blank">guía sobre los tipos de tueste del café',
            '<a href="http://example.com">Tueste</a>',
            'http://tienda.cl/tueste',
            'En chile',
            'Local',
            'Que exista',
        ]
        for sample in dirty_samples:
            self.assertIsNone(normalize_roast_level(sample), f"Debería haber descartado: {sample}")

    def test_normalize_roast_level_accepts_canonical_levels(self):
        self.assertEqual(normalize_roast_level("Tueste Claro"), "Claro")
        self.assertEqual(normalize_roast_level("Medio-claro (City)"), "Medio-Claro")
        self.assertEqual(normalize_roast_level("Medio, tostado artesanal"), "Medio")
        self.assertEqual(normalize_roast_level("Omniroast"), "Medio")
        self.assertEqual(normalize_roast_level("Medio-oscuro (Full City+)"), "Medio-Oscuro")
        self.assertEqual(normalize_roast_level("Oscuro / Espresso Roast"), "Oscuro")
        self.assertEqual(normalize_roast_level("Muy Oscuro (French)"), "Muy Oscuro")


if __name__ == "__main__":
    unittest.main()

