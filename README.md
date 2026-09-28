# Cafe-sitios ☕

Plataforma de comparación y agregación de precios de café de especialidad en Chile.

## Arquitectura
- **Scraper Pipeline**: Ingesta masiva y normalización de precios/formatos ($/kg) desde tiendas Shopify.
- **Base de Datos**: PostgreSQL con SQLAlchemy ORM, driver `psycopg3` e historial temporal de precios.
- **Backend API**: FastAPI bajo Domain-Driven Design (DDD) y Nivel 2 de Madurez de Richardson.

## Estructura del Proyecto
```
cafe-sitios/
├── .env
├── requirements.txt
├── application.py          # Script principal de escaneo e ingesta
├── main.py                 # Servidor de FastAPI
├── db/                     # Configuración y modelos SQLAlchemy
├── scrapper/               # Drivers de extracción (Shopify, etc.)
├── domain/                 # Entidades e Interfaces de Dominio (DDD)
├── infrastructure/         # Implementación de repositorios SQLAlchemy
├── application/            # Casos de uso de la aplicación
└── api/                    # Endpoints FastAPI y Schemas Pydantic
```

## Ejecución
1. Instalar dependencias: `pip install -r requirements.txt`
2. Ejecutar el scraper: `python application.py`
3. Iniciar la API: `python -m uvicorn main:app --reload`
4. Ejecutar test: `python -m unittest discover tests`

## Links de interes
- Documentación Interactiva (Swagger UI): http://localhost:8000/docs
- Documentación ReDoc: http://localhost:8000/redoc
- Healthcheck: http://localhost:8000/
- Endpoint de Productos más Baratos: http://localhost:8000/api/v1/products/cheapest?sort_by=kilo
