import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, Producto, Tienda, Variante
from application.recommend_products import RecommendProductsUseCase


class TestRecommendations(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

        self.store = Tienda(nombre="Tienda Roaster", url_base="https://roaster.cl")
        self.session.add(self.store)
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_recommendation_flavor_and_stock_scoring(self):
        # Café frutal en stock
        prod_frutal = Producto(
            tienda=self.store,
            nombre="Etiopía Yirgacheffe",
            descripcion="Notas muy frutales a bergamota y naranja",
            proceso="lavado",
            tueste="claro",
            url_detalle="https://roaster.cl/etiopia",
            variantes=[Variante(
                id_variante_externo="v_et",
                opcion="250g",
                formato_gramos=250,
                precio_clp=12000,
                precio_original_clp=12000,
                precio_por_kilo=48000,
                disponible=True,
            )]
        )

        # Café achocolatado pero agotado
        prod_choco_agotado = Producto(
            tienda=self.store,
            nombre="Brasil Cerrado",
            descripcion="Cuerpo denso, notas a chocolate y nuez",
            proceso="natural",
            tueste="medio",
            url_detalle="https://roaster.cl/brasil",
            variantes=[Variante(
                id_variante_externo="v_br",
                opcion="250g",
                formato_gramos=250,
                precio_clp=9000,
                precio_original_clp=9000,
                precio_por_kilo=36000,
                disponible=False,  # Agotado -> debe penalizar -50 pts
            )]
        )

        self.session.add_all([prod_frutal, prod_choco_agotado])
        self.session.commit()

        use_case = RecommendProductsUseCase(session=self.session)
        recommendations = use_case.execute(
            metodo="Filtro/Goteo",
            perfil_sabor="Frutal/Cítrico",
            tueste="Claro",
            limit=5
        )

        self.assertEqual(len(recommendations), 2)
        # El primero debe ser el frutal disponible
        self.assertEqual(recommendations[0].id, prod_frutal.id)
        self.assertTrue(recommendations[0].disponible)
        self.assertGreater(recommendations[0].puntaje_coincidencia, recommendations[1].puntaje_coincidencia)

        # El producto agotado debe tener puntaje reducido por penalización
        self.assertFalse(recommendations[1].disponible)


if __name__ == "__main__":
    unittest.main()

