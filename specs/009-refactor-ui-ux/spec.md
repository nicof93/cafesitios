---
id: "SPEC-009"
title: "Modernización y Refactorización UI/UX DTC (Clean E-Commerce)"
status: "accepted"
created_at: "2026-10-16"
updated_at: "2026-10-16"
author: "Agente Antigravity"
---

# SPEC-009: Modernización y Refactorización UI/UX DTC (Clean E-Commerce)

## 1. Contexto y Problema
La interfaz original presentaba saturación visual en la parte superior (above-the-fold) con un bloque de pastillas de tiendas apelmazadas, tarjetas con bajo contraste para paquetes de café blancos o claros, botones secundarios que no se diferenciaban claramente de la acción de conversión y una barra lateral con secciones duplicadas.
Se requería aplicar principios de **Clean E-commerce UX patterns (DTC)**, **Refactoring UI**, y lineamientos de **NN/g** para navegación facetada y tarjetas de producto.

## 2. Requerimientos Funcionales y de Experiencia de Usuario
* **Header compacto y global:**
  - Altura reducida (`py-2.5`), logo con enlace a `/` que restablece filtros.
  - Navegación clara: Catálogo, Todas las Tiendas, Quiz de Sabor, Bitácora de Recetas.
  - Sync status como pill discreto no invasivo.
* **Filtros unificados y descongestión above-the-fold:**
  - Eliminación del bloque horizontal y sección aislada "🏪 Tiendas Disponibles".
  - Sidebar izquierdo (`FiltersAside.astro`) unificado con buscador semántico de esquinas redondeadas (`rounded-lg`), selector de ordenamiento, checklist sobrio de tiendas, y facetas colapsables (origen, proceso, variedad, notas, rango de precio).
  - Banner hero promocional DTC sobrio sobre la grilla: *"Encuentra el mejor precio por kilo ($/kg) en café de especialidad"*.
* **Tarjetas de Producto Clickable Card y Jerarquía de Precios:**
  - Toda la tarjeta es clicable hacia `/product/[id]`.
  - Controles anidados (`+ Comparar`, `Comprar en tienda ↗`) aíslan eventos mediante `event.stopPropagation()`.
  - Contenedor de packshot con fondo neutro suave (`bg-[#F4F3ED]` / `bg-stone-100`) y sombra para resaltar empaques claros.
  - **Jerarquía de Precios:** El **Precio del Formato/Bolsa** ($ CLP) es el protagonista principal (`text-lg font-extrabold text-stone-900`), mientras que el **Precio por Kilo ($/kg)** pasa a un rol secundario/referencial discreto (`text-xs font-bold text-stone-700 bg-stone-100`).
* **Categorización y Exclusión de No-Café:**
  - Filtrado por categoría en backend y frontend (`category=cafe` por defecto) para ignorar ropa, bolsos, suscripciones, cajas de regalo, molinillos y cafeteras en el catálogo principal.
  - Disponibilidad de categoría especial (`no_cafe` / `todos`) seleccionable desde el panel lateral.
* **Scroll Infinito Reactivo:**
  - Al aproximarse al final del catálogo, un `IntersectionObserver` inicia consultas automáticas a la API con `offset` incremental (`limit=18`), renderizando dinámicamente nuevas tarjetas sin recargar la página.
* **Vista Detalle de Producto (`/product/[id]`):**
  - Hero en 2 columnas: galería/packshot a la izquierda y ficha técnica estructurada a la derecha.
  - Data-chips de 2 columnas para especificaciones (País, Región, Altitud, Proceso, Variedad).
  - Notas de cata en badges redondeados ámbar/cálidos.
  - Gráfico de histórico de precios con métricas clave superiores (precio actual, mínimo, promedio).
  - Tabla de variantes clara.
  - Sticky Bottom Bar (`fixed bottom-6 max-w-3xl`) con botón de compra rápida.
  - Carrusel/grilla de cafés relacionados al pie.
* **Widget Flotante de Feedback:**
  - Botón flotante inferior derecho (`fixed bottom-6 right-6 z-40`) con texto *"☕ Pensamos en los amantes del café"*, sin colisionar con la barra de compra.

## 3. Componentes Implementados / Modificados
* `astro-frontend/src/components/common/Header.astro`
* `astro-frontend/src/components/catalog/FiltersAside.astro`
* `astro-frontend/src/components/catalog/ProductCard.astro`
* `astro-frontend/src/components/feedback/FeedbackWidget.astro`
* `astro-frontend/src/pages/index.astro`
* `astro-frontend/src/pages/product/[id].astro`
* `astro-frontend/src/pages/stores.astro`
* `astro-frontend/src/components/catalog/RecentlyViewed.astro`

