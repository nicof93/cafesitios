---
id: "SPEC-003"
title: "Comparador Side-by-Side con Deduplicación por Gramaje"
status: "accepted"
created_at: "2026-10-08"
updated_at: "2026-10-08"
author: "Agente Antigravity"
---

# SPEC-003: Comparativa Side-by-Side (CU-03 / RN-03)

## 1. Contexto y Problema
Los usuarios necesitan cotejar de 2 a 4 cafés simultáneamente (precios, origen, proceso, precio/kg y formatos) para decidir cuál comprar. Si un café tiene múltiples formatos (ej. 250g, 500g y 1kg), incluir todos generaría ruido en la tabla comparativa.

## 2. Requerimientos Funcionales
* **Como:** Comprador de café.
* **Quiero:** Seleccionar hasta 4 productos y ver una tabla comparativa alineada lado a lado.
* **Para:** Evaluar rápidamente qué opción tiene la mejor relación calidad/precio.

## 3. Reglas de Negocio (RN-03)
1. **Límite de Selección:** Mínimo 1 producto, máximo 4 productos (`ids=1,2,3,4`).
2. **Deduplicación por Gramaje (Mejor Variante):** Para cada producto comparado, se selecciona una única variante para la vista comparativa: aquella con el menor `precio_por_kilo` que esté disponible (`disponible == True`). Si no hay disponibles, se elige la de menor $/kg general.
3. **Ordenamiento de Resultados:** Los cafés en la respuesta se ordenan en orden ascendente por `precio_por_kilo` de su variante elegida.
4. **Resaltado Ganador:** El frontend destaca visualmente el café con el menor precio por kilo con una insignia "Mejor precio / kg".

## 4. Archivos Implementados
* `application/compare_products.py`: Caso de uso `CompareProductsUseCase`.
* `api/products.py`: Endpoint `GET /api/v1/products/compare?ids=1,2,3`.
* `api/schemas.py`: `CompareResponse`, `CompareProductItem`.
* `frontend-website/index.html`: Dock flotante y modal comparativo.
* `tests/test_compare_products.py`: Pruebas de deduplicación y ordenamiento.

