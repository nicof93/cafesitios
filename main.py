from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.admin import administracion_router, router as admin_router
from api.admin_tienda import router as admin_tienda_router
from api.dependencies import is_localhost_request
from api.products import ofertas_router, productos_router, router as products_router
from api.stores import router as stores_router, tiendas_router
from api.sync import (
    analitica_router,
    analitica_v1_router,
    router as sync_router,
    sincronizacion_router,
    sincronizaciones_router,
    sincronizaciones_v1_router,
)
from api.recipes import router as recipes_router
from api.feedback import router as feedback_router, sugerencias_router
from api.telemetry import router as telemetry_router, telemetria_router
from api.orders import pedidos_router, router as orders_router
from db.database import DatabaseManager

# Configuración de documentación OpenAPI según ambiente
is_render = os.getenv("RENDER", "").strip().lower() == "true"
is_production = (
    is_render
    or os.getenv("ENVIRONMENT", "").strip().lower() in ("production", "prod", "produccion", "producción")
    or os.getenv("ENV", "").strip().lower() in ("production", "prod", "produccion", "producción")
    or os.getenv("APP_ENV", "").strip().lower() in ("production", "prod", "produccion", "producción")
)
enable_docs_env = os.getenv("ENABLE_DOCS")

if enable_docs_env is not None:
    enable_docs = enable_docs_env.strip().lower() in ("true", "1", "yes")
else:
    enable_docs = not is_production

docs_url = "/docs" if enable_docs else None
redoc_url = "/redoc" if enable_docs else None
openapi_url = "/openapi.json" if enable_docs else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    skip_migrations = os.getenv("SKIP_DB_MIGRATIONS", "").strip().lower() in ("true", "1", "yes")
    if not skip_migrations:
        try:
            db = DatabaseManager()
            db.inicializar_db()
        except Exception as exc:
            logging.warning(f"No se pudo sincronizar el esquema de base de datos al iniciar la API: {exc}")
    else:
        logging.info("⏩ Omitiendo chequeo de migraciones DDL al iniciar la API (SKIP_DB_MIGRATIONS activo).")
    yield


app = FastAPI(
    title="Cafe-sitios API",
    description="API RESTful para la comparación de precios de cafés de especialidad en Chile.",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
    lifespan=lifespan,
)

# Configuración de CORS basada en variables de entorno (ALLOWED_ORIGINS) y puertos locales estándar
raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
local_origins = [
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

official_origins = [
    "https://cafesitios.cl",
    "https://www.cafesitios.cl",
    "https://admin.cafesitios.cl",
    "https://admin.cafesitios.vercel.app",
]

if raw_origins:
    configured_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    if is_production:
        allow_origins = list(dict.fromkeys(official_origins + configured_origins))
    else:
        allow_origins = configured_origins
elif is_production:
    allow_origins = list(official_origins)
else:
    allow_origins = list(local_origins)

# Regex para soportar localhost en desarrollo (cuando no hay ALLOWED_ORIGINS fijado) y subdominios oficiales/vercel en producción
if is_production:
    allow_origin_regex = r"^https://([a-zA-Z0-9-]+\.)*(cafesitios\.cl|vercel\.app)(:\d+)?$"
else:
    allow_origin_regex = (
        r"^https?://([a-zA-Z0-9-]+\.)?(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$" if not raw_origins else None
    )

proxy_secret = os.getenv("PROXY_SECRET", "").strip()


@app.middleware("http")
async def verify_proxy_origin(request: Request, call_next):
    # En desarrollo local, peticiones preflight CORS (OPTIONS) o rutas healthcheck (/), permitir libremente
    if (
        request.method == "OPTIONS"
        or request.url.path == "/"
        or not is_production
    ):
        return await call_next(request)

    # 1. Si se configuró PROXY_SECRET y se recibe cabecera con secreto válido
    incoming_secret = request.headers.get("x-proxy-secret", "").strip() if proxy_secret else ""
    has_valid_secret = bool(proxy_secret and incoming_secret == proxy_secret)

    # 2. Detección de peticiones a través del proxy de Vercel o de dominios autorizados
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
        import re
        allowed_origin_match = bool(origin and re.match(allow_origin_regex, origin)) or bool(referer and re.match(allow_origin_regex, referer))

    if has_valid_secret or is_from_vercel or allowed_origin_match:
        return await call_next(request)

    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "detail": "Acceso directo a la API no permitido. Las solicitudes deben originarse a través del frontend oficial."
        }
    )


# CORSMiddleware se agrega al final para ser la capa más externa (outermost middleware)
# envolviendo todas las respuestas y garantizando cabeceras Access-Control-Allow-Origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers canónicos en español y alias en inglés
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
app.include_router(administracion_router)
app.include_router(admin_router)
app.include_router(admin_tienda_router)
app.include_router(pedidos_router)
app.include_router(orders_router)


@app.get("/", tags=["Healthcheck"])
def healthcheck():
    return {"status": "ok", "service": "Cafe-sitios API"}
