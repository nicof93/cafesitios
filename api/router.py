"""Módulo de enrutamiento principal de la API.

Re-exporta los enrutadores y controladores separados por entidad para
mantener compatibilidad total hacia atrás con importaciones existentes.
"""
from api.dependencies import get_db_session
from api.products import (
    _DescriptionSanitizer,
    get_cheapest_coffee_products,
    get_product_detail,
    router,
    router as products_router,
)
from api.stores import get_stores_summary, router as stores_router
from api.sync import get_last_sync, router as sync_router
from infrastructure.postgres_repository import PostgresCoffeeRepository

__all__ = [
    "get_db_session",
    "router",
    "products_router",
    "stores_router",
    "sync_router",
    "get_product_detail",
    "get_cheapest_coffee_products",
    "get_stores_summary",
    "get_last_sync",
    "_DescriptionSanitizer",
    "PostgresCoffeeRepository",
]
