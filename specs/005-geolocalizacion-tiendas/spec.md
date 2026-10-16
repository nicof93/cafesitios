---
id: "SPEC-005"
title: "Ordenamiento y Cercanía Física con Haversine a Costo $0 USD"
status: "accepted"
created_at: "2026-10-08"
updated_at: "2026-10-08"
author: "Agente Antigravity"
---

# SPEC-005: Cercanía Física de Tiendas sin APIs Pagas (CU-05)

## 1. Contexto y Problema
Saber qué tostadores están cerca permite a los usuarios ahorrar en envíos o comprar presencialmente. Sin embargo, no se deben usar servicios de pago como Google Maps API para mantener el costo en $0 USD.

## 2. Requerimientos Funcionales
* **Como:** Consumidor de café.
* **Quiero:** Ordenar las tiendas por distancia geográfica desde mi ubicación o comuna.
* **Para:** Elegir opciones de despacho rápido o retiro en tienda cercano.

## 3. Reglas Técnicas
1. **Detección de Ubicación en Cascada ($0 USD):**
   * Coordenadas explícitas provistas por GPS del navegador (`lat`, `lon` en query params).
   * Si no hay coordenadas: Cabecera `x-vercel-ip-city` (ciudad/comuna reportada por el proxy de Vercel/Cloudflare).
   * Mapeo estático a coordenadas de comunas de Santiago y regiones (ej. Providencia, Santiago Centro, Las Condes, Valparaíso, Concepción).
2. **Cálculo de Distancia Haversine:**
   * Fórmula ortodrómica Haversine en Python (`R = 6371.0 km`).
   * Retorna `distancia_km` redondeado a 2 decimales.
3. **Compatibilidad:**
   * Al implementarse en capa Python en lugar de extensiones propietarias de base de datos, funciona de manera 100% idéntica en PostgreSQL y en SQLite (para testing).
4. **Visualización en Mapa Interactivo ($0 USD):**
   * Integración con Leaflet.js y mosaicos CartoDB Voyager / OpenStreetMap (100% libre de costo/API keys).
   * Marcadores con pines tipo espresso/taza en coordenadas reales de cada tostaduría.
   * Popups con nombre, comuna, conteo de cafés y enlace directo al catálogo filtrado por esa tienda.
   * Filtro en tiempo real por nombre y comuna, y botón para centrar en ubicación GPS del usuario.

## 4. Archivos Implementados
* `db/database.py`: Columnas `latitud`, `longitud`, `comuna` en `Tienda`.
* `api/stores.py`: Función `haversine_distance()`, tabla de comunas, `url_base` en respuesta y parámetro `sort_by=distance_asc`.
* `astro-frontend/src/pages/stores.astro`: Vista con mapa interactivo Leaflet.js, buscador instantáneo y listado responsive.
* `tests/test_nearby_stores.py`: Pruebas unitarias de cálculo y ordenamiento por cercanía.


