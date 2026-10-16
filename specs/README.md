# Marco de Desarrollo Guiado por Especificaciones (Spec-Driven Development)

Este directorio alberga las especificaciones ejecutables y contratos de requerimientos de **Cafe-sitios**.
Cada funcionalidad o cambio significativo debe contar con un documento en esta carpeta antes o durante su implementación para que tanto desarrolladores humanos como agentes de IA puedan colaborar con precisión matemática y sin ambigüedades.

---

## 1. Convención de Nomenclatura y Estados

Cada especificación se ubica en su propia subcarpeta:
```
specs/
├── README.md
├── template.md
├── 001-busqueda-sinonimos/spec.md
├── 002-precio-kilo-estimado/spec.md
├── 003-comparador-side-by-side/spec.md
├── 004-identidad-y-sustitutos/spec.md
├── 005-geolocalizacion-tiendas/spec.md
├── 006-quiz-sabor/spec.md
├── 007-bitacora-recetas-local-first/spec.md
├── 008-feedback-anonimo/spec.md
└── 009-refactor-ui-ux/spec.md
```

### Ciclo de Vida de una Spec
* **Draft**: En definición de reglas y contratos.
* **In-Progress**: En proceso activo de codificación o pruebas.
* **Accepted / Implemented**: Implementada en producción con suite de pruebas pasando.
* **Deprecated / Superseded**: Reemplazada por una nueva especificación.

---

## 2. Reglas para Agentes de IA

1. **Lectura Obligatoria:** Antes de modificar un módulo del dominio o endpoint, el agente debe consultar la especificación correspondiente en `specs/`.
2. **Cero Dependencias No Autorizadas:** Cumplir siempre con las dependencias fijadas en `AGENTS.md`.
3. **Pruebas de Regresión:** Toda regla de negocio (RN) enunciada en una spec debe tener un test asociado en `tests/`.
4. **Actualización de Estado:** Al finalizar la implementación, el agente debe cambiar el estado en el frontmatter del documento a `Accepted`.

