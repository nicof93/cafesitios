import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapper.coffee_metadata import (
    extract_coffee_characteristics,
    summarize_extraction_coverage,
)


class TestCoffeeMetadataExtraction(unittest.TestCase):
    def test_extracts_fields_from_html_tables_and_section_headings(self):
        description = """
        <h4>Detalles</h4>
        <table>
            <tr><th>País de origen</th><td>Etiopía</td></tr>
            <tr><th>Proceso</th><td>Honey</td></tr>
            <tr><th>Finca</th><td>Los Robles</td></tr>
            <tr><th>Varietal</th><td>Bourbon, Caturra</td></tr>
            <tr><th>Elevación</th><td>1.650 - 1.800 m.s.n.m.</td></tr>
            <tr><th>Cosecha</th><td>2024/25</td></tr>
            <tr><th>Fermentación</th><td>Anaeróbica, 72 horas</td></tr>
        </table>
        <h4>Perfil de taza</h4>
        <p>Berries, cocoa y panela</p>
        """

        result = extract_coffee_characteristics(description)

        self.assertEqual(result['proceso'], 'honey')
        self.assertEqual(result['pais_origen'], 'Etiopía')
        self.assertEqual(result['finca'], 'Los Robles')
        self.assertEqual(result['variedad'], 'Bourbon, Caturra')
        self.assertEqual(result['elevacion_min_msnm'], 1650)
        self.assertEqual(result['elevacion_max_msnm'], 1800)
        self.assertEqual(result['cosecha'], '2024/25')
        self.assertEqual(result['fermentacion_tipo'], 'anaeróbica')
        self.assertEqual(result['fermentacion_horas'], 72)
        self.assertEqual(
            [note['clave_normalizada'] for note in result['notas_cata']],
            ['frutos-rojos', 'cacao', 'panela'],
        )
        self.assertTrue(result['notas_cata_mencionadas'])
        self.assertIn('72 horas', result['fuentes']['fermentacion_horas']['texto'])

    def test_aliases_and_prefix_variations_produce_the_same_note_keys(self):
        description = """
        <p>Country of origin: Guatemala</p>
        <p><strong>Process:</strong> washed</p>
        <p>Tasting notes - red berries, chocolate</p>
        <p>Altitude 1,600–1,800 meters above sea level</p>
        <p>Fermentation time: 36 h, anaerobic</p>
        """

        result = extract_coffee_characteristics(description)

        self.assertEqual(result['proceso'], 'lavado')
        self.assertEqual(result['pais_origen'], 'Guatemala')
        self.assertEqual(
            [note['clave_normalizada'] for note in result['notas_cata']],
            ['frutos-rojos', 'chocolate'],
        )
        self.assertEqual(result['elevacion_min_msnm'], 1600)
        self.assertEqual(result['elevacion_max_msnm'], 1800)
        self.assertEqual(result['fermentacion_horas'], 36)

    def test_missing_characteristics_remain_unknown(self):
        result = extract_coffee_characteristics('<p>Café dulce y equilibrado.</p>')

        self.assertIsNone(result['proceso'])
        self.assertIsNone(result['finca'])
        self.assertIsNone(result['variedad'])
        self.assertIsNone(result['pais_origen'])
        self.assertIsNone(result['elevacion_min_msnm'])
        self.assertIsNone(result['elevacion_max_msnm'])
        self.assertIsNone(result['cosecha'])
        self.assertIsNone(result['fermentacion_tipo'])
        self.assertIsNone(result['fermentacion_horas'])
        self.assertEqual(result['notas_cata'], [])
        self.assertFalse(result['notas_cata_mencionadas'])

    def test_summarizes_per_field_extraction_coverage(self):
        results = [
            extract_coffee_characteristics('<p>Proceso: Natural</p><p>Notas: Panela</p>'),
            extract_coffee_characteristics('<p>Café dulce y equilibrado.</p>'),
        ]

        coverage = summarize_extraction_coverage(results)

        self.assertEqual(coverage['total'], 2)
        self.assertEqual(coverage['con_datos'], 1)
        self.assertEqual(coverage['porcentaje_con_datos'], 50.0)
        self.assertEqual(coverage['campos']['proceso']['detectados'], 1)
        self.assertEqual(coverage['campos']['notas_cata']['detectados'], 1)
        self.assertEqual(coverage['campos']['finca']['detectados'], 0)

    def test_skips_decorative_lines_after_section_heading(self):
        result = extract_coffee_characteristics(
            '<h4>PERFIL DE TAZA</h4><p>________________________</p>'
            '<p>Chocolate, mora y panela</p>'
        )

        self.assertEqual(
            [note['clave_normalizada'] for note in result['notas_cata']],
            ['chocolate', 'mora', 'panela'],
        )


if __name__ == '__main__':
    unittest.main()