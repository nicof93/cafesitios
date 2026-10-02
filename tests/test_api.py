import sys
from pathlib import Path
import unittest
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app
from api.router import get_db_session, get_product_detail, get_stores_summary
from api.schemas import ProductDetailResponse
from db.database import (
    Base,
    HistorialPrecio,
    NotaCata,
    Producto,
    ProductoNotaCata,
    Tienda,
    Variante,
)
from domain.models import CoffeeProductDomain, VariantDomain
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

client = TestClient(app)

class MockDatabaseSession:
    pass

class MockCoffeeRepositoryForAPI:
    def __init__(self, session=None):
        pass

    def get_cheapest_products(self, **kwargs):
        return [
            CoffeeProductDomain(
                id=1,
                tienda="Singular Coffee",
                nombre="Café Test",
                url_detalle="https://singular.cl/p1",
                imagen=None,
                descripcion="Floral",
                variante_mas_barata=VariantDomain(
                    id_externo="v1", opcion="250g", formato_gramos=250,
                    precio_clp=10000, precio_original_clp=10000, en_oferta=False,
                    descuento_porcentaje=0, precio_por_kilo=40000.0, disponible=True
                )
            )
        ]

    def count_cheapest_products(self, **kwargs):
        return 2

def mock_get_db_session_override():
    yield MockDatabaseSession()

app.dependency_overrides[get_db_session] = mock_get_db_session_override

