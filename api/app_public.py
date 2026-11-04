from contextlib import asynccontextmanager
import logging
import os
import re
from typing import List, Optional
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from api.admin_tienda import router as admin_tienda_router
from api.feedback import router as feedback_router, sugerencias_router
from api.orders import pedidos_router, router as orders_router
from api.products import ofertas_router, productos_router, router as products_router
from api.recipes import router as recipes_router
from api.stores import router as stores_router, tiendas_router
from api.sync import (
    analitica_router,
    analitica_v1_router,
    router as sync_router,
    sincronizacion_router,
    sincronizaciones_router,
    sincronizaciones_v1_router,
)
from api.telemetry import router as telemetry_router, telemetria_router
from db.database import DatabaseManager


def _get_production_flag() -> bool:
    is_render = os.getenv("RENDER", "").strip().lower() == "true"
    return (
        is_render
        or os.getenv("ENVIRONMENT", "").strip().lower() in ("production", "prod", "produccion", "producción")
        or os.getenv("ENV", "").strip().lower() in ("production", "prod", "produccion", "producción")
        or os.getenv("APP_ENV", "").strip().lower() in ("production", "prod", "produccion", "producción")
    )


@asynccontextmanager
async def public_app_lifespan(app: FastAPI):
    skip_migrations = os.getenv("SKIP_DB_MIGRATIONS", "").strip().lower() in ("true", "1", "yes")
    if not skip_migrations:
        try:
            db = DatabaseManager()
            db.inicializar_db()
        except Exception as exc:
            logging.warning(f"No se pudo sincronizar el esquema de base de datos al iniciar la API Pública: {exc}")
    else:
        logging.info("⏩ Omitiendo chequeo de migraciones DDL al iniciar la API Pública (SKIP_DB_MIGRATIONS activo).")
    yield


def create_public_app() -> FastAPI:
    """Crea y configura la instancia de FastAPI para el Sitio Público y Portal de Administración de Tiendas (Parte 1).

    Esta aplicación expone el catálogo público, comparador de precios, recetas, feedback, pedidos WhatsApp,
    telemetría, y el portal multi-tenant para los encargados de las tostadurías (/api/v1/admin-tienda).
    Excluye estrictamente las rutas superadmin de la plataforma (/api/v1/administracion).
    """
    is_production = _get_production_flag()
    enable_docs_env = os.getenv("ENABLE_DOCS")
    enable_docs = enable_docs_env.strip().lower() in ("true", "1", "yes") if enable_docs_env is not None else not is_production

    app = FastAPI(
        title="Cafe-sitios Public & Store Admin API",
        description="API RESTful para el sitio público de Café-sitios y el portal de administración de tostadurías por parte del encargado.",
        version="1.0.0",
        docs_url="/docs" if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
        openapi_url="/openapi.json" if enable_docs else None,
        lifespan=public_app_lifespan,
    )

    # Configuración de CORS
    raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
    local_origins: List[str] = [
        "http://localhost:4321",
        "http://127.0.0.1:4321",
        "http://admin.localhost:4321",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://admin.localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://admin.cafesitios.cl",
        "https://admin.cafesitios.vercel.app",
    ]
    official_origins: List[str] = [
        "https://cafesitios.cl",
        "https://www.cafesitios.cl",
        "https://admin.cafesitios.cl",
        "https://admin.cafesitios.vercel.app",
    ]

    if raw_origins:
        configured_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        allow_origins = list(dict.fromkeys(official_origins + configured_origins)) if is_production else configured_origins
    elif is_production:
        allow_origins = list(official_origins)
    else:
        allow_origins = list(local_origins)

    if is_production:
        allow_origin_regex: Optional[str] = r"^https://([a-zA-Z0-9-]+\.)*(cafesitios\.cl|vercel\.app)(:\d+)?$"
    else:
        allow_origin_regex = (
            r"^https?://([a-zA-Z0-9-]+\.)?(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$" if not raw_origins else None
        )

    proxy_secret = os.getenv("PROXY_SECRET", "").strip()

    @app.middleware("http")
    async def verify_proxy_origin(request: Request, call_next):
        if (
            request.method == "OPTIONS"
            or request.url.path == "/"
            or request.url.path.startswith("/static")
            or not is_production
        ):
            return await call_next(request)

        incoming_secret = request.headers.get("x-proxy-secret", "").strip() if proxy_secret else ""
        has_valid_secret = bool(proxy_secret and incoming_secret == proxy_secret)

        vercel_id = request.headers.get("x-vercel-id")
        forwarded_host = request.headers.get("x-forwarded-host", "")
        origin = request.headers.get("origin", "")
        referer = request.headers.get("referer", "")

        is_from_vercel = bool(vercel_id) or ("vercel.app" in forwarded_host)

        allowed_origin_match = False
        if allow_origins:
            allowed_origin_match = any(
                (origin and origin.startswith(allowed.rstrip("/")))
                or (referer and referer.startswith(allowed.rstrip("/")))
                or (forwarded_host and forwarded_host == allowed.split("://")[-1].rstrip("/"))
                for allowed in allow_origins
            )

        if not allowed_origin_match and allow_origin_regex:
            allowed_origin_match = bool(origin and re.match(allow_origin_regex, origin)) or bool(
                referer and re.match(allow_origin_regex, referer)
            )

        if has_valid_secret or is_from_vercel or allowed_origin_match:
            return await call_next(request)

        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": "Acceso directo a la API no permitido. Las solicitudes deben originarse a través del frontend oficial."
            },
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Inclusión de routers del Sitio Público y Portal de Tiendas
    app.include_router(productos_router)
    app.include_router(products_router)
    app.include_router(ofertas_router)
    app.include_router(tiendas_router)
    app.include_router(stores_router)
    app.include_router(sincronizacion_router)
    app.include_router(sync_router)
    app.include_router(sincronizaciones_router)
    app.include_router(sincronizaciones_v1_router)
    app.include_router(analitica_router)
    app.include_router(analitica_v1_router)
    app.include_router(recipes_router)
    app.include_router(sugerencias_router)
    app.include_router(feedback_router)
    app.include_router(telemetria_router)
    app.include_router(telemetry_router)
    app.include_router(admin_tienda_router)
    app.include_router(pedidos_router)
    app.include_router(orders_router)

    # Subida de imágenes de productos para encargados de tienda
    os.makedirs(os.path.join("static", "uploads", "productos"), exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/", tags=["Healthcheck"])
    def healthcheck():
        return {"status": "ok", "service": "Cafe-sitios API"}

    return app
