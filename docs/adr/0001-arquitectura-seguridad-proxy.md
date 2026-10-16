# ADR 0001: Arquitectura de Seguridad Multicapa para API y Despliegue Frontend

## Estado
Aceptado

## Fecha
2026-10-08

## Contexto
El frontend de Cafe-sitios se aloja en Vercel mientras que la API backend (FastAPI) corre en Render. Anteriormente se presentaban problemas de CORS y la API estaba expuesta a ser consumida directamente desde herramientas como Postman sin control de origen.
El usuario requería que la API fuera restrictiva fuera de entornos de desarrollo local y pudiera coexistir con un proxy o dominio unificado en Cloudflare para evitar fricciones de CORS.

## Decisión
Se implementó una defensa en profundidad de 3 niveles:

1. **Nivel 1 - Verificación Estricta de Origen en Backend (FastAPI Middleware):**
   * Cuando `ENVIRONMENT == "production"` (o fuera de localhost), el middleware inspecciona las cabeceras `Origin` y `Sec-Fetch-Site`.
   * Solicitudes desde dominios no autorizados o sin origen válido en endpoints de mutación/consumo son rechazadas con `HTTP 403 Forbidden`.
   * En desarrollo (`ENVIRONMENT == "development"`), se permite el tráfico desde localhost y 127.0.0.1 para pruebas ágiles.

2. **Nivel 2 - Enrutamiento y Proxy de Origen Único (Cloudflare / Vercel Rewrites):**
   * Configuración de reescritura hacia `/api/*` que canaliza el tráfico bajo el mismo host (`same-origin`).
   * Elimina completamente la necesidad de preflights `OPTIONS` innecesarios y mitiga ataques de Cross-Origin Request Forgery.

3. **Nivel 3 - Protección contra Abuso y Privacidad PII:**
   * Almacenamiento seguro sin datos personales sensibles (PII): las direcciones IP remotas se anonimizan mediante hashing unidireccional `SHA-256` antes de ser almacenadas en telemetría o control de tasa (rate limiting).
   * Detección de bots automatizados mediante señuelos Honeypot en formularios frontend.
   * Límite de cuota estricto en recetas (15 por dispositivo) y feedbacks (2 por hora).

## Consecuencias
* **Positivas:**
  * Cero filtración de datos de usuario (cumplimiento de privacidad).
  * Consumo controlado de cuota de computo en Render.
  * Interfaz de usuario protegida contra scraping masivo no autorizado.
* **Negativas:**
  * Los clientes de pruebas manuales (ej. Postman) deben simular la cabecera `Origin` o correr contra el servidor local de desarrollo.

