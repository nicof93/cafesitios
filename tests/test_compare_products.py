import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, Producto, Tienda, Variante
from application.compare_products import CompareProductsUseCase


class TestCompareProducts(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

        self.store = Tienda(nombre="Café Demo", url_base="https://cafedemo.cl")
        self.session.add(self.store)
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_deduplication_by_weight_rule_rn_03(self):
        # Café con múltiples variantes de molienda para el mismo formato (250g)
        prod = Producto(
            tienda=self.store,
            nombre="Geisha Panamá",
            url_detalle="https://cafedemo.cl/geisha",
            variantes=[
                Variante(
                    id_variante_externo="v1",
                    opcion="250g - Grano Entero",
                    formato_gramos=250,
                    precio_clp=15000,
                    precio_original_clp=15000,
                    precio_por_kilo=60000,
                    disponible=True,
                ),
                Variante(
                    id_variante_externo="v2",
                    opcion="250g - Molienda Espresso",
                    formato_gramos=250,
                    precio_clp=14000,  # Más barata
                    precio_original_clp=14000,
                    precio_por_kilo=56000,
                    disponible=True,
                ),
                Variante(
                    id_variante_externo="v3",
                    opcion="250g - Molienda Filtro",
                    formato_gramos=250,
                    precio_clp=15000,
                    precio_original_clp=15000,
                    precio_por_kilo=60000,
                    disponible=True,
                ),
                Variante(
                    id_variante_externo="v4",
                    opcion="1kg - Grano Entero",
                    formato_gramos=1000,
                    precio_clp=45000,
                    precio_original_clp=45000,
                    precio_por_kilo=45000,
                    disponible=True,
                ),
            ],
        )
        self.session.add(prod)
        self.session.commit()

        use_case = CompareProductsUseCase(session=self.session)
        results = use_case.execute([prod.id])

        self.assertEqual(len(results), 1)
        comparado = results[0]
        # Debe haber exactamente 2 presentaciones deduplicadas (250g y 1000g), NO 4
        self.assertEqual(len(comparado.variantes_por_gramaje), 2)
        gramajes = [v.formato_gramos for v in comparado.variantes_por_gramaje]
        self.assertEqual(gramajes, [250, 1000])

        # Para 250g debe haber seleccionado la variante de 14.000 CLP (v2)
        v250 = comparado.variantes_por_gramaje[0]
        self.assertEqual(v250.precio_clp, 14000)
        self.assertEqual(v250.id_externo, "v2")

    def test_compare_limits_to_four_products(self):
        products = []
        for i in range(6):
            p = Producto(
                tienda=self.store,
                nombre=f"Café {i}",
                url_detalle=f"https://cafedemo.cl/p{i}",
                variantes=[Variante(
                    id_variante_externo=f"v_p{i}",
                    opcion="250g",
                    formato_gramos=250,
                    precio_clp=10000,
                    precio_original_clp=10000,
                    precio_por_kilo=40000,
                    disponible=True,
                )]
            )
            products.append(p)
        self.session.add_all(products)
        self.session.commit()

        use_case = CompareProductsUseCase(session=self.session)
        results = use_case.execute([p.id for p in products])
        self.assertEqual(len(results), 4)


if __name__ == "__main__":
    unittest.main()

