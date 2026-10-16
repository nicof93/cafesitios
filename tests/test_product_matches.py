import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, Producto, Tienda, Variante
from infrastructure.postgres_repository import PostgresCoffeeRepository


class TestProductMatches(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

        self.store1 = Tienda(nombre="Tostaduría 1", url_base="https://t1.cl")
        self.store2 = Tienda(nombre="Tostaduría 2", url_base="https://t2.cl")
        self.store3 = Tienda(nombre="Tostaduría 3", url_base="https://t3.cl")
        self.session.add_all([self.store1, self.store2, self.store3])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_strict_grain_identity_rule_rn_04(self):
        # Mismo lote de café vendido por Tostaduría 1 y Tostaduría 2:
        # Coincidencia en: País de origen, Finca, Variedad, Proceso
        prod_t1 = Producto(
            tienda=self.store1,
            nombre="Colombia El Paraíso",
            pais_origen="Colombia",
            finca="El Paraíso",
            variedad="Castillo",
            proceso="anaeróbico",
            url_detalle="https://t1.cl/el-paraiso",
            variantes=[Variante(
                id_variante_externo="v_t1",
                opcion="250g",
                formato_gramos=250,
                precio_clp=16000,
                precio_original_clp=16000,
                precio_por_kilo=64000,
                disponible=True,
            )]
        )

        prod_t2 = Producto(
            tienda=self.store2,
            nombre="El Paraíso Diego Bermúdez",
            pais_origen="Colombia",
            finca="El Paraíso",
            variedad="Castillo",
            proceso="anaerobio",  # Sinónimo de anaeróbico
            url_detalle="https://t2.cl/paraiso",
            variantes=[Variante(
                id_variante_externo="v_t2",
                opcion="250g",
                formato_gramos=250,
                precio_clp=14000,  # Más barato
                precio_original_clp=14000,
                precio_por_kilo=56000,
                disponible=True,
            )]
        )

        # Café distinto (otro origen / finca) en Tostaduría 3
        prod_t3 = Producto(
            tienda=self.store3,
            nombre="Etiopía Guji",
            pais_origen="Etiopía",
            finca="Guji Highland",
            variedad="Heirloom",
            proceso="natural",
            url_detalle="https://t3.cl/guji",
            variantes=[Variante(
                id_variante_externo="v_t3",
                opcion="250g",
                formato_gramos=250,
                precio_clp=13000,
                precio_original_clp=13000,
                precio_por_kilo=52000,
                disponible=True,
            )]
        )

        self.session.add_all([prod_t1, prod_t2, prod_t3])
        self.session.commit()

        repo = PostgresCoffeeRepository(self.session)
        matches = repo.find_matching_products(prod_t1.id)

        # Debe encontrar exactamente prod_t2 como coincidencia y excluir prod_t3 y a sí mismo
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].id, prod_t2.id)
        self.assertEqual(matches[0].tienda, "Tostaduría 2")
        self.assertEqual(matches[0].variante_mas_barata.precio_clp, 14000)


if __name__ == "__main__":
    unittest.main()

