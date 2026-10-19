# Café-sitios ☕🇨🇱

Plataforma de comparación, agregación de precios y directorio de café de especialidad en Chile.

Café-sitios centraliza en tiempo real los catálogos de tostadores y tiendas de café en Chile, permitiendo a los amantes del café filtrar por origen, proceso, notas de cata y comparar precios estandarizados por kilo ($/kg), registrar extracciones en la bitácora del barista y acceder a paneles de gestión para tostadurías.

---

## 🏛️ Arquitectura del Sistema

El proyecto sigue una arquitectura desacoplada basada en **Domain-Driven Design (DDD)** simplificado y principios *Twelve-Factor App*:

* **Pipeline ETL / Scraper Asíncrono (`scrapper/`, `core/`):** Ingesta masiva desde tiendas Shopify (JSON endpoints) y WooCommerce (Store API + HTML fallback). Normaliza gramajes, precios CLP, calcula precio por kilo ($/kg) y extrae atributos botánicos estructurados (variedad, origen, finca, proceso, fermentación y notas de cata SCA).
* **Base de Datos & Performance (`db/`, `migrations/`):** PostgreSQL (Supabase en producción) con SQLAlchemy 2.0 y Alembic. Optimizado con índices en Foreign Keys, índices compuestos de ordenación, aceleración GIN con `pg_trgm` para búsqueda textual y vistas materializadas concurrentes para métricas y variaciones de precio.
* **Backend REST API (`api/`, `main.py`):** Desarrollado con FastAPI, tipado estricto con Pydantic v2, autenticación y panel multi-tenant (RBAC) para tostadurías con registro de auditoría.
* **Frontend Web (`astro-frontend/`):** Aplicación de alto rendimiento construida en Astro (SSR/SSG) con Tailwind CSS, islas reactivas, optimización estricta de Core Web Vitals (LCP < 1.2s), SEO semántico y datos estructurados Schema.org.
* **CI/CD Automatizado (`.github/workflows/`):** Desacoplamiento de migraciones de base de datos en merge a `main` y ejecución programada del scraper nocturno (03:00 AM UTC).

---

## 📁 Estructura del Repositorio

```text
cafe-sitios/
├── .github/workflows/          # Automatizaciones CI/CD
│   ├── database-migrations.yml # Migraciones automáticas de BD al hacer merge a main
│   └── scraper.yml             # Scraper nocturno programado (03:00 AM UTC)
├── api/                        # Capa HTTP (FastAPI)
│   ├── router.py               # Orquestador de rutas públicas (/api/v1/...)
│   ├── products.py             # Catálogo público, filtros y comparador
│   ├── stores.py               # Directorio de tiendas y sucursales
│   ├── admin_tienda.py         # Panel multi-inquilino para tostadurías (RBAC)
│   └── schemas.py              # DTOs de entrada y salida Pydantic v2
├── application/                # Casos de uso de negocio (orquestación)
│   ├── get_cheapest_products.py
│   ├── compare_products.py
│   └── get_weekly_price_drops.py
├── domain/                     # Entidades puras y contratos (CERO dependencias externas)
│   ├── models.py               # Dataclasses del dominio
│   ├── repositories.py         # Interfaces abstractas (ProductRepository)
│   └── search_normalizer.py    # Sinónimos botánicos y clasificador de categorías
├── infrastructure/             # Adaptadores E/S y persistencia
│   └── postgres_repository.py  # Implementación SQLAlchemy 2.0 de repositorios
├── db/                         # Conexión, configuración y modelos ORM
│   ├── config.py               # Carga de variables de entorno (.env)
│   └── database.py             # Modelos declarativos y DatabaseManager
├── migrations/versions/        # Historial de migraciones con Alembic (0001 a 0015)
├── scrapper/                   # Drivers de extracción (Shopify JSON, WooCommerce API)
├── core/                       # Normalizadores y extractores de metadatos botánicos (SCA)
├── astro-frontend/             # Frontend moderno en Astro + Tailwind CSS
├── tests/                      # Suite de pruebas unitarias (módulo nativo unittest)
├── scrapper_application.py     # Entrypoint del pipeline ETL / Sincronización
├── main.py                     # Entrypoint de la API FastAPI
└── AGENTS.md                   # Protocolo técnico y directivas de desarrollo para IA
```

