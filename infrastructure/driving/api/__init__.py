"""Adaptadores HTTP (FastAPI) bajo la arquitectura hexagonal (infrastructure/driving/api)."""
from infrastructure.driving.api.sync_router import (
    analitica_router,
    analitica_v1_router,
    get_current_sync_summary,
    get_last_sync,
    get_market_analytics,
    get_sync_history,
    router,
    sincronizaciones_router,
    sincronizaciones_v1_router,
)

__all__ = [
    "router",
    "sincronizaciones_router",
    "sincronizaciones_v1_router",
    "analitica_router",
    "analitica_v1_router",
    "get_last_sync",
    "get_current_sync_summary",
    "get_sync_history",
    "get_market_analytics",
]
