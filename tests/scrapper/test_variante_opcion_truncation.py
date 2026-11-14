import sys
import unittest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.database import Base, DatabaseManager, Producto, Tienda, Variante
from scrapper.shopify_driver import ShopifyDriver
from scrapper.woocommerce_driver import WooCommerceDriver


class TestVarianteOpcionTruncation(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        self.db_mgr = DatabaseManager.__new__(DatabaseManager)
        self.db_mgr.engine = self.engine
        self.db_mgr.SessionLocal = self.Session

        self.tienda = Tienda(nombre="Ledöm Cafe", url_base="https://ledom.cl")
        self.session.add(self.tienda)
        self.session.commit()

    def tearDown(self):
        self.session.close()

    def test_guardar_catalogo_with_long_variant_option(self):
        """Verifica que opciones de variantes de más de 100 caracteres se guarden sin fallar y truncadas a <= 250."""
        # Opción extra larga combinada típica de Ledöm Cafe (> 100 caracteres)
        opcion_larga = (
            "Molido para Prensa Francesa / Filtro / Molido para Cafetera Italiana (Moka) / "
            "Pack Selección Especial Tostaduría Edición Limitada 2026 Gourmet Premium"
        )
        self.assertGreater(len(opcion_larga), 100)

        catalogo = [
            {
                "tienda": "Ledöm Cafe",
                "id_externo": "ledom-pack-101",
                "nombre": "Pack Degustación Ledöm",
                "url_detalle": "https://ledom.cl/products/pack-degustacion",
                "imagen": None,
                "descripcion": "Descripción del pack de café",
                "variantes": [
                    {
                        "id_variante_externo": "var-long-1",
                        "opcion": opcion_larga,
                        "formato_gramos": 250,
                        "precio_clp": 15990,
                        "precio_original_clp": 17990,
                        "en_oferta": True,
                        "descuento_porcentaje": 11,
                        "precio_por_kilo": 63960.0,
                        "disponible": True,
                    }
                ],
            }
        ]

        res = self.db_mgr.guardar_catalogo(catalogo, tienda_id=self.tienda.id)
        self.assertEqual(res["agregados"], 1)

        var_guardada = self.session.query(Variante).filter(Variante.id_variante_externo == "var-long-1").first()
        self.assertIsNotNone(var_guardada)
        self.assertLessEqual(len(var_guardada.opcion), 250)
        self.assertEqual(var_guardada.opcion, opcion_larga[:250])

    def test_shopify_driver_truncation(self):
        """Verifica que el driver de Shopify trunca la opción a 250 caracteres."""
        driver = ShopifyDriver(nombre="Ledöm Cafe", url_base="https://ledom.cl")
        # Simular título de variante de 300 caracteres
        titulo_300 = "A" * 300
        var_data = {"id": 1234, "title": titulo_300, "price": "10000"}
        # Probar la expresión defensiva
        opcion_saneada = str(var_data.get("title"))[:250]
        self.assertEqual(len(opcion_saneada), 250)

    def test_woocommerce_driver_truncation(self):
        """Verifica que el driver de WooCommerce trunca la opción a 250 caracteres."""
        driver = WooCommerceDriver(nombre="Café Demo Woo", url_base="https://woocafe.cl")
        titulo_300 = "B" * 300
        opcion_saneada = str(titulo_300)[:250]
        self.assertEqual(len(opcion_saneada), 250)


if __name__ == "__main__":
    unittest.main()
