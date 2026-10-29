import sys
import time
import unittest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.extractor import CoffeeAttributesExtractor, compute_description_hash
from core.normalizer import SCAFlavorWheelNormalizer, calcular_precio_kilo
from db.database import Base, Cafe, OfertaTienda, Tienda, DatabaseManager


class TestExtractionPipeline(unittest.TestCase):
    def setUp(self):
        self.extractor = CoffeeAttributesExtractor()

        # Muestras reales de tiendas chilenas
        self.sample_singular_coffee = (
            "Origen: Colombia, Huila\n"
            "Finca: El Paraíso\n"
            "Productor: Diego Bermúdez\n"
            "Variedad: Castillo\n"
            "Proceso: Anaeróbico\n"
            "Lote: DP-04\n"
            "Notas de cata: Frutilla, Frambuesa, Chocolate blanco, Vainilla"
        )

        self.sample_cafe_triciclo = (
            "Etiopía Yirgacheffe\n"
            "Origen: Etiopía\n"
            "Variedad: Heirloom\n"
            "Proceso: Lavado\n"
            "Altura: 1950 msnm\n"
            "Notas de cata: Jazmín, Bergamota, Té negro, Limón"
        )

        self.sample_artisan_roast = (
            "Brasil Fazenda Rainha\n"
            "Origen: Brasil\n"
            "Finca: Fazenda Rainha\n"
            "Variedad: Yellow Bourbon\n"
            "Proceso: Natural\n"
            "Notas de cata: Caramelo, Almendras tostadas, Chocolate con leche, Panela"
        )

    def test_singular_coffee_extraction_and_sca_mapping(self):
        start_time = time.time()
        result = self.extractor.extract(self.sample_singular_coffee, nombre_producto="Colombia El Paraíso")
        duration = time.time() - start_time

        self.assertLess(duration, 0.1, "La extracción de Capa 1 debe tardar menos de 100 ms")
        self.assertEqual(result["capa"], 1)
        self.assertGreaterEqual(result["confianza"], 0.90)

        # Atributos botánicos
        self.assertEqual(result["origen"], "Colombia")
        self.assertEqual(result["variedad"], "Castillo")
        self.assertEqual(result["proceso"], "Anaeróbico")
        self.assertIn("Diego Bermúdez", result["finca_productor"])
        self.assertEqual(result["lote"], "DP-04")

        # Rueda SCA
        familias = result["macro_familias"]
        self.assertIn("Frutal / Frutos Rojos", familias)
        self.assertIn("Dulce / Chocolate", familias)
        self.assertIn("Frutilla", result["notas_normalizadas"])
        self.assertIn("Frambuesa", result["notas_normalizadas"])
        self.assertIn("Vainilla", result["notas_normalizadas"])

    def test_cafe_triciclo_extraction_and_sca_mapping(self):
        result = self.extractor.extract(self.sample_cafe_triciclo, nombre_producto="Etiopía Yirgacheffe")

        self.assertEqual(result["origen"], "Etiopía")
        self.assertEqual(result["variedad"], "Heirloom")
        self.assertEqual(result["proceso"], "Lavado")

        familias = result["macro_familias"]
        self.assertIn("Floral", familias)
        self.assertIn("Frutal / Cítrico", familias)
        self.assertIn("Jazmín", result["notas_normalizadas"])
        self.assertIn("Limón", result["notas_normalizadas"])

    def test_artisan_roast_extraction_and_sca_mapping(self):
        result = self.extractor.extract(self.sample_artisan_roast, nombre_producto="Brasil Fazenda Rainha")

        self.assertEqual(result["origen"], "Brasil")
        self.assertIn("Bourbon", result["variedad"])
        self.assertEqual(result["proceso"], "Natural")

        familias = result["macro_familias"]
        self.assertIn("Dulce / Chocolate", familias)
        self.assertIn("Frutos Secos", familias)
        self.assertIn("Caramelo", result["notas_normalizadas"])
        self.assertIn("Almendra", result["notas_normalizadas"])
        self.assertIn("Chocolate con leche", result["notas_normalizadas"])

    def test_hash_diffing_idempotency(self):
        h1 = compute_description_hash(self.sample_singular_coffee)
        h2 = compute_description_hash(self.sample_singular_coffee)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 32)

        # Si el hash existente es igual, extract no debe intentar re-procesar con capas generativas
        res = self.extractor.extract(self.sample_singular_coffee, existing_hash=h1)
        self.assertEqual(res["hash_descripcion"], h1)

    def test_precio_kilo_rn02(self):
        # 1. Caso oficial con unit_price (Shopify / e-commerce)
        precio_kilo, es_estimado = calcular_precio_kilo(
            precio_clp=14990,
            formato_gramos=250,
            unit_price=59960.0
        )
        self.assertEqual(precio_kilo, 59960.0)
        self.assertFalse(es_estimado, "Debe ser es_estimado = False si unit_price es oficial")

        # 2. Caso estimado a partir de gramos
        precio_kilo_est, es_estimado_est = calcular_precio_kilo(
            precio_clp=12500,
            formato_gramos=250,
            unit_price=None
        )
        self.assertEqual(precio_kilo_est, 50000.0)
        self.assertTrue(es_estimado_est, "Debe ser es_estimado = True si se infiere por gramos")

        # 3. Caso 1kg
        precio_kilo_1k, es_estimado_1k = calcular_precio_kilo(
            precio_clp=38000,
            formato_gramos=1000,
            unit_price=None
        )
        self.assertEqual(precio_kilo_1k, 38000.0)
        self.assertTrue(es_estimado_1k)

    def test_database_persistence_cascade(self):
        # Base de datos en memoria para probar persistencia de cafes y ofertas_tienda
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Crear tienda
        tienda = Tienda(nombre="Singular Coffee", url_base="https://singularcoffee.cl")
        session.add(tienda)
        session.commit()

        # Instanciar DatabaseManager mockeado con el engine en memoria
        db_mgr = DatabaseManager.__new__(DatabaseManager)
        db_mgr.engine = engine
        db_mgr.SessionLocal = Session

        # Ejecutar extracción
        data_singular = self.extractor.extract(self.sample_singular_coffee, nombre_producto="Colombia El Paraíso")
        catalogo_cascada = [{
            "nombre": "Colombia El Paraíso",
            "origen": data_singular["origen"],
            "finca_productor": data_singular["finca_productor"],
            "variedad": data_singular["variedad"],
            "proceso": data_singular["proceso"],
            "lote": data_singular["lote"],
            "notas_cata": data_singular["notas_cata"],
            "notas_normalizadas": data_singular["notas_normalizadas"],
            "hash_descripcion": data_singular["hash_descripcion"],
            "ofertas": [
                {
                    "precio_actual": 14990,
                    "formato_gramos": 250,
                    "precio_por_kilo": 59960.0,
                    "es_estimado": True,
                    "link_detalle": "https://singularcoffee.cl/products/colombia-el-paraiso",
                    "disponible": True,
                }
            ]
        }]

        res_counts = db_mgr.guardar_cafes_cascada(catalogo_cascada, tienda_id=tienda.id)
        self.assertEqual(res_counts["cafes_agregados"], 1)
        self.assertEqual(res_counts["ofertas_guardadas"], 1)

        # Validar en base de datos
        cafe_guardado = session.query(Cafe).filter(Cafe.nombre == "Colombia El Paraíso").first()
        self.assertIsNotNone(cafe_guardado)
        self.assertEqual(cafe_guardado.origen, "Colombia")
        self.assertEqual(cafe_guardado.variedad, "Castillo")
        self.assertEqual(cafe_guardado.proceso, "Anaeróbico")

        oferta_guardada = session.query(OfertaTienda).filter(OfertaTienda.cafe_id == cafe_guardado.id).first()
        self.assertIsNotNone(oferta_guardada)
        self.assertEqual(oferta_guardada.precio_actual, 14990)
        self.assertEqual(float(oferta_guardada.precio_por_kilo), 59960.0)
        self.assertTrue(oferta_guardada.es_estimado)

    def test_layer_2_gliner_fallback_invocation(self):
        # Texto narrativo no estructurado (sin dos puntos ni etiquetas)
        unstructured_text = "Un café extraordinario cosechado a mano con sabores silvestres."
        extractor = CoffeeAttributesExtractor()

        class FakeGLiNER:
            def predict_entities(self, text, labels, threshold=0.4):
                return [
                    {"label": "nota_de_cata", "text": "Jazmín"},
                    {"label": "variedad_cafe", "text": "Geisha"},
                    {"label": "proceso_beneficio", "text": "Lavado"},
                    {"label": "finca_o_productor", "text": "Hacienda La Esmeralda"},
                ]

        extractor._gliner_pipeline = FakeGLiNER()
        result = extractor.extract(unstructured_text)

        self.assertEqual(result["capa"], 2)
        self.assertEqual(result["variedad"], "Geisha")
        self.assertEqual(result["proceso"], "Lavado")
        self.assertIn("Jazmín", result["notas_normalizadas"])
        self.assertIn("Floral", result["macro_familias"])

    def test_layer_3_llm_fallback_invocation(self):
        # Texto donde Capa 1 y 2 no logran extraer y el hash es nuevo
        unstructured_text = "Grano seleccionado de altura con notas increíbles."
        extractor = CoffeeAttributesExtractor(qwen_model_path="dummy/path/qwen.gguf")

        class FakeLLM:
            def __call__(self, prompt, **kwargs):
                return {
                    "choices": [
                        {
                            "text": '{"origen": "Guatemala", "variedad": "Pacamara", "proceso": "Honey", "notas": ["Miel", "Manzana verde"]}'
                        }
                    ]
                }

        extractor._llm_instance = FakeLLM()
        result = extractor.extract(unstructured_text)

        self.assertEqual(result["capa"], 3)
        self.assertEqual(result["origen"], "Guatemala")
        self.assertEqual(result["variedad"], "Pacamara")
        self.assertEqual(result["proceso"], "Honey")
        self.assertIn("Miel", result["notas_normalizadas"])
        self.assertIn("Manzana verde", result["notas_normalizadas"])

    def test_origin_extracted_from_title_when_missing_in_body(self):
        description_without_origin = """
        Proceso: Lavado
        Variedad: Caturra
        Notas: Naranja, Caramelo
        """
        result = self.extractor.extract(description_without_origin, nombre_producto="Café Colombia Huila 250g")
        self.assertEqual(result["origen"], "Colombia")
        self.assertEqual(result["variedad"], "Caturra")
        self.assertEqual(result["proceso"], "Lavado")

    def test_sca_score_and_agtron_extraction(self):
        text_with_sca_and_agtron = """
        Origen: Etiopía
        Proceso: Natural
        Variedad: Heirloom
        Puntuación SCA: 88.75 pts
        Escala Agtron: 72
        Notas: Jazmín, Arándano, Miel
        """
        result = self.extractor.extract(text_with_sca_and_agtron, nombre_producto="Etiopía Bombe")
        self.assertEqual(result["puntuacion_sca"], 88.75)
        self.assertEqual(result["escala_agtron"], 72)
        self.assertEqual(result["tueste"], "Medio-Claro (Agtron 72)")

    def test_sca_score_extracted_from_title(self):
        text_simple = "Proceso: Lavado\nNotas: Floral"
        result = self.extractor.extract(text_simple, nombre_producto="Panamá Geisha 89.5 SCA")
        self.assertEqual(result["origen"], "Panamá")
        self.assertEqual(result["puntuacion_sca"], 89.5)

    def test_guardar_cafes_cascada_truncates_long_lote(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        tienda = Tienda(nombre="Tienda Lote Largo", url_base="https://ejemplo.cl")
        session.add(tienda)
        session.commit()

        db_mgr = DatabaseManager.__new__(DatabaseManager)
        db_mgr.engine = engine
        db_mgr.SessionLocal = Session

        long_lote = "Bourbon, Caturra y Catuaí— son en realidad una familia: Caturra es una mutación de Bourbon, y Catuaí es hija de Caturra"
        self.assertGreater(len(long_lote), 100)

        catalogo_cascada = [{
            "nombre": "Qawale",
            "origen": "Guatemala",
            "variedad": "Bourbon",
            "proceso": "Lavado",
            "lote": long_lote,
            "notas_cata": ["Manzana Verde", "Panela", "Vainilla"],
            "notas_normalizadas": ["Manzana verde", "Panela", "Vainilla"],
            "hash_descripcion": "0f9409599568013d0b1605411ab8f6db",
            "ofertas": [
                {
                    "precio_actual": 12990,
                    "formato_gramos": 250,
                    "precio_por_kilo": 51960.0,
                    "es_estimado": True,
                    "link_detalle": "https://ejemplo.cl/products/qawale",
                    "disponible": True,
                }
            ]
        }]

        res_counts = db_mgr.guardar_cafes_cascada(catalogo_cascada, tienda_id=tienda.id)
        self.assertEqual(res_counts["cafes_agregados"], 1)

        cafe_guardado = session.query(Cafe).filter(Cafe.nombre == "Qawale").first()
        self.assertIsNotNone(cafe_guardado)
        self.assertLessEqual(len(cafe_guardado.lote), 100)
        self.assertEqual(cafe_guardado.lote, long_lote[:100])


if __name__ == "__main__":
    unittest.main()

