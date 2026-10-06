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
    last_filters = {}

    def __init__(self, session=None):
        pass

    def get_cheapest_products(self, **kwargs):
        MockCoffeeRepositoryForAPI.last_filters = kwargs
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
        MockCoffeeRepositoryForAPI.last_filters = kwargs
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
                pais_origen="Etiopía",
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
            self.assertEqual(result["pais_origen"], "Etiopía")
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
            response = client.get(
                "/api/v1/products/cheapest?limit=5&process=natural&country=Etiop%C3%ADa"
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("data", data)
            self.assertEqual(data["total_items"], 2)
            self.assertEqual(api.router.PostgresCoffeeRepository.last_filters["process"], "natural")
            self.assertEqual(api.router.PostgresCoffeeRepository.last_filters["country"], "Etiopía")
        finally:
            api.router.PostgresCoffeeRepository = original_repo

    def test_api_route_accepts_advanced_catalog_filters(self):
        import api.router
        original_repo = api.router.PostgresCoffeeRepository
        api.router.PostgresCoffeeRepository = MockCoffeeRepositoryForAPI
        try:
            response = client.get(
                "/api/v1/products/cheapest?min_price=15000&max_price=30000&country=Etiop%C3%ADa"
                "&variety=Caturra&store_name=Singular&notes=floral"
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(api.router.PostgresCoffeeRepository.last_filters["min_price"], 15000)
            self.assertEqual(api.router.PostgresCoffeeRepository.last_filters["max_price"], 30000)
            self.assertEqual(api.router.PostgresCoffeeRepository.last_filters["country"], "Etiopía")
            self.assertEqual(api.router.PostgresCoffeeRepository.last_filters["variety"], "Caturra")
            self.assertEqual(api.router.PostgresCoffeeRepository.last_filters["store_name"], "Singular")
            self.assertEqual(api.router.PostgresCoffeeRepository.last_filters["tasting_notes"], "floral")
        finally:
            api.router.PostgresCoffeeRepository = original_repo

    def test_stores_summary_endpoint(self):
        response = client.get("/api/v1/stores?page=1&page_size=10&sort_by=product_count_desc")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertIn("total_items", data)
        self.assertTrue(isinstance(data["items"], list))

    def test_get_products_renamed_endpoint(self):
        import api.router
        original_repo = api.router.PostgresCoffeeRepository
        api.router.PostgresCoffeeRepository = MockCoffeeRepositoryForAPI
        try:
            response = client.get("/api/v1/products?limit=5&process=natural&country=Etiop%C3%ADa")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("data", data)
            self.assertEqual(data["total_items"], 2)
            self.assertEqual(api.router.PostgresCoffeeRepository.last_filters["process"], "natural")
            self.assertEqual(api.router.PostgresCoffeeRepository.last_filters["country"], "Etiopía")
        finally:
            api.router.PostgresCoffeeRepository = original_repo

    def test_docs_and_redoc_disabled_in_production(self):
        import os
        import importlib
        import main

        old_env = os.environ.get("ENVIRONMENT")
        old_docs = os.environ.get("ENABLE_DOCS")
        try:
            os.environ["ENVIRONMENT"] = "production"
            os.environ.pop("ENABLE_DOCS", None)
            importlib.reload(main)
            self.assertIsNone(main.app.docs_url)
            self.assertIsNone(main.app.redoc_url)
            self.assertIsNone(main.app.openapi_url)
        finally:
            if old_env is not None:
                os.environ["ENVIRONMENT"] = old_env
            else:
                os.environ.pop("ENVIRONMENT", None)
            if old_docs is not None:
                os.environ["ENABLE_DOCS"] = old_docs
            else:
                os.environ.pop("ENABLE_DOCS", None)
            importlib.reload(main)

    def test_cors_allowed_origins_from_env(self):
        import os
        import importlib
        import main

        old_origins = os.environ.get("ALLOWED_ORIGINS")
        try:
            os.environ["ALLOWED_ORIGINS"] = "https://cafesitios.onrender.com, https://mi-frontend.vercel.app"
            importlib.reload(main)
            prod_client = TestClient(main.app)

            # Solicitud con origen no permitido (ej. localhost)
            res_blocked = prod_client.options(
                "/api/v1/products",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET"
                }
            )
            self.assertNotIn("access-control-allow-origin", res_blocked.headers)

            # Solicitud con origen permitido
            res_allowed = prod_client.options(
                "/api/v1/products",
                headers={
                    "Origin": "https://cafesitios.onrender.com",
                    "Access-Control-Request-Method": "GET"
                }
            )
            self.assertEqual(
                res_allowed.headers.get("access-control-allow-origin"),
                "https://cafesitios.onrender.com"
            )
        finally:
            if old_origins is not None:
                os.environ["ALLOWED_ORIGINS"] = old_origins
            else:
                os.environ.pop("ALLOWED_ORIGINS", None)
            importlib.reload(main)

    def test_proxy_middleware_enforces_origin_in_production(self):
        import os
        import importlib
        import main

        old_render = os.environ.get("RENDER")
        old_secret = os.environ.get("PROXY_SECRET")
        try:
            os.environ["RENDER"] = "true"
            os.environ.pop("PROXY_SECRET", None)
            importlib.reload(main)
            main.app.dependency_overrides[get_db_session] = mock_get_db_session_override
            prod_client = TestClient(main.app)

            # Healthcheck siempre permitido
            res_health = prod_client.get("/")
            self.assertEqual(res_health.status_code, 200)

            # Solicitud directa sin cabeceras de proxy debe ser 403 Forbidden
            res_direct = prod_client.get("/api/v1/sync/last")
            self.assertEqual(res_direct.status_code, 403)
            self.assertIn("Acceso directo a la API no permitido", res_direct.json()["detail"])

            # Solicitud con cabecera de proxy de Vercel debe ser permitida
            res_vercel = prod_client.get(
                "/api/v1/sync/last",
                headers={"x-vercel-id": "fra1::iad1::test"}
            )
            self.assertEqual(res_vercel.status_code, 200)

            # Solicitud con forwarded host de vercel
            res_forwarded = prod_client.get(
                "/api/v1/sync/last",
                headers={"x-forwarded-host": "cafesitios-app.vercel.app"}
            )
            self.assertEqual(res_forwarded.status_code, 200)

            # Prueba con PROXY_SECRET
            os.environ["PROXY_SECRET"] = "clave-super-secreta"
            importlib.reload(main)
            main.app.dependency_overrides[get_db_session] = mock_get_db_session_override
            secret_client = TestClient(main.app)

            res_bad_secret = secret_client.get(
                "/api/v1/sync/last",
                headers={"x-proxy-secret": "clave-incorrecta"}
            )
            self.assertEqual(res_bad_secret.status_code, 403)

            res_good_secret = secret_client.get(
                "/api/v1/sync/last",
                headers={"x-proxy-secret": "clave-super-secreta"}
            )
            self.assertEqual(res_good_secret.status_code, 200)
        finally:
            if old_render is not None:
                os.environ["RENDER"] = old_render
            else:
                os.environ.pop("RENDER", None)
            if old_secret is not None:
                os.environ["PROXY_SECRET"] = old_secret
            else:
                os.environ.pop("PROXY_SECRET", None)
            importlib.reload(main)
            main.app.dependency_overrides[get_db_session] = mock_get_db_session_override

if __name__ == "__main__":
    unittest.main()
