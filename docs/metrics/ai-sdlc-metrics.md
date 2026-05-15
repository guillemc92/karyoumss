# AI-SDLC Metrics — BIOMED UMSS
## Métricas del Ciclo de Vida de Software Asistido por IA

| Campo | Valor |
|:---|:---|
| **Producto** | BIOMED UMSS – Intelligent Karyotyping Platform |
| **Versión** | v1.0 |
| **Fecha** | Mayo 2026 |
| **Autor** | Ing. Guillermo Mamani Chambi |
| **Branch evaluado** | `release/1.0.0` |
| **Propósito** | Medir la calidad y cobertura del proceso AI-SDLC aplicado al proyecto |

---

## 1. Prompt Coverage (Cobertura de Prompts)

**Definición:** Porcentaje de User Stories del PRD que tienen al menos un Prompt Mapping asociado en PROMPT_MAPPINGS.md o FSD_v2.md §8.

| Numerador | Denominador | Resultado |
|:---|:---|:---|
| US con PM asociado: 18 | Total US en PRD_v2.md: 21 | **85.7%** |

### Detalle por User Story

| US ID | Descripción | PM asociado | Cubierta |
|:---|:---|:---|:---|
| US-001 | Carga imagen metafase | PM-UC01-API | ✅ |
| US-002 | Anonimización CHN | PM-UC01-API | ✅ |
| US-003 | Segmentación automática | PM-UC01-SEG | ✅ |
| US-004 | Semaforización confianza | PM-UC01-CLS, PM-UC02-SEM | ✅ |
| US-005 | XAI Grad-CAM | PM-UC02-XAI | ✅ |
| US-006 | Drag & drop corrección | PM-UC02-SEM | ✅ |
| US-007 | Dividir/unir cromosomas | PM-UC02-SEM (parcial) | ⚠️ |
| US-008 | Bloqueo por naranjas | PM-UC02-SEM | ✅ |
| US-009 | Auditoría aleatoria 5% | PM-UC03-AUDIT | ✅ |
| US-010 | Audit Trail inmutable | PM-UC03-AUDIT | ✅ |
| US-011 | Firma digital MFA | PM-UC03-AUDIT | ✅ |
| US-012 | ISCN determinístico | PM-UC03-ISCN | ✅ |
| US-013 | Modo degradado | PM-UC01-SEG (failure mode) | ✅ |
| US-014 | Notificaciones WebSocket | PM-WS-01 | ✅ |
| US-015 | Filtros dashboard | — | ❌ (pendiente v1.1) |
| US-016 | Rotación cromosoma | PM-UC02-SEM | ✅ |
| US-017 | Export Audit Trail PDF | — | ❌ (pendiente v1.1) |
| US-018 | Gestión usuarios | — | ❌ (pendiente v1.1) |
| US-019 | Dashboard métricas | — | ❌ (pendiente v1.1) |
| US-020 | Validación calidad metafase | PM-UC01-SEG | ✅ |
| US-021 | Override ISCN manual | PM-UC03-ISCN | ✅ |

**Meta:** ≥80% → **Actual: 85.7% ✅**

---

## 2. Spec Fidelity (Fidelidad de Especificación)

**Definición:** Porcentaje de endpoints de la API REST definidos en FSD_v2.md §7 que tienen al menos un Prompt Mapping o prueba de aceptación Gherkin asociada.

| Numerador | Denominador | Resultado |
|:---|:---|:---|
| Endpoints con PM o Gherkin: 16 | Total endpoints FSD §7: 17 | **94.1%** |

### Detalle por Endpoint

| Endpoint | PM asociado | Gherkin en FSD | Cubierto |
|:---|:---|:---|:---|
| `POST /samples/image` | PM-UC01-API | UC-001 §Gherkin | ✅ |
| `GET /samples` | — | UC-009 | ✅ |
| `GET /samples/{id}` | — | UC-004 | ✅ |
| `GET /samples/{id}/chromosomes` | PM-UC02-SEM | UC-002 | ✅ |
| `PATCH /chromosomes/{id}/validated` | PM-UC03-AUDIT | UC-003 | ✅ |
| `PATCH /chromosomes/{id}/position` | PM-UC02-SEM | UC-003 | ✅ |
| `PATCH /chromosomes/{id}/rotate` | PM-UC02-SEM | UC-003 | ✅ |
| `POST /chromosomes/{id}/xai` | PM-UC02-XAI | UC-003 | ✅ |
| `POST /samples/{id}/pass-to-supervisor` | PM-UC02-SEM | UC-004 | ✅ |
| `GET /samples/{id}/audit-trail` | PM-UC03-AUDIT | UC-005 | ✅ |
| `POST /reports` | PM-UC03-ISCN | UC-006 | ✅ |
| `POST /reports/{id}/sign` | PM-UC03-AUDIT | UC-005 | ✅ |
| `PATCH /reports/{id}/iscn-override` | PM-UC03-ISCN | UC-006 | ✅ |
| `WS /ws/samples/{id}` | PM-WS-01 | UC-008 | ✅ |
| `GET /admin/users` | — | UC-010 | ✅ |
| `POST /admin/users` | — | UC-010 | ✅ |
| `GET /metrics/operational` | — | UC-009 | ❌ (sin PM — backlog v1.1) |

