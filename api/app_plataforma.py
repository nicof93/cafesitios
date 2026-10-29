from contextlib import asynccontextmanager
import logging
import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.admin import administracion_router, router as admin_router
from api.sync import (
    analitica_router,
    analitica_v1_router,
    router as sync_router,
    sincronizacion_router,
    sincronizaciones_router,
    sincronizaciones_v1_router,
)
from db.database import DatabaseManager


@asynccontextmanager
async def plataforma_app_lifespan(app: FastAPI):
    skip_migrations = os.getenv("SKIP_DB_MIGRATIONS", "").strip().lower() in ("true", "1", "yes")
    if not skip_migrations:
        try:
            db = DatabaseManager()
            db.inicializar_db()
        except Exception as exc:
            logging.warning(f"No se pudo sincronizar el esquema de base de datos al iniciar la API de Plataforma: {exc}")
    else:
        logging.info("⏩ Omitiendo chequeo de migraciones DDL al iniciar la API de Plataforma (SKIP_DB_MIGRATIONS activo).")
    yield


def create_plataforma_app() -> FastAPI:
    """Crea y configura la instancia de FastAPI para la Plataforma de Administración (Superadmin - Parte 2).

    Esta aplicación está aislada para el uso exclusivo de la consola de administración interna (plataforma-admin en :4322).
    Contiene la gestión global de tiendas, sucursales, borrado en cascada, auditoría global, ambientes,
    ejecución y pruebas de drivers, cuotas de almacenamiento y métricas de tracción.
    """
    app = FastAPI(
        title="Cafe-sitios Plataforma Superadmin API",
        description="API dedicada exclusivamente para la Plataforma de Administración y Bitácora Barista (Superadmin).",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=plataforma_app_lifespan,
    )

    # Orígenes autorizados para la plataforma local de administración
    plataforma_origins: List[str] = [
        "http://localhost:4322",
        "http://127.0.0.1:4322",
        "http://localhost:4321",
        "http://127.0.0.1:4321",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ]

    custom_origins = os.getenv("PLATAFORMA_ALLOWED_ORIGINS", "").strip()
    if custom_origins:
        plataforma_origins.extend([o.strip() for o in custom_origins.split(",") if o.strip()])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=plataforma_origins,
        allow_origin_regex=r"^https?://([a-zA-Z0-9-]+\.)?(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers exclusivos de superadministración
    app.include_router(administracion_router)
    app.include_router(admin_router)

    # Routers de soporte para analítica y métricas de sincronización requeridas en la bitácora
    app.include_router(sincronizacion_router)
    app.include_router(sync_router)
    app.include_router(sincronizaciones_router)
    app.include_router(sincronizaciones_v1_router)
    app.include_router(analitica_router)
    app.include_router(analitica_v1_router)

    @app.get("/", tags=["Healthcheck"])
    def healthcheck():
        return {"status": "ok", "service": "Cafe-sitios Plataforma Superadmin API"}

    return app
