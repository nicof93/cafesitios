---
id: "SPEC-006"
title: "Quiz Interactivo de Sabor con Scoring y Penalización de Stock"
status: "accepted"
created_at: "2026-10-08"
updated_at: "2026-10-08"
author: "Agente Antigravity"
---

# SPEC-006: Quiz Interactivo de Sabor (CU-07)

## 1. Contexto y Problema
Muchos usuarios no conocen variedades técnicas pero saben cómo preparan su café o qué perfil de sabor les agrada. Un recomendador interactivo de 3 pasos elimina la indecisión de compra.

## 2. Requerimientos Funcionales
* **Como:** Aficionado o principiante en café de especialidad.
* **Quiero:** Responder un breve cuestionario sobre método, perfil sensorial y acidez.
* **Para:** Recibir recomendaciones personalizadas con una explicación del porcentaje de afinidad (match score).

## 3. Reglas de Negocio
1. **Paso 1 - Método:** Espresso, Filtrado, Prensa Francesa, Cold Brew.
   * Asocia pesos a tipos de tueste y procesos recomendados.
2. **Paso 2 - Perfil Sensorial:** Frutal/Floral, Chocolate/Nueces, Cítrico/Balanceado, Especiado.
   * Busca coincidencias semánticas con las notas de cata y variedad.
3. **Paso 3 - Acidez:** Baja, Media, Alta.
   * Filtra y pondera según proceso (Lavado suele tener acidez más brillante, Naturales/Anaeróbicos acidez vinosa o media, tuestes oscuros acidez baja).
4. **Penalización de Stock:** Si un producto tiene todas sus variantes agotadas (`disponible == False`), su puntaje de afinidad se penaliza fuertemente en un 70% (`score * 0.3`) para priorizar compras viables.
5. **Resultado:** Retorna hasta 3 productos ordenados por afinidad.

## 4. Archivos Implementados
* `application/recommend_products.py`: `RecommendProductsUseCase`.
* `api/products.py`: Endpoint `GET /api/v1/products/recommend`.
* `api/schemas.py`: `RecommendationResponse`, `RecommendedProductItem`.
* `frontend-website/index.html`: Modal y flujo interactivo del quiz.
* `tests/test_recommendations.py`: Test unitario con validación de penalización de stock.

