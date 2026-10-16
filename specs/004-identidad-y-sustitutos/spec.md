---
id: "SPEC-004"
title: "Identidad Estricta de Grano y Sustitutos Directos"
status: "accepted"
created_at: "2026-10-08"
updated_at: "2026-10-08"
author: "Agente Antigravity"
---

# SPEC-004: Identidad Estricta de Grano y Sustitutos Directos (CU-04 / RN-04)

## 1. Contexto y Problema
Varios tostadores en Chile importan lotes del mismo origen, finca o productor (ej. "Huila Colombia Lavado" o "Yirgacheffe Etiopía"). Cuando un usuario consulta un café en una tienda, desea saber si ese mismo grano o un sustituto directo está disponible en otra tienda y a qué precio.

## 2. Requerimientos Funcionales
* **Como:** Comprador en la página de detalle de un café.
* **Quiero:** Ver una sección "Disponible en otras tiendas" o "Sustitutos directos".
* **Para:** Comparar precios entre tostadores para el mismo perfil de grano.

## 3. Reglas de Negocio (RN-04)
1. **Identidad Estricta:** Dos cafés se consideran equivalentes si coinciden en su país de origen (`origen`) Y en su proceso (`proceso`).
2. **Exclusión de Auto-Referencia:** Nunca se debe incluir el mismo producto que el usuario está consultando.
3. **Ordenamiento:** Los cafés coincidentes se ordenan en forma ascendente por el `precio_por_kilo` de su variante más conveniente.
4. **Fallback Sensible:** Si un producto no tiene país o proceso catalogado, el endpoint retorna una lista vacía para evitar falsas equivalencias.

## 4. Archivos Implementados
* `infrastructure/postgres_repository.py`: Método `find_matching_products(product_id: int)`.
* `api/products.py`: Endpoint `GET /api/v1/products/{product_id}/matches`.
* `api/schemas.py`: Schema `ProductMatchesResponse`.
* `frontend-website/product.html`: Sección de tarjetas coincidentes.
* `tests/test_product_matches.py`: Test unitario de coincidencia y orden.

