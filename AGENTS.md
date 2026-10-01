# AGENTS.md - Guía de Contexto para Agentes de IA

Este documento describe la arquitectura, convenciones, comandos canónicos y reglas de negocio del proyecto **Cafe-sitios** para facilitar el trabajo autónomo de agentes de inteligencia artificial y desarrolladores.

---

## 1. Visión General del Proyecto

**Cafe-sitios** es una plataforma de agregación, normalización y comparación de precios de café de especialidad en Chile.
- **Scraper / ETL:** Extrae catálogos y variantes de tiendas de especialidad en distintas plataformas (Shopify y WooCommerce Store API) y almacena el historial de precios.
- **Base de Datos:** PostgreSQL (local o Supabase) gestionado mediante SQLAlchemy ORM con el driver `psycopg` (psycopg3).
- **Backend API:** FastAPI estructurado bajo **Domain-Driven Design (DDD)** y Clean Architecture (Nivel 2 de Madurez de Richardson).

---

## 2. Comandos Canónicos de Desarrollo

Todos los comandos se deben ejecutar desde la raíz del espacio de trabajo.

### Ejecución de Pruebas Unitarias
```bash
# Ejecutar toda la suite de pruebas
python -m unittest discover tests

# Ejecutar en modo detallado (verbose)
python -m unittest discover tests -v

# Ejecutar una suite específica
python -m unittest tests/test_woocommerce_driver.py
python -m unittest tests/test_driver.py
python -m unittest tests/test_api.py
python -m unittest tests/test_use_cases.py
python -m unittest tests/test_domain.py
```

### Ejecución de la Aplicación
```bash
# Ejecutar pipeline de scraping y persistencia en base de datos
python scrapper_application.py

# Iniciar servidor FastAPI en modo desarrollo
python -m uvicorn main:app --reload
```

---

## 3. Mapa de Arquitectura y Estructura

El proyecto implementa una arquitectura en capas desacoplada:

```
cafe-sitios/
├── domain/                      # Capa de Dominio (Pura, sin dependencias externas)
│   ├── models.py                # Entidades: CoffeeProduct, Variant
│   └── repositories.py          # Interfaces/Contratos: ProductRepository
├── application/                 # Capa de Aplicación (Casos de Uso)
│   └── get_cheapest_products.py # Use Case: ordenamiento por $/kg o $/unidad
├── infrastructure/              # Capa de Infraestructura
│   └── postgres_repository.py   # Implementación del repositorio usando SQLAlchemy
├── api/                         # Capa de Presentación / Transporte
│   ├── router.py                # Endpoints FastAPI (/api/v1/products/...)
│   └── schemas.py               # DTOs y Schemas de validación Pydantic
├── db/                          # Persistencia Relacional
│   ├── config.py                # Carga de variables de entorno (.env)
│   └── database.py              # Modelos ORM (Tienda, Producto, Variante, HistorialPrecio)
├── scrapper/                    # Drivers de Extracción
│   ├── shopify_driver.py        # Driver para tiendas Shopify (/products.json)
│   └── woocommerce_driver.py    # Driver para WooCommerce (/wp-json/wc/store/v1/products)
├── tests/                       # Suite de pruebas automatizadas
├── scrapper_application.py      # Entrypoint del scraping general
├── main.py                      # Entrypoint de la API FastAPI
└── AGENTS.md                    # Este archivo de instrucciones
```

---

## 4. Reglas de Negocio y Normalización de Datos

Cualquier nuevo driver, modelo o cambio debe cumplir estrictamente estas reglas:

1. **Precios en Pesos Chilenos (CLP):**
   * `precio_clp` y `precio_original_clp` son siempre números enteros (`int`).
   * WooCommerce Store API puede incluir `currency_minor_unit`; para CLP es 0, pero si es mayor a 0, se debe dividir entre $10^{\text{minor\_unit}}$.
