---
id: "SPEC-002"
title: "Precio por Kilo Oficial vs Estimado"
status: "accepted"
created_at: "2026-10-08"
updated_at: "2026-10-08"
author: "Agente Antigravity"
---

# SPEC-002: Precio por Kilo Oficial vs Estimado (CU-02 / RN-02)

## 1. Contexto y Problema
Cuando una tienda omite el gramaje de una bolsa de café en su título u opciones, los scrapers aplican un valor fallback de 250 gramos. Sin embargo, mostrar dicho precio por kilo como una cifra oficial puede inducir a error o generar desconfianza en el usuario si en realidad el paquete era de otro tamaño (ej. 200g o 500g).

## 2. Requerimientos Funcionales
* **Como:** Usuario que compara precios.
* **Quiero:** Saber con total transparencia cuándo un precio por kilo fue calculado a partir de un gramaje explícito y cuándo corresponde a una estimación.
* **Para:** Tomar decisiones de compra bien fundamentadas.

## 3. Reglas de Negocio (RN-02)
1. **Flag Booleano `es_estimado`:**
   * `es_estimado = False`: Cuando el gramaje (`formato_gramos`) fue extraído explícitamente mediante expresiones regulares del título o de la opción del producto (ej: `250g`, `1kg`, `500 gr`).
   * `es_estimado = True`: Cuando no se encontró ningún patrón de peso y se recurrió al fallback por defecto (250g).
2. **Persistencia y Exposición:**
   * Columna booleana `es_estimado` en la tabla `variantes`.
   * Campo `es_estimado: bool` expuesto en `VariantResponse` de Pydantic v2.
3. **Indicador Visual:**
   * La UI renderiza un badge distintivo de advertencia `Estimado` con tooltip explicativo junto a la cifra de $/kg.

## 4. Archivos Implementados
* `db/database.py`: Columna `es_estimado = Column(Boolean, default=False, nullable=False)`.
* `domain/models.py`: Atributo `es_estimado` en `VariantDomain`.
* `api/schemas.py`: Campo `es_estimado: bool` en `VariantResponse`.
* `frontend-website/index.html` & `product.html`: Badges visuales en catálogo y detalle.

