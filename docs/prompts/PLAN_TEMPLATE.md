# /plan — BIOMED UMSS

## 🎯 Objetivo
Descomponer la especificación técnica del sistema de Cariotipado Inteligente (BIOMED UMSS) en tareas implementables, granulares y testeables, asegurando la trazabilidad con los requerimientos funcionales y las restricciones clínicas.

---

## Output esperado

| Task ID | Descripción | Tipo | Prioridad |
| :--- | :--- | :--- | :--- |
| **T-01.1** | Setup Docker Compose (FastAPI, PG, Redis) | Infra | P0 |
| **T-01.2** | Scaffold React + Vite + Zustand | Infra | P0 |
| **T-02.1** | Implementación esquema DB `samples` y `users` | DB | P0 |
| **T-02.2** | Implementación esquema DB `chromosomes` y `edits` | DB | P0 |
| **T-02.3** | Implementación esquema DB `reports` | DB | P1 |
| **T-03.1** | Servicio de generación de código CHN (único) | Backend | P0 |
| **T-03.2** | Endpoint `POST /samples` (Registro básico) | Backend | P0 |
| **T-03.3** | Integración `POST /samples` $\to$ `chn_service` | Backend | P0 |
| **T-04.1** | Integración S3/MinIO Client | Backend | P0 |
| **T-04.2** | Endpoint `POST /samples/{id}/image` | Backend | P0 |
| **T-05.1** | Celery Worker: Consumo de cola Redis | Backend | P0 |
| **T-05.2** | Pipeline: Pre-procesamiento CLAHE | AI | P1 |
| **T-05.3** | Pipeline: Tiling 1024x1024 + overlap 64px | AI | P1 |
| **T-05.4** | Integración TorchServe $\to$ U-Net (Segmentación) | AI | P0 |
| **T-05.5** | Implementación de lógica de reintentos en Celery | Backend | P1 |
| **T-06.1** | Integración TorchServe $\to$ EfficientNet-B3 (Clasificación) | AI | P0 |
| **T-06.2** | Lógica de ensamblado de tiles y NMS | AI | P1 |
| **T-06.3** | Persistencia de 46 cromosomas en DB | Backend | P0 |
| **T-07.1** | Backend: WebSocket Event Publisher | Backend | P1 |
| **T-07.2** | Frontend: WebSocket Client listener | Frontend | P1 |
| **T-08.1** | Konva.js: Renderizado básico de cromosomas | Frontend | P0 |
| **T-08.2** | Implementación de Semaforización Visual | Frontend | P0 |
| **T-09.1** | Panel de revisión: Lista ordenada por score $\uparrow$ | Frontend | P1 |
| **T-09.2** | Interacción: Click en lista $\to$ Resaltado en Canvas | Frontend | P2 |
| **T-10.1** | Implementación Drag & Drop y Rotación en Konva | Frontend | P1 |
| **T-10.2** | Endpoint `PATCH /chromosomes/{id}/position` | Backend | P1 |
| **T-10.3** | Implementación de Reclasificación manual de pares | Frontend | P1 |
| **T-11.1** | Marcado de validación `PATCH /chromosomes/{id}/validated` | Backend | P0 |
| **T-11.2** | Lógica de desbloqueo de informe (Check $\text{all\_validated}$) | Backend | P0 |
| **T-12.1** | Motor de generación de nomenclatura ISCN 2020 | Backend | P1 |
| **T-12.2** | Endpoint `POST /reports` (Creación de borrador) | Backend | P1 |
| **T-13.1** | Notificación de firma al Supervisor | Backend | P2 |
| **T-13.2** | Panel de Auditoría: Visualización de `EditTrail` | Frontend | P1 |
| **T-13.3** | Endpoint `POST /reports/{id}/sign` | Backend | P0 |
| **T-14.1** | Integración HL7 FHIR para envío de informe | Backend | P2 |
| **T-15.1** | Test de integración E2E (Pipeline completo) | QA | P1 |
| **T-15.2** | Validación de Performance SLA (p95 $\le 15\text{s}$) | QA | P1 |

---

## Reglas
- Tareas pequeñas (máximo 2-3 horas)
- Máxima 1 responsabilidad por tarea
- Deben ser testeables (criterios de aceptación claros)
- Deben mantener trazabilidad con los requisitos (FSD/BRD)