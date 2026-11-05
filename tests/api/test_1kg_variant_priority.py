import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, Producto, Tienda, Variante
from infrastructure.postgres_repository import PostgresCoffeeRepository


class Test1KgVariantPriority(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        self.session = self.SessionLocal()
        # Crear tienda
        self.tienda = Tienda(
            nombre="Cafeterra Single Origin",
            url_base="https://cafeterra.cl",
            plataforma="shopify",
            activo=True,
        )
        self.session.add(self.tienda)
        self.session.commit()
        self.session.refresh(self.tienda)

        # Crear producto con variantes: 2000g (2kg a $57.900 -> $28.950/kg), 1000g (1kg a $31.900 -> $31.900/kg), 250g ($11.490 -> $45.960/kg)
        self.prod_con_1kg = Producto(
            tienda_id=self.tienda.id,
            nombre="Café Colombia El Vergel",
            url_detalle="https://cafeterra.cl/products/el-vergel",
            activo=True,
            oculto_catalogo=False,
            categoria="cafe",
        )
        self.session.add(self.prod_con_1kg)
        self.session.commit()
        self.session.refresh(self.prod_con_1kg)

        v_2kg = Variante(
            producto_id=self.prod_con_1kg.id,
            id_variante_externo="var-2kg",
            opcion="2kg",
            formato_gramos=2000,
            precio_clp=57900,
            precio_original_clp=57900,
            precio_por_kilo=28950.0,
            es_estimado=True,
            disponible=True,
        )
        v_1kg = Variante(
            producto_id=self.prod_con_1kg.id,
            id_variante_externo="var-1kg",
            opcion="1kg",
            formato_gramos=1000,
            precio_clp=31900,
            precio_original_clp=31900,
            precio_por_kilo=31900.0,
            es_estimado=False,
            disponible=True,
        )
        v_250g = Variante(
            producto_id=self.prod_con_1kg.id,
            id_variante_externo="var-250g",
            opcion="250g",
            formato_gramos=250,
            precio_clp=11490,
            precio_original_clp=11490,
            precio_por_kilo=45960.0,
            es_estimado=True,
            disponible=True,
        )
        self.session.add_all([v_2kg, v_1kg, v_250g])

        # Crear producto sin 1kg (solo 250g y 500g)
        self.prod_sin_1kg = Producto(
            tienda_id=self.tienda.id,
            nombre="Café Etiopía Guji",
            url_detalle="https://cafeterra.cl/products/etiopia-guji",
            activo=True,
            oculto_catalogo=False,
            categoria="cafe",
        )
        self.session.add(self.prod_sin_1kg)
        self.session.commit()
        self.session.refresh(self.prod_sin_1kg)

        v_sin_500g = Variante(
            producto_id=self.prod_sin_1kg.id,
            id_variante_externo="var-guji-500g",
            opcion="500g",
            formato_gramos=500,
            precio_clp=18000,
            precio_original_clp=18000,
            precio_por_kilo=36000.0,
            es_estimado=True,
            disponible=True,
        )
        v_sin_250g = Variante(
            producto_id=self.prod_sin_1kg.id,
            id_variante_externo="var-guji-250g",
            opcion="250g",
            formato_gramos=250,
            precio_clp=10000,
            precio_original_clp=10000,
            precio_por_kilo=40000.0,
            es_estimado=True,
            disponible=True,
        )
        self.session.add_all([v_sin_500g, v_sin_250g])
        self.session.commit()

    def tearDown(self):
        self.session.query(Variante).delete()
        self.session.query(Producto).delete()
        self.session.query(Tienda).delete()
        self.session.commit()
        self.session.close()

    def test_producto_con_1kg_prioriza_formato_1000g_y_no_estima_desde_2kg(self):
        repo = PostgresCoffeeRepository(self.session)
        products = repo.get_cheapest_products(sort_by="kilo", limit=10, search_query="El Vergel")
        
        self.assertEqual(len(products), 1)
        prod = products[0]
        self.assertEqual(prod.nombre, "Café Colombia El Vergel")
        
        # Debe haber elegido la variante de 1kg (1000g) a $31.900, NO la de 2kg ($28.950)
        best_var = prod.variante_mas_barata
        self.assertEqual(best_var.formato_gramos, 1000)
        self.assertEqual(best_var.precio_clp, 31900)
        self.assertEqual(best_var.precio_por_kilo, 31900.0)
        self.assertFalse(best_var.es_estimado, "El formato de 1kg debe tener es_estimado = False")

    def test_producto_sin_1kg_mantiene_seleccion_por_menor_precio_por_kilo(self):
        repo = PostgresCoffeeRepository(self.session)
        products = repo.get_cheapest_products(sort_by="kilo", limit=10, search_query="Guji")
        
        self.assertEqual(len(products), 1)
        prod = products[0]
        best_var = prod.variante_mas_barata
        # Como no tiene 1kg, toma la más económica por kilo disponible (500g a $36.000/kg)
        self.assertEqual(best_var.formato_gramos, 500)
        self.assertEqual(best_var.precio_por_kilo, 36000.0)


if __name__ == "__main__":
    unittest.main()

