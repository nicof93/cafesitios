# ADR 0002: Adopción de Spec-Driven Development (SDD) para Agentes de IA

## Estado
Aceptado

## Fecha
2026-10-08

## Contexto
El desarrollo de software asistido por múltiples agentes de IA y humanos requiere sincronización precisa sobre los casos de uso, restricciones técnicas y dependencias del sistema.
Sin un estándar documental versionado, los agentes corren el riesgo de:
1. Re-leer o re-escribir archivos innecesarios consumiendo tokens en exceso.
2. Proponer librerías incompatibles o no autorizadas en `requirements.txt`.
3. Introducir inconsistencias en las reglas de negocio (ej. cómo calcular $/kg o manejar fallbacks).

## Decisión
Se establece el marco **Spec-Driven Development (SDD)** en el repositorio `cafe-sitios`:

1. **Estructura `specs/`:**
   * Cada funcionalidad o caso de uso cuenta con una especificación canónica numerada (`specs/00X-nombre/spec.md`).
   * Toda especificación contiene frontmatter con su estado (`draft`, `in-progress`, `accepted`, `superseded`) y fecha de actualización.
   * Define contratos claros: Reglas de Negocio (RN), esquemas Pydantic v2, endpoints HTTP y criterios de aceptación.

2. **Protocolo Operativo de Agentes (`AGENTS.md`):**
   * Edición quirúrgica y lectura focalizada.
   * Ejecución exclusiva de tests puntuales relacionados con el cambio antes de confirmar.
   * Prohibición estricta de instalar paquetes adicionales no declarados en el stack base.

3. **Arquitectura Limpia / DDD Simplificado:**
   * Las entidades y reglas nucleares residen en `domain/` con CERO dependencias externas.
   * Los casos de uso en `application/` orquestan la lógica sin detalles de infraestructura.
   * `infrastructure/` implementa persistencia y adaptadores.
   * `api/` gestiona las rutas FastAPI y serialización Pydantic v2.

## Consecuencias
* **Positivas:**
  * Cualquier nuevo agente o desarrollador puede retomar el trabajo entendiendo el contexto en segundos.
  * Trazabilidad completa entre requerimientos (`requerimientos-cafesitios-mvp.md`), especificaciones (`specs/`) y suites de prueba (`tests/`).
* **Negativas:**
  * Cada nueva funcionalidad requiere redactar o actualizar su documento en `specs/` antes de considerarse completa.

