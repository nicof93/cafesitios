---
id: "SPEC-007"
title: "Bitácora de Recetas Local-First con Fake Door de Sincronización"
status: "accepted"
created_at: "2026-10-08"
updated_at: "2026-10-08"
author: "Agente Antigravity"
---

# SPEC-007: Bitácora de Recetas Local-First (CU-08)

## 1. Contexto y Problema
Los amantes del café quieren anotar sus parámetros de extracción (ratio, molienda, agua, tiempo y notas). Forzar registro previo (login/OAuth) crea fricción de abandono del 90%.

## 2. Requerimientos Funcionales
* **Como:** Barista en casa o consumidor.
* **Quiero:** Guardar recetas de preparación al instante sin crear cuenta.
* **Para:** Perfeccionar mi taza diaria y tener respaldo de mis pruebas favoritas.

## 3. Reglas Técnicas y de Seguridad
1. **Local-First en Browser:** Almacenamiento primario en `localStorage` (`cafesitios_recetas_v1`) accesible sin conexión.
2. **Sincronización en la Nube (Fake Door):** Botón para respaldar en la nube mediante `POST /api/v1/recetas`.
3. **5 Capas de Seguridad en Backend:**
   * Capa 1: Validación estricta de esquema Pydantic (`device_id` requerido, rangos físicos: agua 10-2000ml, café 1-200g, tiempo 1-1800s, nota 1-5).
   * Capa 2: Sanitización de entradas contra XSS e inyecciones.
   * Capa 3: Quota por dispositivo (máximo 15 recetas en BD por `device_id` para evitar saturación de almacenamiento).
   * Capa 4: Rate limit en endpoint.
   * Capa 5: SHA-256 IP logging para trazabilidad PII-free.

## 4. Archivos Implementados
* `db/database.py`: Modelo `Receta`.
* `application/manage_recipes.py`: Lógica de validación y control de cuota por dispositivo.
* `api/recipes.py`: Router `POST /api/v1/recetas` y `GET /api/v1/recetas`.
* `frontend-website/index.html`: Modal de recetas con gestión local y botón de respaldo.
* `tests/test_recipes_api.py`: Pruebas de guardado, lectura y cuota máxima (15).

