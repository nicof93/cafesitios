# AGENTS.md - Protocolo de Eficiencia, Calidad y Contexto para Agentes de IA

Este documento establece los contratos de datos, la arquitectura, los estándares de ingeniería de software de clase mundial y las directivas de ejecución para **Café-sitios**. Todo agente o desarrollador que opere en este repositorio debe cumplir estas directivas para garantizar **máxima autonomía, velocidad de respuesta (< 50 ms), escalabilidad, seguridad multi-tenant y optimización de tokens**.

---

## 1. Estrategia de Ahorro de Créditos y Optimización de Flujo (CRÍTICO)

Para evitar consumo desmedido de ventana de contexto y llamadas de herramientas innecesarias:

1. **Aislamiento de Tareas (Edición Quirúrgica):**
   * Modifica **únicamente** los archivos directamente involucrados en la solicitud.
   * NO leas todo el proyecto para resolver un problema puntual. Usa la estructura del mapa para ir directo al archivo.
2. **Ejecución de Pruebas Focalizadas:**
   * **NUNCA** ejecutes la suite completa de pruebas (`discover`) salvo que el usuario lo pida o sea un cambio estructural global.
   * Corre exclusivamente la prueba unitaria del módulo afectado (ej. `python -m unittest tests/test_woocommerce_driver.py`).
3. **Procesamiento Muestral en Scraping:**
   * Al depurar o crear drivers de scraping, **NO cargues respuestas JSON o HTML completas en el chat**. Trabaja con fragmentos de muestra o mocks locales en `tests/`.
4. **Respeto Estricto de Librerías (`requirements.txt`):**
   * NO intentes instalar ni sugerir paquetes adicionales (como `pytest`, `httpx`, `pydantic-settings`). Usa únicamente la pila existente.
5. **No tocar `README.md` innecesariamente:**
   * Modifica `README.md` únicamente si la tarea cambia explícitamente la instalación, configuración, variables de entorno o comandos de ejecución principales.

---

## 2. Visión General y Stack Tecnológico Fijo

* **Proyecto:** Agregador y comparador de precios de café de especialidad en Chile.
* **Lenguaje:** Python 3.11+ con **Type Hints estrictos** (obligatorios en firmas de funciones/métodos y modelos de datos).
* **Dependencias Fijas (`requirements.txt`):**
  * `fastapi >= 0.100.0` | `uvicorn >= 0.22.0`
  * `sqlalchemy >= 2.0.0` (Sintaxis 2.0 moderna con `select()`, prohibido usar el legacy `.query()`)
  * `alembic >= 1.13.0`
  * `psycopg[binary] >= 3.1.0` (Driver Psycopg 3 para PostgreSQL)
  * `pydantic >= 2.0.0` (Sintaxis Pydantic v2: `ConfigDict`, `from_attributes`, `Field`)
  * `requests >= 2.31.0` | `python-dotenv >= 1.0.0`
* **Testing:** Módulo nativo `unittest`.

---

## 3. Mapa de Arquitectura (DDD Simplificado)

```text
cafe-sitios/
├── domain/                  # Entidades puras y Contratos (CERO dependencias externas)
│   ├── models.py            # Dataclasses: CoffeeProduct, Variant, Store
│   ├── repositories.py      # Interfaces/ABCs: ProductRepository
│   └── search_normalizer.py # Normalización de sinónimos, clasificación y reglas de texto
├── application/             # Casos de Uso (Orquestación sin detalles de infraestructura)
│   ├── get_cheapest_products.py
│   ├── compare_products.py
│   └── get_weekly_price_drops.py
├── infrastructure/          # Adaptadores E/S y Persistencia
│   └── postgres_repository.py # Implementación SQLAlchemy 2.0 de ProductRepository
├── api/                     # Capa HTTP (FastAPI)
│   ├── router.py            # Orquestador y re-exportador de rutas (ES canónico / EN alias)
│   ├── products.py          # Catálogo (/api/v1/productos, alias /api/v1/products) y comparador
│   ├── stores.py            # Directorio de tiendas y sucursales (/api/v1/tiendas, alias /stores)
│   ├── sync.py              # Métricas y analítica (/api/v1/sincronizacion, alias /sync)
│   ├── recipes.py           # Guías de preparación (/api/v1/recetas)
│   ├── feedback.py          # Sugerencias (/api/v1/sugerencias, alias /feedback)
│   ├── telemetry.py         # Registro anónimo de clics (/api/v1/telemetria, alias /telemetry)
│   ├── admin.py             # Herramientas administrativas (/api/v1/administracion, alias /admin)
│   ├── admin_tienda.py      # Panel multi-inquilino para tostadurías (RBAC / Tenancy)
│   └── schemas.py           # DTOs de entrada y salida Pydantic v2
├── db/                      # Configuración de BD y Modelos ORM
│   ├── config.py            # Carga de variables de entorno (.env)
│   └── database.py          # Tablas SQLAlchemy (DeclarativeBase) y DatabaseManager
├── migrations/versions/     # Migraciones de base de datos con Alembic
├── scrapper/                # Drivers ETL (Shopify JSON / WooCommerce Store API)
├── astro-frontend/          # Frontend Público (SSR / Edge CDN en Vercel) y Portal de Tiendas
├── plataforma-admin/        # Administrador Local Multi-Ambiente y Bitácora Barista (/plataforma en :4322)
├── tests/                   # Pruebas automatizadas con unittest
├── scrapper_application.py  # Entrypoint ETL / Sincronización
└── main.py                  # Entrypoint API FastAPI
```

