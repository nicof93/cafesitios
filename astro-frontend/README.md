# Astro Frontend — Cafe-sitios ☕

Frontend de alto rendimiento para **Cafe-sitios**, desarrollado con **Astro 5**, **TypeScript**, **Tailwind CSS**, arquitectura limpia (**Clean Architecture**) y diseño guiado por el dominio (**Domain-Driven Design - DDD**).

---

## 1. Arquitectura del Proyecto

El código fuente en `src/` sigue estrictamente la separación de responsabilidades:

```
src/
├── core/                           # Núcleo de la aplicación (Reglas de negocio y adaptadores)
│   ├── domain/                     # Entidades puras y tipos de dominio (CERO dependencias de frameworks)
│   │   ├── models/                 # CoffeeProduct, ProductVariant, Store, Recipe, Feedback, Recommendation
│   │   └── errors/                 # AppError, ApiError, NotFoundError, RateLimitError
│   ├── application/                # Casos de uso (Orquestación del negocio)
│   │   ├── GetCatalog.ts           # Obtención de catálogo con búsqueda y filtros
│   │   ├── GetProductDetail.ts     # Ficha de café y sustitutos directos (RN-04)
│   │   ├── GetStores.ts            # Directorio de tiendas y cálculo de cercanía (Haversine)
│   │   ├── CompareProducts.ts      # Comparativa Side-by-Side con deduplicación por $/kg (RN-03)
│   │   ├── GetRecommendations.ts   # Recomendador del Quiz de Sabor con scoring y penalización de stock
│   │   ├── ManageRecipes.ts        # Bitácora Local-First y respaldo en nube
│   │   └── SubmitFeedback.ts       # Envío de feedback anónimo con protección anti-abuso
│   └── infrastructure/             # Adaptadores de entrada/salida y servicios externos
│       ├── api/                    # HttpClient unificado (fetch, timeouts, tipado estricto)
│       ├── storage/                # LocalStorageAdapter (Recetas, Vistos recientemente, DeviceId)
│       ├── analytics/              # AnalyticsTracker (11 eventos canónicos dataLayer + backend beacon)
│       └── config/                 # Environment (detección inteligente SSR / Browser)
├── components/                     # Componentes UI (Astro + TS puro)
│   ├── common/                     # Header, Footer
│   ├── catalog/                    # ProductCard, FiltersAside, StoreChips, RecentlyViewed
│   ├── compare/                    # CompareBarAndModal (Dock flotante y diálogo)
│   ├── quiz/                       # FlavorQuizModal (Diálogo interactivo de 3 pasos)
│   ├── recipes/                    # RecipeBookModal (Bitácora local-first y ratio calculator)
│   └── feedback/                   # FeedbackWidget (Botón flotante, diálogo y honeypot)
├── layouts/                        # Plantillas comunes
│   └── BaseLayout.astro            # Estructura HTML5, SEO OpenGraph, analítica y diálogos globales
├── pages/                          # Rutas SSR
│   ├── index.astro                 # Catálogo interactivo con SSR inicial
│   ├── product/[id].astro          # Detalle dinámico con gráfico Chart.js y sustitutos
│   ├── stores.astro                # Directorio de tiendas y ordenamiento por GPS/comuna
│   └── 404.astro                   # Manejo de páginas o cafés no encontrados
└── styles/                         # Hojas de estilo globales
    └── global.css                  # Tailwind CSS y tipografía enriquecida
```

---

## 2. Variables de Ambiente

El proyecto maneja archivos de variables de entorno para separar desarrollo y producción:

| Variable | Descripción | Ejemplo Local | Ejemplo Producción |
| :--- | :--- | :--- | :--- |
| `PUBLIC_API_BASE_URL` | URL de la API consumida desde el navegador | `http://localhost:8000` | `https://cafe-sitios.onrender.com` |
| `INTERNAL_API_BASE_URL` | URL de la API consumida en SSR por el servidor | `http://localhost:8000` | `https://cafe-sitios.onrender.com` |
| `PUBLIC_GTM_ID` | Contenedor de Google Tag Manager (Opcional) | `GTM-XXXXXXX` | `GTM-XXXXXXX` |
| `PUBLIC_GA_MEASUREMENT_ID` | Medición de Google Analytics 4 (Opcional) | `G-XXXXXXXXXX` | `G-XXXXXXXXXX` |

* **Local:** Definido en `.env`.
* **Producción:** Configurado en el panel de Vercel o en `.env.production`.

---

## 3. Comandos de Ejecución

Desde la carpeta `astro-frontend`:

```bash
# Instalar dependencias
npm install

# Modo desarrollo (con recarga rápida)
npm run dev

# Ejecutar suite de pruebas unitarias (Vitest + Happy-DOM)
npm test

# Compilación para producción (genera .vercel/output)
npm run build

# Previsualizar el build de producción
npm run preview
```

---

## 4. Despliegue en Vercel

1. El proyecto incluye el adaptador oficial `@astrojs/vercel` configurado en `astro.config.mjs` con `output: "server"`.
2. Al conectar el repositorio con Vercel:
   * **Root Directory:** `astro-frontend`
   * **Framework Preset:** `Astro`
   * **Build Command:** `astro build`
   * **Output Directory:** `.vercel/output` (manejado automáticamente por el adaptador).
3. Configurar las variables de entorno `PUBLIC_API_BASE_URL` e `INTERNAL_API_BASE_URL` apuntando a la instancia de FastAPI en Render.

