import os
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.products import router as products_router
from api.stores import router as stores_router
from api.sync import router as sync_router

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

app = FastAPI(
    title="Cafe-sitios API",
    description="API RESTful para la comparación de precios de cafés de especialidad en Chile.",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

# Configuración de CORS basada en variables de entorno (ALLOWED_ORIGINS)
raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
if raw_origins:
    allow_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
elif is_production:
    # En producción publicada sin orígenes configurados, no permitir orígenes locales
    allow_origins = []
else:
    # Entorno local de desarrollo
    allow_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

proxy_secret = os.getenv("PROXY_SECRET", "").strip()


@app.middleware("http")
async def verify_proxy_origin(request: Request, call_next):
    # En desarrollo local o rutas esenciales de healthcheck (/), permitir libremente
    if request.url.path == "/" or not is_production:
        return await call_next(request)

    # 1. Si se configuró PROXY_SECRET, validar la firma
    if proxy_secret:
        incoming_secret = request.headers.get("x-proxy-secret", "").strip()
        if incoming_secret == proxy_secret:
            return await call_next(request)
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Acceso no autorizado. Firma de proxy inválida."}
        )

    # 2. Detección de peticiones a través del proxy de Vercel o de dominios autorizados
    vercel_id = request.headers.get("x-vercel-id")
    forwarded_host = request.headers.get("x-forwarded-host", "")
    origin = request.headers.get("origin", "")

    is_from_vercel = bool(vercel_id) or ("vercel.app" in forwarded_host)

    allowed_origin_match = False
    if allow_origins:
        allowed_origin_match = any(
            origin.startswith(allowed.rstrip("/")) or forwarded_host == allowed.split("://")[-1].rstrip("/")
            for allowed in allow_origins
        )

    if is_from_vercel or allowed_origin_match:
        return await call_next(request)

    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "detail": "Acceso directo a la API no permitido. Las solicitudes deben originarse a través del frontend oficial."
        }
    )

app.include_router(products_router)
app.include_router(stores_router)
app.include_router(sync_router)


@app.get("/", tags=["Healthcheck"])
def healthcheck():
    return {"status": "ok", "service": "Cafe-sitios API"}