---

## 4. Comandos Canónicos de Desarrollo

Todos los comandos se ejecutan desde la raíz del proyecto.

1. **Pruebas unitarias puntuales (Usar SIEMPRE preferentemente):**
   ```powershell
   python -m unittest tests/test_database.py
   python -m unittest tests/test_api.py
   python -m unittest tests/test_multi_environment_admin.py
   python -m unittest tests/test_store_admin_multi_tenant.py
   python -m unittest tests/test_weekly_price_drops.py
   ```
2. **Migraciones con Alembic:**
   ```powershell
   python -m alembic revision --autogenerate -m "descripcion"
   python -m alembic upgrade head
   ```
3. **Ejecución local:**
   ```powershell
   python scrapper_application.py          # Correr scraper / sincronización
   python -m uvicorn main:app --reload      # Correr API FastAPI
   cd astro-frontend; npm run dev           # Correr Sitio Público (localhost:4321)
   cd plataforma-admin; npm run dev         # Correr Administrador Local (localhost:4322/plataforma)
   ```

---

## 5. Contratos de Datos y Reglas de Negocio Invariantes

Cualquier nuevo driver, endpoint o caso de uso debe cumplir sin excepción:

1. **Precios (CLP):** `precio_clp` y `precio_original_clp` son enteros (`int`). Si la fuente incluye `minor_unit`, dividir entre $10^{\text{minor\_unit}}$.
2. **Gramos (`formato_gramos`):** Entero (`int`). Patrones admitidos: `250g`, `1kg` ($\to 1000$). Fallback predeterminado = $250$.
3. **Precio por Kilo:** $\text{round}((\text{precio\_clp} / \text{formato\_gramos}) \times 1000, 2)$. Si precio o gramos $\le 0$, retorna $0.0$.
4. **Ofertas:** `en_oferta = True` si y solo si `precio_original_clp > precio_clp`.
5. **Sintaxis Pydantic v2:**
   ```python
   from pydantic import BaseModel, ConfigDict
   class ProductSchema(BaseModel):
       model_config = ConfigDict(from_attributes=True)
   ```
6. **Interfaz de Drivers Scraping:**
   ```python
   class BaseDriver:
       @staticmethod
       def extraer_gramos(texto: Optional[str], default: int = 250) -> int: ...
       @staticmethod
       def calcular_precio_por_kilo(precio_clp: int, formato_gramos: int) -> float: ...
       def consumir_productos(self) -> List[Dict[str, Any]]: ...
   ```

---

## 6. Buenas Prácticas de Base de Datos y Escalabilidad (DBA Protocol)

Todo diseño o modificación del esquema debe cumplir con estándares estrictos de base de datos de producción:

1. **Normalización vs. Desnormalización Controlada:**
   * La base de datos opera bajo **Tercera Forma Normal (3FN)** para integridad relacional (`tiendas`, `productos`, `variantes`, `historial_precios`).
   * Solo se permite desnormalización si existe una justificación documentada de latencia crítica (ej. columna `categoria` en `productos` para evitar $15+$ cláusulas `ILIKE NOT` dinámicas por query).
2. **Reglas de Oro de Indexación:**
   * **Foreign Keys obligatorias:** Toda FK relacional **debe tener un índice explícito** (`idx_productos_tienda_id`, `idx_variantes_producto_id`, `idx_historial_precios_variante_id`).
   * **Índices Compuestos por Selectividad:** Ordenar columnas de izquierda a derecha: primero condiciones de igualdad (`disponible = True`, `activo = True`), luego rangos o criterios de ordenamiento (`precio_por_kilo ASC`).
   * **Búsquedas de Texto en PostgreSQL:** Utilizar índices GIN con `pg_trgm` (`gin_trgm_ops`) para acelerar búsquedas libres y matching parcial sin escaneos secuenciales (`Seq Scan`).
   * **Evitar Sobre-indexación:** No crear índices redundantes en columnas con baja cardinalidad (ej. booleanos aislados) a menos que formen parte de un índice compuesto o filtro parcial cubriente.
