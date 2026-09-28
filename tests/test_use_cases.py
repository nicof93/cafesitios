import sys
from pathlib import Path
import unittest
from typing import List, Literal, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import CoffeeProductDomain, VariantDomain
from domain.repositories import ICoffeeRepository
from application.get_cheapest_products import GetCheapestProductsUseCase

class MockCoffeeRepository(ICoffeeRepository):
    def __init__(self):
        self.sample_products = [
            CoffeeProductDomain(
                id=1,
                tienda="Singular Coffee",
                nombre="Café Geisha",
                url_detalle="https://singular.cl/p1",
                imagen=None,
                descripcion="Floral",
                variante_mas_barata=VariantDomain(
                    id_externo="v1", opcion="250g", formato_gramos=250,
                    precio_clp=10000, precio_original_clp=10000, en_oferta=False,
                    descuento_porcentaje=0, precio_por_kilo=40000.0, disponible=True
                )
            ),
            CoffeeProductDomain(
                id=2,
                tienda="Café Triciclo",
                nombre="Café Bourbon",
                url_detalle="https://triciclo.cl/p2",
                imagen=None,
                descripcion="Cacao",
                variante_mas_barata=VariantDomain(
                    id_externo="v2", opcion="500g", formato_gramos=500,
                    precio_clp=12000, precio_original_clp=15000, en_oferta=True,
                    descuento_porcentaje=20, precio_por_kilo=24000.0, disponible=True
                )
            )
        ]

    def get_cheapest_products(
        self, sort_by: Literal["kilo", "unit"] = "kilo", limit: int = 10,
        only_available: bool = True, store_name: Optional[str] = None,
        min_weight_g: Optional[int] = None, max_weight_g: Optional[int] = None,
        search_query: Optional[str] = None, min_price: Optional[int] = None,
        max_price: Optional[int] = None
    ) -> List[CoffeeProductDomain]:
        prods = list(self.sample_products)
        if search_query:
            prods = [p for p in prods if search_query.lower() in p.nombre.lower()]
        if sort_by == "kilo":
            prods.sort(key=lambda p: p.variante_mas_barata.precio_por_kilo)
        else:
            prods.sort(key=lambda p: p.variante_mas_barata.precio_clp)
        return prods[:limit]

class TestUseCases(unittest.TestCase):
    def test_use_case_sort_by_kilo(self):
        repo = MockCoffeeRepository()
        use_case = GetCheapestProductsUseCase(repo)
        results = use_case.execute(sort_by="kilo")
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].nombre, "Café Bourbon")
        self.assertEqual(results[1].nombre, "Café Geisha")

    def test_use_case_sort_by_unit(self):
        repo = MockCoffeeRepository()
        use_case = GetCheapestProductsUseCase(repo)
        results = use_case.execute(sort_by="unit")
        
        self.assertEqual(results[0].nombre, "Café Geisha")
        self.assertEqual(results[1].nombre, "Café Bourbon")

    def test_use_case_search_query(self):
        repo = MockCoffeeRepository()
        use_case = GetCheapestProductsUseCase(repo)
        results = use_case.execute(search_query="Geisha")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].nombre, "Café Geisha")

if __name__ == "__main__":
    unittest.main()
