"""Módulo de enrutamiento principal de la API.

Re-exporta los enrutadores y controladores separados por entidad para
mantener compatibilidad total hacia atrás con importaciones existentes.
"""
from api.admin import router as admin_router
from api.dependencies import get_db_session
from api.products import (
    _DescriptionSanitizer,
    get_cheapest_coffee_products,
    get_product_detail,
    ofertas_router,
    router,
    router as products_router,
)
from api.stores import get_stores_summary, router as stores_router
from api.sync import (
    analitica_router,
    analitica_v1_router,
    get_current_sync_summary,
    get_last_sync,
    get_market_analytics,
    get_sync_history,
    router as sync_router,
    sincronizaciones_router,
    sincronizaciones_v1_router,
)
from infrastructure.postgres_repository import PostgresCoffeeRepository

__all__ = [
    "admin_router",
    "get_db_session",
    "router",
    "products_router",
    "stores_router",
    "sync_router",
    "sincronizaciones_router",
    "sincronizaciones_v1_router",
    "analitica_router",
    "analitica_v1_router",
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
