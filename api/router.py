"""Módulo de enrutamiento principal de la API.

Re-exporta los enrutadores y controladores separados por entidad para
mantener compatibilidad total hacia atrás con importaciones existentes.
"""
from api.admin import administracion_router, router as admin_router
from api.app_plataforma import create_plataforma_app
from api.app_public import create_public_app
from api.dependencies import get_db_session
from api.feedback import router as feedback_router, sugerencias_router
from api.products import (
    _DescriptionSanitizer,
    get_cheapest_coffee_products,
    get_product_detail,
    ofertas_router,
    productos_router,
    router,
    router as products_router,
)
from api.stores import get_stores_summary, router as stores_router, tiendas_router
from api.sync import (
    analitica_router,
    analitica_v1_router,
    get_current_sync_summary,
    get_last_sync,
    get_market_analytics,
    get_sync_history,
    router as sync_router,
    sincronizacion_router,
    sincronizaciones_router,
    sincronizaciones_v1_router,
)
from api.orders import pedidos_router, router as orders_router
from api.telemetry import router as telemetry_router, telemetria_router
from infrastructure.postgres_repository import PostgresCoffeeRepository

__all__ = [
    "create_public_app",
    "create_plataforma_app",
    "admin_router",
    "administracion_router",
    "get_db_session",
    "router",
    "products_router",
    "productos_router",
    "stores_router",
    "tiendas_router",
    "sync_router",
    "sincronizacion_router",
    "sincronizaciones_router",
    "sincronizaciones_v1_router",
    "analitica_router",
    "analitica_v1_router",
    "feedback_router",
    "sugerencias_router",
    "telemetry_router",
    "telemetria_router",
    "orders_router",
    "pedidos_router",
    "get_product_detail",
    "get_cheapest_coffee_products",
    "get_stores_summary",
    "get_last_sync",
    "get_current_sync_summary",
    "get_sync_history",
    "get_market_analytics",
    "_DescriptionSanitizer",
    "PostgresCoffeeRepository",
]