---

## 🚀 Puesta en Marcha Local

### 1. Requisitos Previos
* Python 3.11+
* Node.js 18+ (para el frontend Astro)
* Base de datos PostgreSQL (local o instancia de Supabase)

### 2. Instalación de Dependencias
```powershell
# Clonar el repositorio
git clone https://github.com/tu-usuario/cafe-sitios.git
cd cafe-sitios

# Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\activate       # En Windows
# source venv/bin/activate    # En Linux/macOS

# Instalar dependencias backend
pip install -r requirements.txt
```

### 3. Configuración del Entorno (`.env`)
Crea un archivo `.env` en la raíz del proyecto basado en las siguientes variables:
```env
DATABASE_URL=postgresql+psycopg://postgres:tu_password@tu_host:5432/postgres
ENVIRONMENT=development
ENABLE_DOCS=true
```

### 4. Migraciones de Base de Datos
```powershell
python -m alembic upgrade head
```

### 5. Ejecución del Scraper
```powershell
# Modo normal (verifica e inicializa BD si hace falta):
python scrapper_application.py

# Modo ultra-rápido (omite verificación DDL si ya ejecutaste migraciones):
python scrapper_application.py --skip-migrations
```

### 6. Iniciar la API FastAPI
```powershell
python -m uvicorn main:app --reload --port 8000
```
La documentación interactiva estará disponible en:
* Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
* ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 7. Iniciar el Frontend (Astro)
```powershell
cd astro-frontend
npm install
npm run dev
```
El frontend estará corriendo en [http://localhost:4321](http://localhost:4321).

---

## 🧪 Pruebas Automatizadas

Siguiendo el protocolo de calidad definido en `AGENTS.md`, las pruebas se ejecutan de manera focalizada con el módulo nativo `unittest`:

```powershell
# Pruebas de base de datos y migraciones
python -m unittest tests/test_database.py

# Pruebas de endpoints API y contratos HTTP
python -m unittest tests/test_api.py

# Pruebas de seguridad multi-tenant y roles de tienda
python -m unittest tests/test_store_admin_multi_tenant.py

# Pruebas de caídas de precio y ofertas
python -m unittest tests/test_weekly_price_drops.py

# Pruebas de drivers de scraping
python -m unittest tests/test_woocommerce_driver.py
python -m unittest tests/test_driver.py
```

---

## ⚙️ Despliegue en Producción

### Frontend (Vercel)
1. Importa el repositorio en Vercel.
2. Configura `astro-frontend` como **Root Directory**.
3. Framework Preset: **Astro**.
4. Variables de Entorno en Vercel:
   - `PUBLIC_SITE_URL`: `https://cafesitios.cl`
   - `PUBLIC_API_URL`: URL pública de tu API FastAPI (sin `/api/v1` al final).

### Backend (Render / Railway / Koyeb)
- Comando de inicio: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Variable de entorno recomendada: `SKIP_DB_MIGRATIONS=true` (las migraciones se aplican automáticamente vía GitHub Actions al hacer merge).

### CI/CD en GitHub Actions
Configura el secreto en tu repositorio de GitHub (`Settings -> Secrets and variables -> Actions`):
* `DATABASE_URL`: Cadena de conexión completa a tu base de datos de producción con driver psycopg3 (ej. `postgresql+psycopg://postgres.xxx:pass@aws-0-sa-east-1.pooler.supabase.com:6543/postgres`).

---

## 🚩 Estrategia de Feature Flags (Lanzamiento Controlado)

Cafesitios utiliza un sistema desacoplado de Feature Flags para controlar el despliegue progresivo de funcionalidades tanto en el **Frontend (Astro)** como en el **Backend (FastAPI)**.

Permite activar o desactivar páginas completas, enlaces en menús de navegación, botones de acción y rastreo en `sitemap.xml` para SEO sin necesidad de eliminar código.

### Variables de Configuración

| Variable de Entorno | Ámbito | Valor por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `PUBLIC_ENABLE_RECIPES` | Frontend | `true` | Habilita o deshabilita la página `/recetas` (Guías Baristas) y sus enlaces en el header. Si está inactiva, retorna `404` limpio y se omite en el `sitemap.xml`. |
| `ENABLE_RECIPES` | Backend | `true` | Habilita o restringe los endpoints de guardado y sincronización de recetas `/api/v1/recetas`. Si está inactivo, responde `404 Not Found`. |
| `PUBLIC_ENABLE_CALIBRATOR` | Frontend | `true` | Habilita o deshabilita el Calibrador Sensorial 2D `/calibrador`, su acceso en el Header y el banner destacado en Guías. Si está inactivo, retorna `404` y se excluye del sitemap. |
| `ENABLE_CALIBRATOR` | Backend | `true` | Flag en configuración del backend para control de dependencias asociadas al calibrador. |
| `PUBLIC_ENABLE_MY_RECIPES` | Frontend | `true` | Controla la visualización del portal "Mis Recetas" local-first en el menú de navegación y sitemap. |
| `PUBLIC_ENABLE_FLAVOR_QUIZ` | Frontend | `true` | Controla la visualización del botón interactivo "Quiz de Sabor" en la navegación y hero principal. |

### Cómo activar o pausar un módulo:
* **En desarrollo local:** Edita el archivo `astro-frontend/.env` o la raíz `.env`. Por ejemplo, para ocultar el calibrador antes del lanzamiento oficial:
  ```env
  PUBLIC_ENABLE_CALIBRATOR=false
  ```
* **En producción (Vercel / Render):**
  Agrega o modifica la variable en el panel del servicio (`Settings -> Environment Variables`) y realiza un redespliegue sin reconstruir la base de código.

---

## 📌 Endpoints Principales de la API

La API cuenta con endpoints canónicos en español y alias transparentes en inglés para garantizar total retrocompatibilidad:

| Método | Endpoint Canónico (ES) | Alias Retrocompatible (EN) | Descripción |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | `/` | Healthcheck de la API. |
| `GET` | `/api/v1/productos` | `/api/v1/products` (`/cheapest`) | Catálogo paginado con filtros de origen, proceso, variedad, rango de precio, notas y ordenamiento por `$/kg`. |
| `GET` | `/api/v1/productos/comparar` | `/api/v1/products/compare` | Comparador side-by-side de hasta 4 cafés (atributos técnicos y organolépticos). |
| `GET` | `/api/v1/productos/recomendar` | `/api/v1/products/recommend` | Recomendador interactivo / Quiz de afinidad por método de preparación y perfil. |
| `GET` | `/api/v1/productos/{id}/detalle` | `/api/v1/products/{id}/detail` | Ficha técnica completa, variantes e historial temporal de precios. |
| `GET` | `/api/v1/productos/ofertas-semana` | `/api/v1/products/ofertas-semana` | Mayores rebajas de precio verificadas en los últimos 7 días. |
| `GET` | `/api/v1/tiendas` | `/api/v1/stores` | Directorio paginado de tostadurías activas y sucursales con cercanía geográfica. |
| `GET` | `/api/v1/sincronizacion/ultima` | `/api/v1/sync/last` | Marca temporal y estado de la última sincronización del scraper. |
| `GET` | `/api/v1/sincronizacion/resumen` | `/api/v1/sync/summary` | Resumen de novedades, productos agregados y variaciones de precio. |
| `GET` | `/api/v1/sincronizacion/mercado` | `/api/v1/sync/market` | Estadísticas agregadas del mercado de café (precios promedio, distribución de tueste y procesos). |
| `POST` | `/api/v1/sugerencias` | `/api/v1/feedback` | Envío anónimo y seguro de sugerencias con rate limiting y honeypot anti-bot. |
| `POST` | `/api/v1/telemetria/evento` | `/api/v1/telemetry/event` | Registro anónimo de clics hacia tiendas externas e interacciones. |
| `GET` | `/api/v1/recetas` | — | Guías y recetas interactivas de barismo según método de extracción. |
| `POST` | `/api/v1/admin-tienda/login` | — | Autenticación multi-tenant (RBAC) para tostadurías asociadas. |
| `GET/POST`| `/api/v1/admin-tienda/productos` | — | Gestión del catálogo de la tostaduría autenticada. |
| `GET` | `/api/v1/administracion/tiendas` | `/api/v1/admin/stores` | Administración local de tostadurías, sincronización manual y moderación. |
