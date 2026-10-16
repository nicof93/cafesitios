---
id: "SPEC-008"
title: "Módulo Flotante de Feedback Anónimo con Rate Limiting y Honeypot"
status: "accepted"
created_at: "2026-10-08"
updated_at: "2026-10-08"
author: "Agente Antigravity"
---

# SPEC-008: Feedback Anónimo (CU-11)

## 1. Contexto y Problema
El comparador se nutre de datos dinámicos. Los usuarios detectan precios desactualizados o quieren sugerir nuevas tiendas. Se requiere un canal de retroalimentación ultrarrápido y seguro contra spam.

## 2. Requerimientos Funcionales
* **Como:** Visitante del sitio.
* **Quiero:** Enviar sugerencias o reportes en 2 clics desde cualquier página.
* **Para:** Ayudar a mantener la plataforma actualizada sin trámites ni registro de datos personales.

## 3. Reglas Técnicas y Anti-Abuso
1. **Categorías Estrictas:** `reportar_precio`, `tienda_faltante`, `sugerencia_ui`, `otro`.
2. **Honeypot Silencioso:** Campo señuelo oculto en la UI (`feedback-hp`). Si un bot rellena el campo, la solicitud se ignora silenciosamente.
3. **Rate Limiting Anónimo en Backend:** Máximo 2 feedbacks por hora por dirección IP hasheada (`SHA-256`). Si se supera, se responde `429 Too Many Requests`.
4. **Almacenamiento PII-Free:** Nunca se almacena la dirección IP en texto plano en la base de datos; únicamente su hash criptográfico truncado.

## 4. Archivos Implementados
* `db/database.py`: Modelo `SugerenciaFeedback`.
* `application/manage_feedback.py`: Casos de uso y hashing SHA-256 de IP.
* `api/feedback.py`: Router `POST /api/v1/feedback`.
* `frontend-website/index.html`: Botón flotante y modal responsive.
* `tests/test_feedback_api.py`: Pruebas de guardado, rate limit y categorías válidas.

