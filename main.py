import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.include_router(products_router)
app.include_router(stores_router)
app.include_router(sync_router)


@app.get("/", tags=["Healthcheck"])
def healthcheck():
    return {"status": "ok", "service": "Cafe-sitios API"}