class TestAPI(unittest.TestCase):
    def test_product_detail_returns_description_and_all_variants(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        try:
            store = Tienda(nombre="Tienda Demo", url_base="https://example.com")
            product = Producto(
                tienda=store,
                nombre="Café de prueba",
                url_detalle="https://example.com/cafe",
                descripcion=(
                    '<p>Notas de <strong>cacao</strong></p>'
                    '<script>alert("xss")</script>'
                    '<img src="javascript:alert(1)" onerror="alert(1)">'
                ),
                proceso="natural",
                finca="Los Robles",
                variedad="Caturra",
                elevacion_min_msnm=1650,
                elevacion_max_msnm=1800,
                cosecha="2024/25",
                fermentacion_tipo="anaeróbica",
                fermentacion_horas=72,
                caracteristicas_fuente={
                    "finca": {"texto": "Finca: Los Robles", "confianza": 0.95, "version": "rules-v1"}
                },
            )
            product.notas_cata = [ProductoNotaCata(
                nota=NotaCata(nombre="frutos rojos", clave_normalizada="frutos-rojos"),
                texto_origen="Perfil de taza: berries",
                confianza=0.9,
                version_extractor="rules-v1",
            )]
            product.variantes = [
                Variante(
                    id_variante_externo="variant-250",
                    opcion="Grano",
                    formato_gramos=250,
                    precio_clp=10000,
                    precio_original_clp=12000,
                    en_oferta=True,
                    descuento_porcentaje=17,
                    precio_por_kilo=40000,
                    disponible=True,
                    historial_precios=[
                        HistorialPrecio(
                            precio_clp=11000,
                            precio_original_clp=11000,
                            precio_por_kilo=44000,
                            fecha_registro=datetime(2026, 9, 1),
                        ),
                        HistorialPrecio(
                            precio_clp=10000,
                            precio_original_clp=10000,
                            precio_por_kilo=40000,
                            fecha_registro=datetime(2026, 9, 2),
                        ),
                    ],
                ),
                Variante(
                    id_variante_externo="variant-1000",
                    opcion="Grano",
                    formato_gramos=1000,
                    precio_clp=35000,
                    precio_original_clp=35000,
                    en_oferta=False,
                    descuento_porcentaje=0,
                    precio_por_kilo=35000,
                    disponible=False,
                ),
            ]
            session.add(product)
            session.commit()

            result = get_product_detail(product.id, session)

            self.assertEqual(result["descripcion"], '<p>Notas de <strong>cacao</strong></p>')
            self.assertEqual(result["tienda"], "Tienda Demo")
            self.assertEqual(result["proceso"], "natural")
            self.assertEqual(result["finca"], "Los Robles")
            self.assertEqual(result["elevacion_min_msnm"], 1650)
            self.assertEqual(result["fermentacion_horas"], 72)
            self.assertEqual(result["notas_cata"][0]["clave_normalizada"], "frutos-rojos")
            self.assertEqual(result["notas_cata"][0]["confianza"], 0.9)
            self.assertEqual(len(result["variantes"]), 2)
            self.assertEqual(result["variantes"][1]["formato_gramos"], 1000)
            self.assertFalse(result["variantes"][1]["disponible"])
            history = result["variantes"][0]["historial_precios"]
            self.assertEqual([item["precio_clp"] for item in history], [11000, 10000])
            validated_result = ProductDetailResponse.model_validate(result)
            self.assertEqual(len(validated_result.variantes[0].historial_precios), 2)

            product.activo = False
            session.commit()
            with self.assertRaises(HTTPException) as error:
                get_product_detail(product.id, session)
            self.assertEqual(error.exception.status_code, 404)
        finally:
            session.close()
            engine.dispose()

    def test_store_summary_excludes_inactive_stores_and_products(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        try:
            active_store = Tienda(nombre="Activa", url_base="https://active.example")
            disabled_store = Tienda(
                nombre="Desactivada",
                url_base="https://disabled.example",
                activo=False,
            )
            active_store.productos = [
                Producto(
                    nombre="Activo",
                    url_detalle="https://active.example/activo",
                    variantes=[Variante(
                        id_variante_externo="active-variant",
                        opcion="250g",
                        formato_gramos=250,
                        precio_clp=10000,
                        precio_original_clp=10000,
                        precio_por_kilo=40000,
                    )],
                ),
                Producto(
                    nombre="Eliminado lógico",
                    url_detalle="https://active.example/inactivo",
                    activo=False,
                    variantes=[Variante(
                        id_variante_externo="inactive-variant",
                        opcion="250g",
                        formato_gramos=250,
                        precio_clp=9000,
                        precio_original_clp=9000,
                        precio_por_kilo=36000,
                    )],
                ),
            ]
            disabled_store.productos = [Producto(
                nombre="Producto de tienda desactivada",
                url_detalle="https://disabled.example/producto",
                variantes=[Variante(
                    id_variante_externo="disabled-variant",
                    opcion="250g",
                    formato_gramos=250,
                    precio_clp=8000,
                    precio_original_clp=8000,
                    precio_por_kilo=32000,
                )],
            )]
            session.add_all([active_store, disabled_store])
            session.commit()

            summary = get_stores_summary(1, 10, "name_asc", session)

            self.assertEqual(summary["total_items"], 1)
            self.assertEqual(summary["items"], [{"nombre": "Activa", "cantidad_productos": 1}])
        finally:
            session.close()
            engine.dispose()

    def test_healthcheck(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "Cafe-sitios API"})

    def test_api_route_registered(self):
        # Patch PostgresCoffeeRepository in api.router
        import api.router
        original_repo = api.router.PostgresCoffeeRepository
        api.router.PostgresCoffeeRepository = MockCoffeeRepositoryForAPI
        try:
            response = client.get("/api/v1/products/cheapest?limit=5")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("data", data)
            self.assertEqual(data["total_items"], 2)
        finally:
            api.router.PostgresCoffeeRepository = original_repo

    def test_stores_summary_endpoint(self):
        response = client.get("/api/v1/stores?page=1&page_size=10&sort_by=product_count_desc")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertIn("total_items", data)
        self.assertTrue(isinstance(data["items"], list))

    def test_last_sync_endpoint_without_record(self):
        response = client.get("/api/v1/sync/last")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"last_sync": None})

if __name__ == "__main__":
    unittest.main()