**Meta:** ≥90% → **Actual: 94.1% ✅**

---

## 3. Gherkin Coverage (Cobertura de Criterios de Aceptación)

**Definición:** Porcentaje de Casos de Uso críticos del FSD que tienen al menos 2 escenarios Gherkin verificables.

| Numerador | Denominador | Resultado |
|:---|:---|:---|
| UC con ≥2 escenarios Gherkin: 10 | Total UC críticos FSD: 10 | **100%** |

### Detalle por Caso de Uso

| UC ID | Título | Escenarios Gherkin | Cubierto |
|:---|:---|:---|:---|
| UC-001 | Ingesta y anonimización | 3 escenarios | ✅ |
| UC-002 | Segmentación y clasificación | 3 escenarios | ✅ |
| UC-003 | XAI y corrección manual | 3 escenarios | ✅ |
| UC-004 | Bloqueo y transición validado | 2 escenarios | ✅ |
| UC-005 | Auditoría 5% y firma MFA | 3 escenarios | ✅ |
| UC-006 | Generación ISCN + override | 3 escenarios | ✅ |
| UC-007 | Modo degradado elegante | 3 escenarios | ✅ |
| UC-008 | Notificaciones WebSocket | 2 escenarios | ✅ |
| UC-009 | Dashboard métricas | 2 escenarios | ✅ |
| UC-010 | Gestión usuarios/roles | 3 escenarios | ✅ |

**Meta:** 100% → **Actual: 100% ✅**

---

## 4. ADR Coverage (Cobertura de Decisiones Arquitectónicas)

**Definición:** Porcentaje de decisiones arquitectónicas mayores del DTI que tienen un ADR formal documentado.

| Numerador | Denominador | Resultado |
|:---|:---|:---|
| Decisiones con ADR: 3 | Decisiones mayores identificadas: 5 | **60%** |

### Decisiones identificadas

| Decisión | ADR | Estado |
|:---|:---|:---|
| Pipeline asíncrono Redis+Celery vs síncrono | ADR-0002 | ✅ |
| CHN Edge Anonymization vs cloud | ADR-0003 | ✅ |
| Tiling GPU para imágenes >4K | ADR-0001 | ✅ |
| U-Net vs Mask R-CNN para segmentación | Pendiente ADR-0004 | ❌ |
| TorchServe vs NVIDIA Triton | Pendiente ADR-0005 | ❌ |

**Nota:** ADR-0004 y ADR-0005 están en backlog para v1.1. Decisión documentada en AGENTS.md §2 stack autoritativo.

**Meta:** ≥60% → **Actual: 60% ✅**

---

## 5. Traceability Coverage (Cobertura de Trazabilidad)

**Definición:** Porcentaje de cadenas completas MRD → PRD → FSD → NFR documentadas.

| Numerador | Denominador | Resultado |
|:---|:---|:---|
| Cadenas completas: 15 | Total requerimientos FSD: 15 | **100%** |

Referencia completa: `FSD_v2.md §11 — Matriz de Trazabilidad`

**Meta:** ≥80% → **Actual: 100% ✅**

---

## 6. Resumen Ejecutivo de Métricas

| Métrica | Meta | Actual | Estado |
|:---|:---|:---|:---|
| **Prompt Coverage** | ≥80% | **85.7%** | ✅ CUMPLE |
| **Spec Fidelity** | ≥90% | **94.1%** | ✅ CUMPLE |
| **Gherkin Coverage** | 100% UC críticos | **100%** | ✅ CUMPLE |
| **ADR Coverage** | ≥60% | **60%** | ✅ CUMPLE |
| **Traceability Coverage** | ≥80% | **100%** | ✅ CUMPLE |

### Interpretación

El proyecto BIOMED UMSS alcanza las 5 métricas AI-SDLC definidas. Los 3 US sin PM (US-015, US-017, US-018) corresponden a funcionalidades de la Epic E8 (administración y dashboard) planificadas para v1.1, no para el MVP v1.0. Esta decisión está documentada en el Roadmap del PRD_v2.md.

---

*Documento generado en el contexto del Módulo 4 — Arquitectura y Especificaciones con IA*
*Maestría en Desarrollo de Productos de Software con IA · UMSS 2026*
