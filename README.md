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
2. Aplicar migraciones: `alembic upgrade head`
3. Ejecutar el scraper: `python scrapper_application.py`
4. Iniciar la API: `python -m uvicorn main:app --reload`
5. Ejecutar test: `python -m unittest discover tests`

### Versionado de base de datos

El esquema se versiona con Alembic. Las bases existentes que fueron creadas antes de Alembic deben marcar el baseline una sola vez y luego aplicar las nuevas revisiones:

```bash
alembic stamp 0001_baseline
alembic upgrade head
```

En una base vacía basta con ejecutar `alembic upgrade head`. Cada fila de `sincronizaciones` representa una ejecución por tienda y almacena fechas, resultado, detalle de error y conteos de productos agregados, eliminados y actualizados.

Tiendas, productos y variantes registran `fecha_creacion` y `fecha_actualizacion`; la fecha de creación se conserva en las sincronizaciones posteriores y la de actualización cambia cuando se modifica el registro. Los productos conservan además su `id_externo` de la tienda (ID de plataforma o SKU disponible), separado del ID interno de la base de datos, para reconocerlos aunque cambie su URL.

## Links de interes
- Documentación Interactiva (Swagger UI): http://localhost:8000/docs
- Documentación ReDoc: http://localhost:8000/redoc
- Healthcheck: http://localhost:8000/
- Endpoint de Productos más Baratos: http://localhost:8000/api/v1/products/cheapest?sort_by=kilo
