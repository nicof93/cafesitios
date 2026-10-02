import sys
from pathlib import Path
import unittest
from typing import List, Literal, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import CoffeeProductDomain, VariantDomain
from domain.repositories import ICoffeeRepository
from application.get_cheapest_products import GetCheapestProductsUseCase
from db.database import Base, Producto, Tienda, Variante
from infrastructure.postgres_repository import PostgresCoffeeRepository

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

    def count_cheapest_products(
        self, sort_by: Literal["kilo", "unit"] = "kilo", only_available: bool = True,
        store_name: Optional[str] = None, min_weight_g: Optional[int] = None,
        max_weight_g: Optional[int] = None, search_query: Optional[str] = None,
        min_price: Optional[int] = None, max_price: Optional[int] = None
    ) -> int:
        prods = list(self.sample_products)
        if search_query:
            prods = [p for p in prods if search_query.lower() in p.nombre.lower()]
        return len(prods)

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

    def test_repository_counts_and_returns_unique_products(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        try:
            store = Tienda(nombre="WR4 / WRoasters", url_base="https://wr4.example")
            multi_variant_product = Producto(
                tienda=store,
                nombre="Café con varias presentaciones",
                url_detalle="https://wr4.example/producto-1",
                variantes=[
                    Variante(
                        id_variante_externo="wr4-250",
                        opcion="Grano",
                        formato_gramos=250,
                        precio_clp=12000,
                        precio_original_clp=12000,
                        en_oferta=False,
                        descuento_porcentaje=0,
                        precio_por_kilo=48000,
                        disponible=True,
                    ),
                    Variante(
                        id_variante_externo="wr4-500",
                        opcion="Grano",
                        formato_gramos=500,
                        precio_clp=20000,
                        precio_original_clp=20000,
                        en_oferta=False,
                        descuento_porcentaje=0,
                        precio_por_kilo=40000,
                        disponible=True,
                    ),
                ],
            )
            single_variant_product = Producto(
                tienda=store,
                nombre="Café de una presentación",
                url_detalle="https://wr4.example/producto-2",
                variantes=[
                    Variante(
                        id_variante_externo="wr4-1000",
                        opcion="Grano",
                        formato_gramos=1000,
                        precio_clp=45000,
                        precio_original_clp=45000,
                        en_oferta=False,
                        descuento_porcentaje=0,
                        precio_por_kilo=45000,
                        disponible=True,
                    ),
                ],
            )
            session.add_all([multi_variant_product, single_variant_product])
            session.commit()

            repository = PostgresCoffeeRepository(session)
            products = repository.get_cheapest_products(limit=10, store_name="WR4 / WRoasters")

            self.assertEqual(repository.count_cheapest_products(store_name="WR4 / WRoasters"), 2)
            self.assertEqual(len(products), 2)
            self.assertEqual(len({product.id for product in products}), 2)
            self.assertEqual(products[0].variante_mas_barata.id_externo, "wr4-500")
        finally:
            session.close()
            engine.dispose()

if __name__ == "__main__":
    unittest.main()