2. **Formato en Gramos (`formato_gramos`):**
   * Siempre es un número entero (`int`).
   * Patrones aceptados: `250g`, `250-gr`, `1kg`, `1-kilo`, `500 gramos`.
   * Si no se especifica peso en la variante ni en el producto, el valor por defecto es **250** (formato estándar de café de especialidad en Chile).
3. **Precio por Kilo (`precio_por_kilo`):**
   * Cálculo estándar: `round((precio_clp / formato_gramos) * 1000, 2)`.
   * Si el precio es 0 o formato es 0, debe ser `0.0`.
4. **Detección de Ofertas:**
   * `en_oferta`: `True` si `precio_original_clp > precio_clp`, de lo contrario `False`.
   * `descuento_porcentaje`: entero redondeado del porcentaje de rebaja, o `0`.
5. **Identificadores Únicos:**
   * `Producto.url_detalle`: único en la tabla `productos`.
   * `Variante.id_variante_externo`: string único en la tabla `variantes`.
6. **Mapeo de Atributos en WooCommerce:**
   * Los slugs en `variations.attributes` (ej. `250-gr`, `molido-para-espresso`) se deben resolver a nombres legibles usando el diccionario `attributes.terms` del producto (ej. `"250 gr."`, `"molido para espresso"`).

---

## 5. Gotchas Técnicas y Consideraciones del Entorno

1. **Codificación en Windows (CP1252 vs UTF-8):**
   * Los scripts que imprimen emojis en consola deben configurar `sys.stdout.reconfigure(encoding="utf-8")` si se ejecutan en Windows para evitar `UnicodeEncodeError`.
2. **Conexión a Base de Datos (Supabase / PostgreSQL):**
   * La cadena de conexión en `.env` debe usar el formato `postgresql+psycopg://...` o `postgresql://...`.
   * Si la contraseña contiene caracteres especiales como `#`, debe entrecomillarse en `.env` y si es necesario codificarse como `%23` en la URL.
   * `DatabaseManager` incluye `pool_pre_ping=True` y `pool_recycle=300` para evitar sockets cerrados por *idle timeout*.
   * La persistencia se realiza con commits en lotes (cada 20 productos) y caché en memoria de tiendas (`tiendas_cache`) para minimizar la latencia sobre conexiones remotas.
3. **Drivers:**
   * Cada clase de driver debe implementar:
     * `@staticmethod extraer_gramos(texto: Optional[str], default: int = 250) -> int`
     * `@staticmethod calcular_precio_por_kilo(precio_clp: int, formato_gramos: int) -> float`
     * `consumir_productos() -> List[Dict[str, Any]]`

---

## 6. Política de Commits del Agente

Después de completar exitosamente cada solicitud, validar los cambios aplicables y crear un commit que incluya únicamente los archivos modificados para esa solicitud. No incluir ni descartar cambios preexistentes o ajenos; preparar los archivos explícitamente en lugar de usar `git add -A`.

Los mensajes deben seguir Conventional Commits con el formato `<tipo>(<ámbito>): <descripción>`, por ejemplo: `docs(agent): documentar política de commits`. Usar un tipo acorde al cambio (`feat`, `fix`, `docs`, `test`, `refactor`, `chore`, entre otros) y una descripción concreta.

Nunca crear commits directamente en `main` o `master`. Si el trabajo comienza en una de esas ramas:

1. Ejecutar `git fetch origin` y revisar si la rama local está sincronizada con su rama remota correspondiente.
2. Si hay cambios remotos pendientes, actualizar la base de trabajo de forma segura, preservando todos los cambios locales y sin sobrescribirlos.
3. Crear una rama nueva y descriptiva desde la rama remota actualizada antes de editar o confirmar cambios.
4. Preparar y confirmar solo los archivos de la solicitud en esa rama.

Si no es posible actualizar la rama o crear una rama de trabajo sin poner en riesgo cambios locales, detenerse sin confirmar en `main`/`master` y explicar el bloqueo. No hacer `push` salvo que se solicite explícitamente.
