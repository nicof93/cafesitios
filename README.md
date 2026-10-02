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
├── index.html              # Catálogo y acceso a fichas de producto
├── stores.html             # Listado de tiendas
├── product.html            # Detalle de producto e historial de precios
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

El esquema se versiona con Alembic. Al iniciar el scraper, una base heredada sin `alembic_version` se adopta automáticamente si contiene las tablas principales del esquema anterior; si falta la tabla auxiliar `estado_sincronizacion`, se crea antes de registrar el baseline. Luego se aplican las revisiones pendientes. Las bases vacías reciben todas las migraciones. Si se ejecutan migraciones manualmente sobre una base heredada, primero se debe marcar el baseline:

```bash
alembic stamp 0001_baseline
alembic upgrade head
```

En una base vacía basta con ejecutar `alembic upgrade head`. Cada fila de `sincronizaciones` representa una ejecución por tienda y almacena fechas, resultado, detalle de error y conteos de productos agregados, eliminados y actualizados.

Tiendas, productos y variantes registran `fecha_creacion` y `fecha_actualizacion`; la fecha de creación se conserva en las sincronizaciones posteriores y la de actualización cambia cuando se modifica el registro. Los productos conservan además su `id_externo` de la tienda (ID de plataforma o SKU disponible), separado del ID interno de la base de datos, para reconocerlos aunque cambie su URL.

El detalle abre una página propia (`product.html?id=<id>`), donde se muestra la descripción HTML saneada que publica la tienda, las variantes y un gráfico Chart.js con la evolución diaria del precio por variante. El endpoint `/api/v1/products/{id}/detail` devuelve el historial para cada variante.

El scraper consulta las tiendas con `activo = true` en la base de datos y usa sus campos `plataforma` y `url_base`; no crea ni actualiza registros de tienda durante la sincronización. Si una tienda heredada aún tiene `plataforma = 'desconocida'`, prueba los drivers soportados con su `url_base` sin modificar la tienda. Para desactivar o reactivar una tienda comercialmente, cambie su campo `activo`:

```sql
UPDATE tiendas SET activo = FALSE WHERE id = 1;
UPDATE tiendas SET activo = TRUE WHERE id = 1;
```

Los productos que desaparecen de una tienda también se conservan: pasan a `activo = false`, junto con sus variantes e historial, y se reactivan si vuelven a aparecer.

## Links de interes
- Documentación Interactiva (Swagger UI): http://localhost:8000/docs
- Documentación ReDoc: http://localhost:8000/redoc
- Healthcheck: http://localhost:8000/
- Endpoint de Productos más Baratos: http://localhost:8000/api/v1/products/cheapest?sort_by=kilo
- Listado paginado de tiendas: http://localhost:8000/api/v1/stores?page=1&page_size=10&sort_by=product_count_desc
- Detalle de producto y variantes: http://localhost:8000/api/v1/products/1/detail
- Última sincronización: http://localhost:8000/api/v1/sync/last
