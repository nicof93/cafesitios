# AGENTS.md - Protocolo de Eficiencia y Contexto para Agentes de IA

Este documento establece los contratos de datos, la arquitectura y las reglas de ejecucion para **Cafe-sitios**. Todo agente que opere en este repositorio debe cumplir estas directivas para maximizar la autonomia y **minimizar el consumo innecesario de tokens/creditos**.

---

## 1. Estrategia de Ahorro de Creditos y Optimizacion de Flujo (CRITICO)

Para evitar consumo desmedido de ventana de contexto y llamadas de herramientas innecesarias:

1. **Aislamiento de Tareas (Edicion Quirurgica):**
   * Modifica **unicamente** los archivos directamente involucrados en la solicitud.
   * NO leas todo el proyecto para resolver un problema puntual. Usa la estructura del mapa para ir directo al archivo.
2. **Ejecucion de Pruebas Focalizadas:**
   * **NUNCA** ejecutes la suite completa de pruebas ('discover') salvo que el usuario lo pida o sea un cambio estructural global.
   * Corre exclusivamente la prueba unitaria del modulo afectado (ej. 'python -m unittest tests/test_woocommerce_driver.py').
3. **Procesamiento Muestral en Scraping:**
   * Al depurar o crear drivers de scraping, **NO cargues respuestas JSON o HTML completas en el chat**. Trabaja con fragmentos de muestra o mocks locales en 'tests/'.
4. **Respeto Estricto de Librerias ('requirements.txt'):**
   * NO intentes instalar ni sugerir paquetes adicionales (como 'pytest', 'httpx', 'pydantic-settings'). Usa unicamente la pila existente.
5. **No tocar 'README.md' innecesariamente:**
   * Modifica 'README.md' unicamente si la tarea cambia explicitamente la instalacion, configuracion, variables de entorno o comandos de ejecucion principales.

---

## 2. Vision General y Stack Tecnologico Fijo

* **Proyecto:** Agregador y comparador de precios de cafe de especialidad en Chile.
* **Lenguaje:** Python 3.11+ con **Type Hints estrictos** (obligatorios en firmas de funciones/metodos).
* **Dependencias Fijas ('requirements.txt'):**
  * 'fastapi >= 0.100.0' | 'uvicorn >= 0.22.0'
  * 'sqlalchemy >= 2.0.0' (Sintaxis 2.0 con 'select()', no usar '.query()')
  * 'alembic >= 1.13.0'
  * 'psycopg[binary] >= 3.1.0' (Driver Psycopg 3 para PostgreSQL)
  * 'pydantic >= 2.0.0' (Sintaxis Pydantic v2: 'ConfigDict', 'from_attributes', 'Field')
  * 'requests >= 2.31.0' | 'python-dotenv >= 1.0.0'
* **Testing:** Modulo nativo 'unittest'.

---

## 3. Mapa de Arquitectura (DDD Simplificado)

cafe-sitios/
├── domain/                  # Entidades puras y Contratos (CERO dependencias externas)
│   ├── models.py            # Dataclasses: CoffeeProduct, Variant, Store
│   └── repositories.py      # Interfaces/ABCs: ProductRepository
├── application/             # Casos de Uso (Orquestacion sin detalles de infraestructura)
│   └── get_cheapest_products.py
├── infrastructure/          # Adaptadores E/S y Persistencia
│   └── postgres_repository.py # Implementacion SQLAlchemy 2.0 de ProductRepository
├── api/                     # Capa HTTP (FastAPI)
│   ├── router.py            # APIRouter (/api/v1/products/...)
│   └── schemas.py           # DTOs Pydantic v2
├── db/                      # Configuracion de BD y Modelos ORM
│   ├── config.py            # Carga de variables (.env)
│   └── database.py          # Tablas SQLAlchemy (DeclarativeBase)
├── alembic/                 # Migraciones de base de datos
├── scrapper/                # Drivers ETL (Shopify JSON / WooCommerce Store API)
├── tests/                   # Pruebas automatizadas con unittest
├── scrapper_application.py  # Entrypoint ETL
├── main.py                  # Entrypoint API
└── AGENTS.md                # Instrucciones de contexto

---

## 4. Comandos Canonicos de Desarrollo

Todos los comandos se ejecutan desde la raiz del proyecto.

1. Pruebas unitarias puntuales (Usar SIEMPRE preferentemente):
   python -m unittest tests/test_woocommerce_driver.py
   python -m unittest tests/test_driver.py
   python -m unittest tests/test_api.py

2. Migraciones con Alembic:
   alembic revision --autogenerate -m \"descripcion\"
   alembic upgrade head

3. Ejecucion local:
   python scrapper_application.py          # Correr scraper
   python -m uvicorn main:app --reload      # Correr API FastAPI

---

## 5. Contratos de Datos y Reglas de Negocio Invariantes

Cualquier nuevo driver, endpoint o caso de uso debe cumplir sin excepcion:

1. Precios (CLP): 'precio_clp' y 'precio_original_clp' son enteros ('int'). Si la fuente incluye 'minor_unit', dividir entre 10^minor_unit.
2. Gramos ('formato_gramos'): Entero ('int'). Patrones: '250g', '1kg' (-> 1000). Fallback predeterminado = 250.
3. Precio por Kilo: 'round((precio_clp / formato_gramos) * 1000, 2)'. Si el precio o gramos es <= 0, retorna 0.0.
4. Ofertas: 'en_oferta = True' si 'precio_original_clp > precio_clp'.
5. Pydantic v2 Syntax:
   from pydantic import BaseModel, ConfigDict
   class ProductSchema(BaseModel):
       model_config = ConfigDict(from_attributes=True)
6. Interfaz de Drivers Scraping:
   class BaseDriver:
       @staticmethod
       def extraer_gramos(texto: Optional[str], default: int = 250) -> int: ...
       @staticmethod
       def calcular_precio_por_kilo(precio_clp: int, formato_gramos: int) -> float: ...
       def consumir_productos(self) -> List[Dict[str, Any]]: ...

---

## 6. Gotchas Tecnicas Entorno / BD

* Windows CP1252 Encoding: Si un script o test imprime emojis/caracteres especiales en consola, debe incluir:
  if sys.platform == 'win32': sys.stdout.reconfigure(encoding='utf-8')
* Conexion PostgreSQL (Psycopg 3): Usar siempre 'postgresql+psycopg://' en la URL. Contrasenas con caracteres especiales deben codificarse en URL (ej: '#' -> '%23').
* SQLAlchemy Batching: Las inserciones/actualizaciones masivas de productos en 'postgres_repository.py' se procesan en lotes de 20 a 50 items para evitar idle timeouts con Supabase.

---

## 7. Politica de Git y Commits

1. Commits Bajo Demanda: NO generar commits automaticos salvo que el usuario lo solicite expresamente.
2. Formato: Conventional Commits en espanol ('feat(scrapper): driver para jumpseller', 'fix(api): corregir filtro de precios').
3. Proteccion de Ramas: Nunca confirmar directamente sobre 'main' o 'master' si hay cambios remotos pendientes; trabajar en ramas de caracteristicas ('feat/', 'fix/').