import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import VariantDomain, CoffeeProductDomain

class TestDomain(unittest.TestCase):
    def test_variant_domain_creation(self):
        variant = VariantDomain(
            id_externo="v123",
            opcion="250g",
            formato_gramos=250,
            precio_clp=8500,
            precio_original_clp=10000,
            en_oferta=True,
            descuento_porcentaje=15,
            precio_por_kilo=34000.0,
            disponible=True
        )
        self.assertEqual(variant.id_externo, "v123")
        self.assertEqual(variant.formato_gramos, 250)
        self.assertEqual(variant.precio_por_kilo, 34000.0)
        self.assertTrue(variant.en_oferta)

    def test_coffee_product_domain_creation(self):
        variant = VariantDomain(
            id_externo="v123",
            opcion="250g",
            formato_gramos=250,
            precio_clp=8500,
            precio_original_clp=8500,
            en_oferta=False,
            descuento_porcentaje=0,
            precio_por_kilo=34000.0,
            disponible=True
        )
        product = CoffeeProductDomain(
            id=1,
            tienda="Singular Coffee",
            nombre="Café Colombia Geisha",
            url_detalle="https://singularcoffee.cl/products/geisha",
            imagen="https://singularcoffee.cl/img.jpg",
            descripcion="Notas florales y jazmín",
            variante_mas_barata=variant
        )
        self.assertEqual(product.id, 1)
        self.assertEqual(product.tienda, "Singular Coffee")
        self.assertEqual(product.variante_mas_barata.precio_clp, 8500)

if __name__ == "__main__":
    unittest.main()