3. **Prevención de Problemas N+1:**
   * Prohibido iterar sobre colecciones cargadas de forma perezosa (*lazy loading*).
   * Usar siempre carga anticipada explícita en SQLAlchemy 2.0: `selectinload()` para relaciones uno-a-muchos (`Producto.variantes`) y `joinedload()` para relaciones muchos-a-uno (`Producto.tienda`).
4. **Migraciones Seguras y Compatibilidad Dual (Postgres / SQLite):**
   * Toda migración Alembic debe verificar el dialecto activo:
     ```python
     bind = op.get_bind()
     is_postgres = bind.dialect.name == 'postgresql'
     ```
   * Extensiones de Postgres (`pg_trgm`), índices GIN y vistas materializadas deben condicionarse a `is_postgres = True`, manteniendo una alternativa compatible en SQLite para pruebas unitarias.
   * **Zero-Downtime:** Prohibido eliminar o renombrar columnas en caliente. Aplicar el patrón **Expand and Contract** (crear columna nueva $\to$ escribir en ambas $\to$ migrar lecturas $\to$ deprecar antigua).
5. **Vistas Materializadas con Refresco Concurrente:**
   * Las vistas analíticas o de cálculo pesado (como `mv_variaciones_precio`) deben poseer un índice único (`UNIQUE INDEX`) para permitir `REFRESH MATERIALIZED VIEW CONCURRENTLY` sin bloquear lecturas concurrentes de la API.
   * Ejecutar los refrescos en transacciones separadas con nivel `AUTOCOMMIT`.

---

## 7. Construcción, Seguridad y Exposición de APIs (FastAPI)

1. **Aislamiento Multi-Tenant Estricto (RBAC / Tenancy):**
   * En endpoints administrativos (`/api/v1/admin-tienda/...`), el `tienda_id` **nunca debe ser confiado desde el body o query params del cliente**.
   * Debe obtenerse exclusivamente de la sesión autenticada (`ctx.tienda_id`).
   * Toda consulta de lectura, actualización o borrado debe incluir obligatoriamente `.where(Entidad.tienda_id == ctx.tienda_id)`.
2. **Validación Estricta de Entrada (Pydantic v2):**
   * Usar `Field(..., ge=..., le=...)` y validadores para impedir inyecciones, precios negativos o strings excesivamente largos.
   * Evitar vulnerabilidades de asignación masiva (*Mass Assignment*).
3. **Estrategia de Caché en el Edge / CDN:**
   * Los endpoints de catálogo público (`/api/v1/productos` y `/api/v1/products`) deben emitir encabezados HTTP de caché compatibles con Vercel/Cloudflare:
     `Cache-Control: public, s-maxage=60, stale-while-revalidate=300`
   * Esto permite responder al 95% del tráfico en menos de **15 ms** directamente desde el CDN sin sobrecargar la base de datos.
4. **Respuestas de Error Consistentes:**
   * Los errores 4xx y 5xx deben emitir un formato estándar con código de error legible, mensaje descriptivo en español y sin filtrar detalles de stack traces internos.
5. **Estrategia Lingüística y Nomenclatura de URLs (Dual Routing):**
   * Toda la API expone **rutas canónicas en español** (`/api/v1/productos`, `/api/v1/tiendas`, `/api/v1/sincronizacion`, `/api/v1/administracion`, `/api/v1/sugerencias`, `/api/v1/telemetria`, `/api/v1/recetas`, `/api/v1/admin-tienda`) como estándar visible en OpenAPI/Swagger.
   * **Invariante de compatibilidad hacia atrás:** Toda ruta renombrada o nueva debe preservar sus alias en inglés (`/api/v1/products`, `/stores`, `/sync`, etc.) con `include_in_schema=False` o enrutadores secundarios para garantizar cero roturas en llamadas existentes de Astro o clientes externos.

---

## 8. Pirámide de Pruebas y Quality Gates

Todo código nuevo debe contar con cobertura automatizada antes de darse por completado:

1. **Pruebas Unitarias de Dominio (Cero I/O):**
   * Pruebas puras que validan lógica matemática, normalizadores y clasificadores (`domain/`). Se ejecutan en milisegundos sin dependencias externas.
2. **Pruebas de Repositorio e Integración (SQLite en Memoria):**
   * Validan consultas complejas de base de datos, filtros de catálogo, ordenamientos y relaciones ORM.
3. **Pruebas de API (`TestClient`):**
   * Validan contratos HTTP, códigos de estado (200, 201, 400, 403, 404), RBAC y estructura de los DTOs de salida.
4. **Regla de Oro:** Ningún PR, refactor o funcionalidad nueva se da por terminada sin su prueba unitaria específica en `tests/test_<modulo>.py`.

---

## 9. Protocolo de Autonomía e Interacción Humana (Human-in-the-Loop)

