from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.router import router as products_router, stores_router

app = FastAPI(
    title="Cafe-sitios API",
    description="API RESTful para la comparación de precios de cafés de especialidad en Chile.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router)
app.include_router(stores_router)

@app.get("/", tags=["Healthcheck"])
def healthcheck():
    return {"status": "ok", "service": "Cafe-sitios API"}
