---
id: "SPEC-001"
title: "Búsqueda con Expansión de Sinónimos Cafeteros"
status: "accepted"
created_at: "2026-10-08"
updated_at: "2026-10-08"
author: "Agente Antigravity"
---

# SPEC-001: Búsqueda con Expansión de Sinónimos Cafeteros (CU-01 / RN-01)

## 1. Contexto y Problema
En el mercado de café de especialidad conviven múltiples grafías para un mismo concepto (ej. Gesha vs Geisha, Borbón vs Bourbon, Lavado vs Washed, Anaeróbico vs Anaerobio). Una búsqueda SQL `ILIKE` estricta genera altas tasas de falsos ceros cuando el usuario escribe con o sin tildes o con ortografía alternativa.

## 2. Requerimientos Funcionales
* **Como:** Comprador de café de especialidad.
* **Quiero:** Encontrar todas las opciones de una variedad o proceso sin importar cómo lo haya escrito el tostador.
* **Para:** Descubrir cafés relevantes rápidamente sin tener que hacer múltiples búsquedas manuales.

## 3. Reglas de Negocio (RN-01)
1. **Normalización Lingüística:** El término de búsqueda se convierte a minúsculas y se le eliminan acentos ortográficos (NFD desacentuado).
2. **Diccionario de Sinónimos Bidireccional:**
   * `geisha` <-> `gesha`
   * `borbon` <-> `bourbon`
   * `anaerobico` <-> `anaerobio`
   * `lavado` <-> `washed`
   * `natural` <-> `seco`
   * `moka` <-> `moca`
   * `maragogype` <-> `maragogipe`
   * `pacamara` <-> `paca mara`
   * `descafeinado` <-> `decaf`
3. **Composición de Consulta:** Cada token de búsqueda se expande a su lista de sinónimos. En el repositorio de persistencia, se genera una cláusula SQL `OR` para cada variante de sinónimo sobre las columnas de nombre, variedad, proceso y notas de cata.

## 4. Archivos Implementados
* `domain/search_normalizer.py`: Función pura `expand_search_terms(query: str) -> List[str]`.
* `infrastructure/postgres_repository.py`: Integración en `_build_base_query()`.
* `tests/test_search_normalizer.py`: Suite de 6 pruebas unitarias.