Para maximizar la autonomía sin poner en riesgo la estabilidad del sistema ni generar costos imprevistos:

```text
                        ¿La decisión técnica tiene solución estándar?
                                    /                  \
                                  SÍ                    NO
                                 /                        \
           ¿Afecta contratos públicos,            ¿Hay ambigüedad en la
         destrucción de datos o costos?         regla de negocio requerida?
                   /             \                          |
                 SÍ               NO                        |
                /                   \                       |
       [PREGUNTAR / /plan]       [PROCEDER]            [PREGUNTAR]
```

1. **Proceder de forma 100% Autónoma:**
   * Corrección de bugs identificados con causa raíz clara.
   * Creación o ajuste de índices para optimizar consultas lentas identificadas.
   * Implementación de endpoints o casos de uso cuyo contrato ya fue definido.
   * Creación y ejecución de pruebas unitarias focalizadas.
   * Refactorizaciones internas que no alteren contratos públicos de la API ni de la base de datos.
2. **Detenerse y Consultar / Solicitar Aprobación (`/plan`):**
   * **Cambios Destructivos:** Operaciones `DROP TABLE`, `DROP COLUMN` o mutaciones irreversibles sobre datos de producción.
   * **Rotura de Contratos de API Pública:** Modificar o eliminar campos en respuestas JSON que romperían el frontend en Astro o clientes existentes.
   * **Reglas de Negocio Ambiguas:** Dudas sobre criterios de precios, categorizaciones no contempladas o políticas de scraping de una tienda específica.
   * **Costos o Librerías Nuevas:** Incorporar servicios externos de pago o dependencias no listadas en `requirements.txt`.

---

## 10. Protocolo Estricto de SEO y Buenas Prácticas Frontend (OBLIGATORIO)

Toda modificación en el frontend (`astro-frontend/`) debe cumplir sin excepción las siguientes directivas de SEO y Core Web Vitals:

1. **Metaetiquetas y URLs Canónicas:**
   * Cada página debe tener un `<title>` descriptivo y único con patrón: `[Tema Principal] | Cafesitios - [Propuesta de Valor]`.
   * Meta descripción (`<meta name="description">`) concisa, persuasiva y de entre 130 y 160 caracteres.
   * Enlace canónico explícito `<link rel="canonical" href="...">` para evitar penalización por contenido duplicado generado por query params de filtros.
   * Etiquetas Open Graph (`og:title`, `og:description`, `og:image`, `og:url`, `og:type`) y Twitter Card (`twitter:card: "summary_large_image"`).
2. **Semántica HTML y Jerarquía de Encabezados:**
   * Exactamente un único `<h1>` semántico por vista que sintetice la palabra clave principal (ej. "Comparador de Café de Especialidad en Chile").
   * Jerarquía sin saltos arbitrarios: `h1` $\to$ `h2` $\to$ `h3`.
   * Estructura semántica obligatoria: `<header>`, `<main>`, `<section>`, `<article>`, `<aside>`, `<footer>`.
3. **Core Web Vitals y Manejo de Imágenes (LCP / CLS):**
   * Toda etiqueta `<img>` debe tener atributo `alt` informativo en español.
   * Definir dimensiones explícitas (`width`, `height`) o clases Tailwind de aspecto (`aspect-square`, `aspect-[4/3]`) para evitar cambios bruscos de diseño (CLS = 0).
   * La imagen principal de portada (Hero / LCP) debe llevar `loading="eager"` y `fetchpriority="high"`.
   * Todas las demás imágenes (grillas de catálogo, tarjetas de tiendas) deben usar `loading="lazy"`.
4. **Datos Estructurados (Schema.org / JSON-LD):**
   * Incorporar scripts `<script type="application/ld+json">` en el `<head>`:
     - Home / Landing: `WebSite` con `potentialAction` (`SearchAction`) y `Organization`.
     - Detalle de Producto: `Product` con `Offer` (precio en CLP, disponibilidad) y `Brand`.
     - Tiendas: `LocalBusiness` / `Store` con coordenadas y comuna.
5. **Arquitectura de Islas Astro y Rendimiento:**
   * Priorizar componentes estáticos `.astro`.
   * En componentes interactivos con estado cliente (React), usar preferentemente `client:visible` o `client:idle`, reservando `client:load` únicamente para componentes de interacción crítica above-the-fold.

---

## 11. Política de Git y Commits

1. **Commits Bajo Demanda:** NO generar commits automáticos salvo que el usuario lo solicite expresamente.
2. **Formato:** Conventional Commits en español (`feat(scrapper): driver para jumpseller`, `fix(api): corregir filtro de precios`, `perf(db): indices compuestos`).
3. **Protección de Ramas:** Nunca confirmar directamente sobre `main` o `master` si hay cambios remotos pendientes; trabajar en ramas de características (`feat/`, `fix/`).