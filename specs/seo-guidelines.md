# Especificación Técnica de SEO y Core Web Vitals - Cafesitios Frontend

Este documento detalla la implementación y los contratos de Search Engine Optimization (SEO), Core Web Vitals (CWV) y datos estructurados (Schema.org) aplicados a `astro-frontend`.

---

## 1. Metaetiquetas Globales y Open Graph

Cada plantilla en `astro-frontend/src/pages/` debe alimentar `BaseLayout.astro` con los siguientes metadatos:
- **Title Tag**: Máximo 60 caracteres. Debe incorporar la palabra clave relevante y la marca.
  * *Landing*: `Cafesitios | Comparador de Café de Especialidad en Chile - $/kg`
  * *Catálogo*: `Catálogo de Café de Especialidad | Comparar $/kg en Chile - Cafesitios`
  * *Tiendas*: `Tostadurías y Tiendas de Café en Chile | Cafesitios`
  * *Detalle Producto*: `[Nombre Café] | [Tienda] - Precio por Kilo | Cafesitios`
- **Meta Description**: Entre 130 y 160 caracteres con call-to-action sutil.
- **Canonical URL**: `<link rel="canonical" href="https://cafesitios.cl/[ruta]">`. En vistas de catálogo con filtros dinámicos (`?notes=...&price=...`), el canonical debe apuntar a la URL base limpia para consolidar la autoridad de página y evitar contenido duplicado.
- **Open Graph & Twitter**:
  * `og:title`, `og:description`, `og:type` (`website` o `product`), `og:image` (1200x630px).
  * `twitter:card`: `summary_large_image`.

---

## 2. Datos Estructurados JSON-LD (Schema.org)

### A. WebSite & Organization (Landing / Home)
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://cafesitios.cl/#organization",
      "name": "Cafesitios",
      "url": "https://cafesitios.cl",
      "logo": "https://cafesitios.cl/favicon.svg",
      "description": "Plataforma de comparación de precios por kilo y descubrimiento de café de especialidad en Chile."
    },
    {
      "@type": "WebSite",
      "@id": "https://cafesitios.cl/#website",
      "url": "https://cafesitios.cl",
      "name": "Cafesitios",
      "publisher": { "@id": "https://cafesitios.cl/#organization" },
      "potentialAction": {
        "@type": "SearchAction",
        "target": "https://cafesitios.cl/catalog?q={search_term_string}",
        "query-input": "required name=search_term_string"
      }
    }
  ]
}
```

### B. Product & Offer (Detalle de Café)
```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Colombia El Paraíso",
  "description": "Café de especialidad origen Colombia, proceso anaeróbico, notas frutales.",
  "brand": {
    "@type": "Brand",
    "name": "Singular Coffee"
  },
  "offers": {
    "@type": "Offer",
    "priceCurrency": "CLP",
    "price": "14990",
    "availability": "https://schema.org/InStock",
    "url": "https://singularcoffee.cl/..."
  }
}
```

---

## 3. Core Web Vitals (LCP, CLS, INP)

1. **Largest Contentful Paint (LCP < 2.5s)**:
   - La imagen del Hero en la landing page debe tener `loading="eager"` y `fetchpriority="high"`.
   - Evitar fuentes externas pesadas bloqueantes; usar preconnect y fuentes del sistema / sans-serif optimizadas.
2. **Cumulative Layout Shift (CLS < 0.1)**:
   - Todas las imágenes de tarjetas de producto y logotipos deben declarar `width` y `height` o clase Tailwind `aspect-square`.
   - Las tipografías deben renderizar con `font-display: swap`.
3. **Interaction to Next Paint (INP < 200ms)**:
   - Todo renderizado de filtros complejos debe diferir el estado pesado con microtareas o transiciones fluidas.

---

## 4. Archivos de Control de Rastreo

- `public/robots.txt`:
  ```text
  User-agent: *
  Allow: /
  Disallow: /api/
  Sitemap: https://cafesitios.cl/sitemap.xml
  ```

