import unittest
from domain.search_normalizer import expand_search_terms, get_synonym_group, strip_accents


class TestSearchNormalizer(unittest.TestCase):
    def test_strip_accents(self):
        self.assertEqual(strip_accents("Café Borbón Anaeróbico"), "cafe borbon anaerobico")

    def test_geisha_synonyms(self):
        group = get_synonym_group("geisha")
        self.assertIn("gesha", group)
        self.assertIn("geisha", group)

        group_gesha = get_synonym_group("gesha")
        self.assertIn("geisha", group_gesha)

    def test_bourbon_synonyms(self):
        group = get_synonym_group("borbón")
        self.assertIn("bourbon", group)
        self.assertIn("borbon", group)

    def test_anaerobic_synonyms(self):
        group = get_synonym_group("anaerobio")
        self.assertIn("anaeróbico", group)
        self.assertIn("anaerobico", group)

    def test_washed_synonyms(self):
        group = get_synonym_group("lavado")
        self.assertIn("washed", group)

    def test_expand_search_terms(self):
        terms = expand_search_terms("geisha")
        self.assertIn("geisha", terms)
        self.assertIn("gesha", terms)

        multi_terms = expand_search_terms("café lavado")
        self.assertTrue(any("washed" in t for t in multi_terms))

    def test_classify_product_category(self):
        from domain.search_normalizer import classify_product_category
        # Cafés válidos
        self.assertEqual(classify_product_category("COLOMBIA - FINCA LA ESPERANZA"), "cafe")
        self.assertEqual(classify_product_category("GESHA - LAVADO"), "cafe")
        self.assertEqual(classify_product_category("Café Origami Cup SJ Heirloom 100gr"), "cafe")
        self.assertEqual(classify_product_category("Pack 4 Blend's Puelo"), "cafe")
        
        # No cafés (ropa, suscripciones, regalos, vajilla, cafeteras/máquinas)
        self.assertEqual(classify_product_category("Polera Prueba"), "no_cafe")
        self.assertEqual(classify_product_category("BOLSO CAFÉ 3CICLOS x @TEBAL"), "no_cafe")
        self.assertEqual(classify_product_category("Suscripción de café"), "no_cafe")
        self.assertEqual(classify_product_category("Taza Puelo Coffee Roasters"), "no_cafe")
        self.assertEqual(classify_product_category("Caja Regalo Vida Lodge 250gr"), "no_cafe")
        self.assertEqual(classify_product_category("Muela de Titanio para Molino Timemore Slim"), "no_cafe")
        self.assertEqual(classify_product_category("Aeropress Clear"), "no_cafe")
        self.assertEqual(classify_product_category("La Marzocco Linea PB"), "no_cafe")
        self.assertEqual(classify_product_category("Taller de Filtrado - Método V60"), "no_cafe")


if __name__ == "__main__":
    unittest.main()


