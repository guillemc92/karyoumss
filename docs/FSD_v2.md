# Functional Specification Document (FSD) — BIOMED UMSS
## Intelligent Karyotyping Platform

**Propósito:** Describir **cómo** el sistema implementa los requisitos del PRD v2.0, con nivel técnico suficiente para que ingeniería, QA y arquitectura puedan construir, probar y desplegar.

| Campo | Valor |
|:---|:---|
| **Producto** | BIOMED UMSS – Intelligent Karyotyping Platform |
| **Grupo** | G04 |
| **Versión** | v2.0 (Excelente — 10 UC + 30+ elementos + API contracts) |
| **Fecha** | Mayo 2026 |
| **Autores** | Ing. Guillermo Mamani Chambi |
| **Revisores** | Docente + 1 grupo par |
| **Estado** | Aprobado |
| **Modo** | FSD Clásico 🔧 |
| **Trazabilidad PRD** | PRD v2.0 |
| **Trazabilidad BRD** | BRD v3.5 |
| **Prototipo** | https://guillemc92.github.io/karyoumss/ |
| **Fase Spec Kit** | Specify ✅ / Plan ✅ / Tasks ⬜ / Implement ⬜ |

---

## §1. Resumen Ejecutivo

BIOMED UMSS es una plataforma web de inteligencia aumentada para análisis citogenético. Recibe imágenes de metafase (TIFF/PNG/JPEG), las anonimiza localmente con código CHN, y ejecuta un pipeline de visión computacional que segmenta (U-Net) y clasifica (EfficientNet-B3) los 46 cromosomas. Cada cromosoma recibe un confidence score Softmax. La interfaz semaforiza en verde (≥85%) y naranja (<85%). El Analista corrige los cromosomas naranja mediante XAI Grad-CAM y herramientas drag & drop. El Supervisor audita el 5% aleatorio de cromosomas verdes y firma con MFA. El motor determinístico genera la nomenclatura ISCN 2024. El sistema opera en modo degradado manual si la IA falla. Valor diferencial: TTK de 45 → 15 minutos con trazabilidad total (21 CFR Part 11).

---

## §2. Alcance y Plan Técnico

### 2.1 Dentro del alcance

- Ingesta de imágenes con validación de formato, tamaño e integridad
- Anonimización local CHN (formato `CHN-YYYY-MM-DD-NNNN`)
- Segmentación automática (U-Net) y clasificación (EfficientNet-B3)
- Semaforización por umbral 85% (verde/naranja)
- XAI con mapas de calor Grad-CAM y log obligatorio `XAI_VIEWED`
- Corrección manual: drag & drop, dividir, unir, rotar, eliminar artefactos
- Bloqueo de emisión de reporte si hay naranjas sin resolver
- Auditoría aleatoria del 5% de cromosomas con confianza >86%
- Audit Trail inmutable con hash chain SHA256 (cumplimiento 21 CFR Part 11)
- Segregación de roles (Analista, Supervisor, Administrador)
- Firma digital con MFA obligatorio (TOTP/huella/tarjeta)
- Generación determinística de ISCN con override manual supervisado
- Modo degradado elegante (manual puro si IA falla)
- Exportación a PDF con nota al pie en overrides manuales
- Validación de calidad de metafase (detección de superposición >30%)
- Dashboard de métricas operativas (TTK, throughput, errores)
- Gestión de usuarios y roles por Administrador
- Notificaciones en tiempo real vía WebSocket

### 2.2 Fuera del alcance (v1.0)

- Integración HL7 FHIR con LIS Hospitalario (v1.1)
- Importación DICOM (v1.2)
- Diagnóstico autónomo sin revisión humana (prohibido por BRD)
- Secuenciación NGS o microarrays CMA
- Aplicación nativa móvil (iOS/Android)
- Captura directa desde microscopio por hardware

### 2.3 Plan Técnico (Spec Kit — fase Plan)

| Bloque | Contenido |
|:---|:---|
| **Stack Backend** | Python 3.11 + FastAPI + PyTorch 2.0 + PostgreSQL 15 + Redis 7 |
| **Stack Frontend** | React 18 + TypeScript + Vite + Zustand + Konva.js + TailwindCSS |
| **IA / ML** | U-Net (segmentación) + EfficientNet-B3 (clasificación) + Grad-CAM (XAI) |
| **Serving** | TorchServe 0.12+ / NVIDIA Triton (GPU T4 o superior) |
| **Storage** | MinIO/S3 (imágenes) + PostgreSQL (metadatos + audit trail) |
| **Arquitectura** | Hexagonal (puertos y adaptadores): API → Aplicación → Dominio → Infraestructura |
| **Infra** | Docker + Docker Compose, escalado horizontal con `celery_worker=N` |
| **Decisiones ADR** | ADR-0001 Tiling, ADR-0002 Async Pipeline, ADR-0003 CHN Edge Anonymization |
| **Restricciones** | PII nunca sale del nodo institucional · Modo degradado sin conexión IA |

### 2.4 Descomposición en Tasks (Spec Kit)

| Task ID | Descripción | UC | Dependencia | Prompt ID | Estado |
|:---|:---|:---|:---|:---|:---|
| T-001 | `POST /samples/image` con validación + CHN Anonymizer + S3 | UC-001 | — | PM-UC01-API | pendiente |
| T-002 | Pipeline U-Net: CLAHE + tiling 1024×1024 + NMS | UC-002 | T-001 | PM-UC01-SEG | pendiente |
| T-003 | Pipeline EfficientNet-B3: clasificación batch×16 + Softmax | UC-002 | T-002 | PM-UC01-CLS | pendiente |
| T-004 | Grad-CAM XAI + log `XAI_VIEWED` en audit trail | UC-003 | T-003 | PM-UC02-SEM | pendiente |
| T-005 | UI semaforización verde/naranja + bloqueo botón (Konva.js + Zustand) | UC-002, UC-004 | T-003 | PM-UC02-SEM | pendiente |
| T-006 | Herramientas edición: drag & drop, dividir, unir, rotar | UC-003 | T-005 | PM-UC02-SEM | pendiente |
| T-007 | Auditoría aleatoria 5% (seed reproducible SHA256) | UC-005 | T-005 | PM-UC03-AUDIT | pendiente |
| T-008 | Audit Trail inmutable hash chain SHA256 + REVOKE UPDATE/DELETE | UC-005 | T-001 | PM-UC03-AUDIT | pendiente |
| T-009 | Firma digital MFA + override ISCN manual | UC-006 | T-007, T-008 | PM-UC03-ISCN | pendiente |
| T-010 | Modo degradado elegante (manual puro sin IA) | UC-007 | T-005 | PM-UC01-API | pendiente |
| T-011 | WebSocket push notification + Redis PubSub | UC-008 | T-001 | PM-WS-01 | pendiente |
| T-012 | Dashboard métricas + gestión usuarios admin | UC-009, UC-010 | T-001 | — | pendiente |

---

## §3. Actores y Roles del Sistema

| Actor | Tipo | Responsabilidad | Permisos clave |
|:---|:---|:---|:---|
| **Analista Citogenetista** | Humano | Cargar imágenes, revisar cromosomas naranja, corregir IA, pasar caso | `case:upload`, `case:edit`, `case:pass_to_supervisor` |
| **Supervisor** | Humano | Auditar casos, revisar 5% aleatorio, firmar con MFA, override ISCN | `case:audit`, `case:sign`, `case:override_iscn` |
| **Administrador** | Humano | Gestionar usuarios, roles, configuración del sistema, métricas | `admin:*` |
| **Sistema IA** | Agente IA | Segmentar, clasificar, generar confidence scores, XAI Grad-CAM | `ml:inference`, `ml:explain` |
| **Audit Trail** | Sistema | Registrar acciones inmutables, generar hash chain, verificar integridad | `audit:write`, `audit:read`, `audit:verify` |

---

## §4. Casos de Uso Funcionales

> **10 casos de uso críticos documentados** — cumple criterio Excelente de la rúbrica.

---

### FSD-UC-001 — Ingesta y Anonimización de Imagen

**Trazabilidad:** PRD-US-001, PRD-US-002, PRD-REQ-001 · **Actor:** Analista

**Precondiciones:** Analista autenticado · Imagen TIFF/PNG/JPEG disponible (<50MB)

**Disparador:** Analista hace clic en "Cargar imagen" y selecciona archivo

**Flujo principal:**
1. Sistema valida formato (TIFF/PNG/JPEG), tamaño (<50MB) e integridad (checksum MD5)
2. Sistema evalúa calidad de metafase: calcula índice de superposición (overlap index)
3. Si overlap >30% → marca `quality_flag: HIGH_OVERLAP` (advertencia, no bloqueo)
4. Sistema genera código CHN único: `CHN-YYYY-MM-DD-NNNN` con verificación de unicidad en DB
5. Sistema elimina todos los metadatos EXIF/DICOM con PII de la imagen
6. Sistema almacena mapeo CHN en vault cifrado local (nunca sube a la nube)
7. Sistema sube imagen anonimizada a S3 path: `{chn_code}/{timestamp}.tiff`
8. Sistema crea registro en `samples` (status=queued) y encola tarea en Redis
9. FastAPI retorna `202 Accepted` con `{sample_id, chn_code, task_id}`

**Flujos alternativos:**
- `A1`: Archivo corrupto → rechaza, "El archivo está dañado o incompleto"
- `A2`: Formato no soportado → rechaza, "Use TIFF, PNG o JPEG"
- `A3`: Tamaño >50MB → rechaza, "Imagen demasiado grande (máx 50MB)"
- `A4`: CHN colisión → sistema reintenta con NNNN+1 automáticamente (hasta 3 reintentos)

**Postcondiciones:** Imagen anonimizada en S3 · Caso creado en `status=queued` · Audit Trail: `CASE_CREATED` + `ANONYMIZATION_COMPLETED`

**Reglas aplicables:** BR-001 (CHN obligatorio)

**Datos de entrada:**
```json
{ "file": "multipart/form-data (TIFF/PNG/JPEG)", "hospital_code": "string (opcional)" }
```

**Datos de salida:**
```json
{ "sample_id": "uuid", "chn_code": "CHN-2026-05-13-0001", "status": "queued", "task_id": "uuid", "quality_flags": [] }
```

**Criterios Gherkin:**
```gherkin
Scenario: Carga exitosa de imagen válida
  Given un Analista autenticado en el sistema
  When selecciona una imagen TIFF válida de 15MB
  Then el sistema genera un código CHN en menos de 2 segundos
  And la imagen se almacena sin metadatos PII
  And retorna sample_id, chn_code y task_id con status 202

Scenario: Rechazo por archivo corrupto
  Given un Analista autenticado
  When selecciona un archivo TIFF corrupto
  Then el sistema rechaza la carga con código 422
  And muestra "El archivo está dañado o incompleto"
  And no crea ningún caso en el sistema

Scenario: Advertencia por alta superposición
  Given una imagen de metafase con cromosomas superpuestos >30%
  When el sistema evalúa la calidad
  Then procesa la imagen normalmente
  And agrega quality_flag HIGH_OVERLAP al caso
  And muestra banner amarillo de advertencia al Analista
```

---

### FSD-UC-002 — Segmentación, Clasificación y Semaforización

**Trazabilidad:** PRD-US-003, PRD-US-004, PRD-REQ-002, PRD-REQ-003, PRD-REQ-004 · **Actor:** Sistema IA (automático)

**Precondiciones:** Caso en `status=queued` · Imagen anonimizada disponible en S3

**Disparador:** Celery Worker consume tarea de Redis queue

**Flujo principal:**
1. Worker descarga imagen de S3 por `chn_code` (nunca por PII)
2. Aplica CLAHE (clipLimit=3.0, tileGridSize=8×8) para realzar bandas G
3. Si imagen >4000px: divide en tiles 1024×1024 con overlap 64px (tiling strategy)
4. Ejecuta U-Net → detecta cromosomas, genera polígonos y bounding boxes
5. Aplica Non-Maximum Suppression (NMS) para eliminar duplicados en bordes de tiles
6. Verifica conteo: si <40 o >55 cromosomas → `quality_flag: ABNORMAL_COUNT`
7. Extrae crops 224×224 de cada cromosoma detectado
8. Ejecuta EfficientNet-B3 en batch de 16 → `{pair_number, confidence_score}` por cromosoma
9. Asigna semáforo: verde si score ≥0.85, naranja si score <0.85
10. Persiste 46 cromosomas en PostgreSQL con polygon_coords, score, requires_review
11. Actualiza `samples.status` → `ready`
12. Publica en Redis PubSub → WebSocket push "Borrador listo 🔔" al cliente

**Flujos alternativos:**
- `A1`: TorchServe timeout (>10s) × 3 → activa UC-007 (modo degradado)
- `A2`: Conteo anormal (<40 o >55) → marca `ABNORMAL_COUNT`, prioriza revisión manual

**Postcondiciones:** 46 cromosomas en DB con score y semáforo · `status=ready` · Audit Trail: `SEGMENTATION_COMPLETED` + `CLASSIFICATION_COMPLETED`

**Reglas aplicables:** BR-002 (semaforización), BR-003 (bloqueo)

**Datos de salida:**
```json
{
  "chromosomes": [
    {"id": "uuid", "pair_number": 21, "confidence_score": 0.94, "requires_review": false, "polygon_coords": [[x,y],...], "color": "green"},
    {"id": "uuid", "pair_number": 14, "confidence_score": 0.78, "requires_review": true, "color": "orange"}
  ],
  "quality_flags": [],
  "inference_time_ms": 8200
}
```

**Criterios Gherkin:**
```gherkin
Scenario: Procesamiento exitoso de metafase estándar
  Given una imagen de metafase anonimizada en S3
  When el pipeline IA completa el procesamiento
  Then detecta y persiste 46 cromosomas en la base de datos
  And cada cromosoma tiene confidence_score entre 0.000 y 1.000
  And el tiempo de inferencia total es menor a 15 segundos en GPU
  And la precisión de segmentación IoU es mayor a 0.90

Scenario: Cromosoma con baja confianza se marca naranja
  Given un cromosoma clasificado con confidence_score 0.78
  When se renderiza el cariotipo en la UI
  Then el cromosoma muestra borde naranja grueso
  And aparece en la lista de revisión priorizada
  And el botón Pasar a Supervisor está inhabilitado

Scenario: Notificación en tiempo real al completar
  Given un Analista esperando el resultado de su muestra
  When el pipeline IA completa el procesamiento
  Then el sistema envía notificación WebSocket en menos de 500ms
  And el Analista recibe badge de notificación en la UI sin refrescar la página
```

---

### FSD-UC-003 — XAI Grad-CAM y Corrección Manual

**Trazabilidad:** PRD-US-005, PRD-US-006, PRD-US-007, PRD-US-016 · **Actor:** Analista

**Precondiciones:** Caso con al menos un cromosoma naranja · Analista en mesa de edición

**Disparador:** Analista hace clic en cromosoma naranja o activa herramienta de edición

**Flujo principal (XAI Grad-CAM):**
1. Analista hace clic en ícono "¿Por qué?" de un cromosoma naranja
2. Sistema recupera logits almacenados del modelo EfficientNet-B3
3. Ejecuta Grad-CAM: calcula gradientes respecto a la última capa convolucional
4. Genera mapa de calor superpuesto (opacidad 0.5) sobre el crop del cromosoma
5. Identifica región de máxima intensidad → mapea a banda cromosómica (lookup table bandas G)
6. Muestra modal con heatmap + tooltip: "La IA se basó en la banda q22.3 para esta clasificación"
7. Registra `XAI_VIEWED` en Audit Trail: `{chromosome_id, analyst_id, timestamp, confidence_pre_xai}`

**Flujo principal (corrección drag & drop):**
1. Analista selecciona cromosoma (naranja o verde)
2. Arrastra hacia slot del cariograma (1–22, X, Y, o basurero)
3. UI muestra preview visual durante arrastre (snapping con animación 60fps)
4. Al soltar: sistema actualiza `pair_number` al nuevo slot
5. Cromosoma naranja resuelto → `resolution_status = RESOLVED`
6. Audit Trail: `CORREGIR_CLASE {original_class, new_class, analyst_id, timestamp}`
7. Si era el último naranja → sistema activa UC-004 (transición a validado)

**Flujo principal (rotación):**
1. Analista selecciona cromosoma y hace clic en "Rotar 90°"
2. Cromosoma rota 90° en sentido horario manteniendo posición
3. Si era naranja → sistema ejecuta reclasificación automática post-rotación
4. Audit Trail: `ROTAR_90 {chromosome_id, analyst_id}`
5. Analista puede deshacer (Ctrl+Z) dentro de la sesión activa

**Flujos alternativos:**
- `A1`: Analista intenta resolver naranja sin abrir XAI → bloqueo, "Debe consultar XAI antes de resolver"
- `A2`: Herramienta dividir → Analista traza línea, sistema separa máscaras y reclasifica ambas partes
- `A3`: Herramienta unir → selecciona dos fragmentos, sistema combina máscaras y reclasifica

**Postcondiciones:** Corrección en Audit Trail · Si último naranja → estado transiciona en UC-004

**Reglas aplicables:** BR-004 (XAI obligatorio antes de resolver)

**Criterios Gherkin:**
```gherkin
Scenario: XAI requerido antes de resolver naranja
  Given un Analista viendo un cromosoma con borde naranja
  When intenta arrastrarlo sin haber consultado XAI
  Then el sistema bloquea la acción
  And muestra "Debe consultar el mapa de calor (XAI) antes de resolver este cromosoma"

Scenario: Visualización de Grad-CAM exitosa
  Given un Analista que hace clic en el ícono XAI de un cromosoma naranja
  When el sistema genera el mapa de calor
  Then muestra el heatmap superpuesto en menos de 1 segundo
  And registra XAI_VIEWED en el Audit Trail
  And ahora el Analista puede resolver el cromosoma

Scenario: Drag and drop de corrección
  Given un Analista en modo de edición con XAI ya consultado
  When arrastra el cromosoma al slot del Par 21
  Then el cromosoma se reubica en menos de 500ms
  And el sistema registra CORREGIR_CLASE en Audit Trail con clase original y nueva
  And si era el último naranja, habilita el botón Pasar a Supervisor
```

---

### FSD-UC-004 — Bloqueo y Transición a Validado por Analista

**Trazabilidad:** PRD-US-008, PRD-REQ-005 · **Actor:** Analista + Sistema

**Precondiciones:** Caso con cromosomas resueltos progresivamente

**Disparador:** Sistema detecta que `unresolved_orange_count == 0`

**Flujo principal:**
1. Sistema verifica en tiempo real: `SELECT COUNT(*) FROM chromosomes WHERE sample_id=X AND requires_review=TRUE AND resolution_status='PENDING'`
2. Si count == 0 → sistema cambia `samples.status` → `pending_validation`
3. Sistema habilita botón "Pasar a Supervisor" en UI
4. Analista hace clic en "Pasar a Supervisor"
5. Sistema cambia `status` → `pending_supervisor`
6. Audit Trail: `ANALYST_VALIDATED {time_in_blocked_state_seconds, total_corrections}`

**Flujos alternativos:**
- `A1`: Analista presiona botón inhabilitado → tooltip "Resuelva X cromosomas naranja antes de continuar"

**Postcondiciones:** Caso en `status=pending_supervisor` · Supervisor notificado

**Criterios Gherkin:**
```gherkin
Scenario: Desbloqueo automático tras resolver todos los naranjas
  Given un caso con 3 cromosomas naranja
  When el Analista resuelve el último cromosoma naranja
  Then el sistema cambia el estado a pending_validation en menos de 1 segundo
  And el botón Pasar a Supervisor se habilita automáticamente
  And Audit Trail registra ANALYST_VALIDATED con tiempo total de revisión

Scenario: Bloqueo cuando hay naranjas pendientes
  Given un caso con al menos un cromosoma naranja sin resolver
  When el Analista intenta hacer clic en Pasar a Supervisor
  Then el botón está inhabilitado visualmente (disabled + cursor not-allowed)
  And muestra contador "3 cromosomas naranja pendientes de revisión"
```

---

### FSD-UC-005 — Auditoría Aleatoria 5% y Firma con MFA

**Trazabilidad:** PRD-US-009, PRD-US-010, PRD-US-011 · **Actor:** Supervisor

**Precondiciones:** Caso en `status=pending_supervisor` · Supervisor autenticado

**Disparador:** Supervisor abre caso desde bandeja de auditoría

**Flujo principal (auditoría aleatoria):**
1. Sistema filtra cromosomas con `confidence_score > 0.86`
2. Calcula seed reproducible: `SHA256(case_id + "audit_salt_v1") % (2^32)`
3. Inicializa PRNG con seed → selecciona `max(1, floor(len * 0.05))` cromosomas
4. Marca seleccionados con `random_audit_flag = true` y badge púrpura en UI
5. Supervisor revisa cada cromosoma auditado (comparando con ideograma de referencia)
6. Para cada uno: "Confirmado" (acepta IA) o "Rechazado" (devuelve con comentario)
7. Si rechazado → cromosoma vuelve a `requires_review=TRUE` → caso retrocede a Analista
8. Audit Trail: `AUDIT_DECISION {chromosome_id, decision, comment, supervisor_id}`

**Flujo principal (firma con MFA):**
1. Supervisor completa revisión de todos los cromosomas auditados
2. Hace clic en "Firmar Reporte"
3. Sistema solicita MFA (TOTP / huella digital / tarjeta inteligente)
4. Supervisor completa MFA en <90 segundos
5. Sistema valida token MFA
6. Sistema invoca UC-006 (generación ISCN)
7. Audit Trail: `SIGN_REPORT {mfa_method, mfa_token_hash, supervisor_id, timestamp}`
8. `samples.status` → `emitido`

**Flujos alternativos:**
- `A1`: Supervisor intenta firmar sin revisar auditoría → bloqueo, "Debe revisar X cromosomas de auditoría"
- `A2`: MFA falla 3 veces → bloqueo 15 minutos + evento de seguridad en Audit Trail

**Postcondiciones:** Informe firmado digitalmente · Audit Trail completo con hash chain

**Criterios Gherkin:**
```gherkin
Scenario: Selección reproducible del 5% para auditoría
  Given un caso validado con 46 cromosomas y 40 con confidence >0.86
  When el Supervisor abre el caso
  Then el sistema selecciona exactamente 2 cromosomas (5% de 40)
  And los marca con badge púrpura Auditoría requerida
  And si el Supervisor abre el mismo caso nuevamente, selecciona los mismos cromosomas

Scenario: Firma exitosa con MFA TOTP
  Given un Supervisor que ha completado toda la revisión del caso
  When hace clic en Firmar Reporte y completa el código TOTP
  Then el sistema registra la firma en menos de 2 segundos
  And cambia el estado del caso a emitido
  And Audit Trail incluye SIGN_REPORT con método MFA y hash del token

Scenario: Bloqueo por MFA fallido 3 veces
  Given un Supervisor que ingresa 3 códigos TOTP incorrectos consecutivos
  When intenta el cuarto intento
  Then el sistema bloquea la firma por 15 minutos
  And registra SECURITY_EVENT_MFA_BLOCK en Audit Trail
  And envía alerta al Administrador del sistema
```

---

### FSD-UC-006 — Generación de Reporte ISCN con Override Manual

**Trazabilidad:** PRD-US-012, PRD-US-021, PRD-REQ-011 · **Actor:** Supervisor + Sistema

**Precondiciones:** Caso firmado con MFA (tras UC-005)

**Disparador:** Evento `REPORT_GENERATION` tras firma exitosa

**Flujo principal (automático):**
1. Sistema cuenta cromosomas por clase final (incluyendo correcciones manuales)
2. Aplica reglas determinísticas ISCN 2024:
   - Cuenta total de cromosomas (target: 46 para normal)
   - Determina sexo: XX o XY según cromosomas 23 y 24
   - Orden ascendente de anomalías numéricas (+18 antes que +21)
   - Anomalías estructurales en orden de cromosoma afectado
3. Genera string ISCN: "46,XY" (normal) / "47,XY,+21" (trisomía 21)
4. Sistema muestra ISCN en pantalla de resumen para revisión del Supervisor

**Flujo principal (override manual):**
1. Supervisor identifica anomalía compleja no capturada por motor ISCN
2. Hace clic en "Override manual de ISCN"
3. Sistema habilita campo de texto editable con validación de gramática ISCN
4. Supervisor ingresa string corregido + nota de justificación (mínimo 50 caracteres)
5. Sistema valida gramática ISCN 2024 básica → alerta roja si inválida
6. Supervisor confirma con MFA adicional
7. Audit Trail: `ISCN_OVERRIDE {original_iscn, final_iscn, justification, supervisor_id}`
8. PDF incluye nota al pie: "* Nomenclatura editada manualmente. Ver Audit Trail."

**Postcondiciones:** PDF generado y almacenado · ISCN final registrado · `status=reportado`

**Criterios Gherkin:**
```gherkin
Scenario: Generación automática de ISCN para trisomía 21
  Given un cariotipo con 3 copias del cromosoma 21 y sexo XY
  When el sistema genera el ISCN automáticamente
  Then el string resultante es exactamente "47,XY,+21"
  And cumple la gramática ISCN 2024

Scenario: Override manual con justificación
  Given un Supervisor que identifica anomalía estructural compleja
  When edita el ISCN a "46,XY,t(9;22)(q34;q11.2)" con 80 caracteres de justificación
  Then el sistema valida la gramática del string ingresado
  And registra ISCN_OVERRIDE en Audit Trail con ambas versiones
  And el PDF generado incluye nota al pie sobre la edición manual

Scenario: Rechazo de ISCN con gramática inválida
  Given un Supervisor que intenta ingresar "XY,46" (orden incorrecto)
  When confirma el override
  Then el sistema muestra alerta roja "ISCN inválido: el número de cromosomas debe ir primero"
  And no permite confirmar hasta corregir la sintaxis
```

---

### FSD-UC-007 — Modo Degradado Elegante

**Trazabilidad:** PRD-US-013, PRD-REQ-012 · **Actor:** Analista + Sistema

**Precondiciones:** Servicio TorchServe no disponible (timeout >10s o errores 5xx × 3)

**Disparador:** Sistema detecta 3 fallos consecutivos de TorchServe

**Flujo principal:**
1. Sistema detecta 3 timeouts consecutivos o errores HTTP 5xx de TorchServe
2. Activa flag `system.ai_available = false`
3. Muestra banner persistente en UI: "⚠️ Modo Manual Activado — IA no disponible"
4. Analista puede continuar cargando imágenes normalmente
5. Sistema NO ejecuta segmentación ni clasificación automática
6. Habilita herramientas de segmentación manual (dibujo de bounding boxes)
7. Habilita clasificación manual (asignación de par por menú desplegable)
8. Todas las herramientas de corrección disponibles (dividir, unir, rotar, drag & drop)
9. Cada acción registrada en Audit Trail con flag `mode: "degradado"`
10. Sistema monitorea disponibilidad de TorchServe cada 30 segundos (health check)
11. Cuando TorchServe se restaura → sistema ofrece "Migrar caso a modo automático"
12. Si modo degradado >2 horas continuas → alerta a Administrador + crédito automático al laboratorio

**Postcondiciones:** Laboratorio opera sin interrupción · Tiempo en modo degradado registrado para SLA

**Criterios Gherkin:**
```gherkin
Scenario: Activación automática del modo degradado
  Given que TorchServe no responde por más de 10 segundos tres veces consecutivas
  When un Analista intenta procesar una imagen
  Then el sistema muestra banner "Modo Manual Activado - IA no disponible"
  And habilita todas las herramientas de segmentación y clasificación manual
  And registra cada acción con flag mode: degradado en Audit Trail

Scenario: Restauración del servicio IA
  Given que el sistema está en modo degradado y TorchServe se restaura
  When el health check confirma que TorchServe responde correctamente
  Then el sistema muestra notificación "IA restaurada — puede migrar el caso a modo automático"
  And ofrece botón para re-procesar casos en modo degradado con la IA

Scenario: Alerta por modo degradado prolongado
  Given que el sistema lleva más de 2 horas en modo degradado
  When se cumple el umbral de tiempo
  Then el sistema envía alerta automática al Administrador del sistema
  And registra el evento para aplicar crédito SLA al laboratorio afectado
```

---

### FSD-UC-008 — Notificaciones en Tiempo Real (WebSocket)

**Trazabilidad:** PRD-US-014, NFR-002 · **Actor:** Sistema + Analista

**Precondiciones:** Analista autenticado con sesión WebSocket activa

**Disparador:** Celery Worker completa procesamiento de una muestra

**Flujo principal:**
1. Celery Worker publica en Redis PubSub: `sample:{sample_id}:events` con payload
2. FastAPI WebSocket Manager suscrito al canal recibe el evento
3. WS Manager identifica conexión del Analista propietario del caso
4. Envía push en <500ms: `{status: "ready", sample_id, chromosome_count: 46}`
5. React UI recibe evento → muestra badge en ícono de campana + notificación toast
6. Si Analista no está en la aplicación → sistema envía email de respaldo en <5 minutos

**Flujos alternativos:**
- `A1`: Analista desconectado → evento almacenado 24h en DB para notificación al reconectar

**Postcondiciones:** Analista notificado · Métricas de latencia WebSocket registradas

**Criterios Gherkin:**
```gherkin
Scenario: Push en tiempo real al completar inferencia
  Given un Analista con sesión WebSocket activa esperando resultado
  When el pipeline IA completa el procesamiento de su muestra
  Then recibe notificación WebSocket en menos de 500ms
  And aparece badge numérico en el ícono de notificaciones de la UI
  And puede hacer clic para ir directamente a la mesa de edición

Scenario: Email de respaldo por Analista desconectado
  Given un Analista que no tiene sesión activa cuando su muestra termina
  When el sistema detecta que no hay conexión WebSocket activa
  Then envía email de notificación en menos de 5 minutos
  And almacena el evento para mostrarlo al reconectar
```

---

### FSD-UC-009 — Dashboard de Métricas Operativas

**Trazabilidad:** PRD-US-019, MRD §3 · **Actor:** Administrador + Supervisor

**Precondiciones:** Usuario con rol `admin` o `supervisor` autenticado

**Disparador:** Acceso a ruta `/dashboard/metrics`

**Flujo principal:**
1. Sistema agrega métricas en tiempo real vía consultas a PostgreSQL + Redis
2. Calcula TTK mediano del día: `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ttk_seconds)`
3. Calcula throughput del mes: `COUNT(*) WHERE status='emitido' AND created_at >= start_of_month`
4. Genera histograma de distribución de confidence scores (últimos 7 días)
5. Detecta alertas: si TTK >20 min en más del 10% de casos del día → alerta amarilla
6. Calcula tasa de correcciones manuales, tasa de adopción XAI, tasa de override ISCN
7. Retorna datos al frontend para renderizado de charts (Chart.js)
8. Actualización en tiempo real vía WebSocket cada 60 segundos

**Postcondiciones:** Dashboard actualizado con métricas actuales

**Criterios Gherkin:**
```gherkin
Scenario: Visualización de TTK en tiempo real
  Given un Administrador en el dashboard de métricas
  When accede a la vista de Rendimiento operativo
  Then visualiza el TTK mediano del día en formato MM:SS
  And el dato se actualiza automáticamente sin refrescar la página
  And si el TTK supera 20 minutos en más del 10% de casos, muestra alerta amarilla

Scenario: Exportación de métricas a CSV
  Given un Administrador que necesita análisis externo
  When hace clic en Exportar métricas CSV
  Then el sistema genera archivo CSV con TTK, throughput, tasa correcciones por día
  And el archivo descarga automáticamente con nombre biomed_metrics_YYYY-MM-DD.csv
```

---

### FSD-UC-010 — Gestión de Usuarios y Roles (Administrador)

**Trazabilidad:** PRD-US-018 · **Actor:** Administrador

**Precondiciones:** Usuario con rol `admin` autenticado

**Disparador:** Acceso a ruta `/admin/users`

**Flujo principal:**
1. Administrador ve lista paginada de usuarios (20 por página) con filtros por rol/estado
2. Para crear usuario:
   - Ingresa email, nombre, rol (analista/supervisor), laboratorio de pertenencia
   - Sistema genera contraseña provisional y envía por email
   - Usuario debe cambiar contraseña en primer acceso (forced password change)
3. Para cambiar rol de analista a supervisor:
   - Sistema muestra advertencia de segregación de funciones
   - Requiere confirmación adicional del Administrador
   - Notifica al auditor del laboratorio por email
4. Para desactivar usuario:
   - Sistema desactiva sesiones activas
   - Preserva historial completo en Audit Trail
   - Usuario no puede iniciar sesión (soft delete)
5. Audit Trail: `USER_CREATED` / `ROLE_CHANGED` / `USER_DEACTIVATED`

**Postcondiciones:** Usuario creado/modificado/desactivado · Notificaciones enviadas

**Criterios Gherkin:**
```gherkin
Scenario: Creación de nuevo Analista
  Given un Administrador en el panel de gestión de usuarios
  When crea un nuevo usuario con rol analista y email valido@hospital.bo
  Then el sistema genera contraseña provisional y la envía al email
  And el usuario aparece en la lista con estado Pendiente primer acceso
  And en su primer login debe cambiar la contraseña obligatoriamente

Scenario: Cambio de rol requiere confirmación adicional
  Given un Administrador que cambia el rol de un Analista activo a Supervisor
  When confirma el cambio de rol
  Then el sistema solicita confirmación adicional indicando riesgo de segregación
  And envía notificación al auditor del laboratorio por email
  And Audit Trail registra ROLE_CHANGED con roles anterior y nuevo

Scenario: Desactivación de usuario preserva historial
  Given un Administrador que desactiva un usuario con casos emitidos
  When confirma la desactivación
  Then el usuario no puede iniciar sesión inmediatamente
  And todos sus registros en Audit Trail se preservan íntegramente
  And los casos firmados por ese usuario mantienen su validez legal
```

---

## §5. Reglas de Negocio

| ID | Regla | Tipo | Origen BRD | UCs afectados |
|:---|:---|:---|:---|:---|
| **BR-001** | CHN obligatorio antes de cualquier procesamiento. PII nunca sale del nodo institucional. | Validación | RC-03 | UC-001 |
| **BR-002** | Semaforización: verde si confidence ≥ 0.85, naranja si confidence < 0.85. Score persiste SIN redondear. | Cálculo | RN-02 | UC-002 |
| **BR-003** | Bloqueo de reporte: caso no puede pasar a Supervisor si ∃ cromosoma naranja con `resolution_status='PENDING'` | Política | RN-01 | UC-004 |
| **BR-004** | XAI obligatorio: cromosoma naranja no puede resolverse sin evento `XAI_VIEWED` previo en Audit Trail. | Validación | BRD §6 | UC-003 |
| **BR-005** | Auditoría aleatoria 5% cromosomas con confidence >0.86. Selección REPRODUCIBLE por `SHA256(case_id+"salt")`. | Política | BRD §8 | UC-005 |
| **BR-006** | ISCN generado por motor de reglas (no IA). Override manual requiere justificación ≥50 chars + MFA. | Cálculo | BRD §4 | UC-006 |
| **BR-007** | MFA obligatorio para firma del Supervisor. 3 fallos → bloqueo 15 min + alerta de seguridad. | Validación | 21 CFR §11 | UC-005 |
| **BR-008** | Modo degradado: sistema opera sin IA hasta 2 horas continuas. Crédito automático si se excede. | Política | BRD resilencia | UC-007 |
| **BR-009** | Calidad de metafase: superposición >30% genera `HIGH_OVERLAP` (advertencia, no bloqueo). | Validación | PRD-US-020 | UC-001, UC-002 |
| **BR-010** | Analista y Supervisor NO pueden ser el mismo usuario en casos marcados como críticos (segregación). | Validación | RC-01 | UC-005, UC-006 |
| **BR-011** | Audit Trail INALTERABLE: `REVOKE UPDATE, DELETE ON edits FROM app_user`. Solo INSERT permitido. | Técnica | 21 CFR §11 | Todos |

---

## §6. Modelo de Datos Funcional

### 6.1 Diagrama ER

```mermaid
erDiagram
    USERS {
        uuid id PK
        string email UK
        string name
        enum role "analista|supervisor|admin"
        string password_hash
        string totp_secret
        bool active
        timestamp created_at
    }

    SAMPLES {
        uuid id PK
        string chn_code UK "CHN-YYYY-MM-DD-NNNN"
        string s3_path
        enum status "queued|processing|ready|pending_validation|pending_supervisor|emitido|error|manual_mode"
        uuid analyst_id FK
        uuid supervisor_id FK
        int ttk_seconds
        jsonb quality_flags
        timestamp created_at
        timestamp processed_at
        timestamp signed_at
    }

    CHROMOSOMES {
        uuid id PK
        uuid sample_id FK
        int pair_number "1-22 23=X 24=Y"
        float confidence_score "0.000-1.000 SIN redondear"
        json polygon_coords "GeoJSON array"
        bool requires_review "True si score lt 0.85"
        bool xai_consulted
        bool random_audit_flag
        bool random_audit_reviewed
        enum resolution_status "PENDING|RESOLVED"
        uuid resolved_by FK
        timestamp resolved_at
    }

    EDITS {
        uuid id PK "Solo INSERT — INALTERABLE"
        uuid sample_id FK
        uuid chromosome_id FK
        uuid user_id FK "Siempre del JWT"
        enum action "XAI_VIEWED|CORREGIR_CLASE|DIVIDIR|UNIR|ROTAR_90|VALIDATE|ISCN_OVERRIDE|SIGN_REPORT|USER_CREATED|ROLE_CHANGED"
        json before_state
        json after_state
        string previous_hash "SHA256 del registro anterior"
        string current_hash "SHA256 de este registro"
        string mode "normal|degradado"
        timestamp created_at "DEFAULT NOW()"
    }

    REPORTS {
        uuid id PK
        uuid sample_id FK UK
        string iscn_nomenclature "READ ONLY tras generación"
        string iscn_override "si override manual"
        text override_justification "≥50 chars"
        enum status "pending_validation|pending_supervisor|emitido"
        uuid signed_by FK
        string mfa_method
        string mfa_token_hash
        timestamp signed_at
    }

    USERS ||--o{ SAMPLES : "analiza"
    SAMPLES ||--o{ CHROMOSOMES : "contiene"
    SAMPLES ||--o{ EDITS : "registra"
    CHROMOSOMES ||--o{ EDITS : "historial edición"
    SAMPLES ||--|| REPORTS : "genera"
    USERS ||--o{ REPORTS : "firma"
    USERS ||--o{ CHROMOSOMES : "valida"
```

### 6.2 Diccionario de Datos

| Entidad | Atributo | Tipo | Obligatorio | Validación | Origen |
|:---|:---|:---|:---|:---|:---|
| `SAMPLES` | `chn_code` | VARCHAR(50) UK | Sí | Regex `CHN-\d{4}-\d{2}-\d{2}-\d{4}` | Sistema |
| `SAMPLES` | `status` | ENUM | Sí | Ver estados válidos | Sistema |
| `CHROMOSOMES` | `confidence_score` | DECIMAL(5,4) | Sí | 0.0000 a 1.0000 — SIN redondear | IA |
| `CHROMOSOMES` | `resolution_status` | ENUM | Sí | `PENDING` o `RESOLVED` | Sistema |
| `CHROMOSOMES` | `xai_consulted` | BOOLEAN | Sí | Obligatorio `TRUE` antes de resolver naranja | Sistema |
| `EDITS` | `action` | VARCHAR(50) | Sí | Ver enum de acciones válidas | Sistema |
| `EDITS` | `current_hash` | VARCHAR(64) | Sí | SHA256 hexadecimal de (previous_hash + payload) | Sistema |
| `EDITS` | `user_id` | UUID | Sí | Siempre del JWT, nunca del body HTTP | JWT |
| `REPORTS` | `iscn_nomenclature` | TEXT | Sí | READ ONLY — no existe endpoint PATCH | Sistema |
| `REPORTS` | `override_justification` | TEXT | Condicional | ≥50 chars si override activo | Supervisor |

---

## §7. Contratos API REST

| Método | Endpoint | Descripción | Request | Response | Auth |
|:---|:---|:---|:---|:---|:---|
| `POST` | `/api/v1/samples/image` | Ingesta imagen + CHN | `multipart/form-data` | `202 {sample_id, chn_code, task_id}` | JWT analista |
| `GET` | `/api/v1/samples` | Lista muestras con filtros | `?status=&chn=&page=` | `200 {items[], total, page}` | JWT |
| `GET` | `/api/v1/samples/{id}` | Detalle de muestra | — | `200 SampleDetail` | JWT |
| `GET` | `/api/v1/samples/{id}/chromosomes` | Lista cromosomas de muestra | — | `200 [ChromosomeDetail]` | JWT |
| `PATCH` | `/api/v1/chromosomes/{id}/validated` | Valida cromosoma naranja | `{validated: true}` | `200 {all_validated, remaining}` | JWT analista |
| `PATCH` | `/api/v1/chromosomes/{id}/position` | Mueve cromosoma (drag&drop) | `{new_pair: int}` | `200 ChromosomeDetail` | JWT analista |
| `PATCH` | `/api/v1/chromosomes/{id}/rotate` | Rota cromosoma 90° | `{degrees: 90}` | `200 ChromosomeDetail` | JWT analista |
| `POST` | `/api/v1/chromosomes/{id}/xai` | Solicita Grad-CAM | — | `200 {heatmap_b64, salient_region, explanation}` | JWT analista |
| `POST` | `/api/v1/samples/{id}/pass-to-supervisor` | Transición a Supervisor | — | `200 {status: pending_supervisor}` | JWT analista |
| `GET` | `/api/v1/samples/{id}/audit-trail` | Historial de ediciones | `?page=` | `200 [EditRecord]` | JWT supervisor |
| `POST` | `/api/v1/reports` | Genera informe ISCN | `{sample_id}` | `201 {report_id, iscn_nomenclature}` | JWT analista |
| `POST` | `/api/v1/reports/{id}/sign` | Firma digital con MFA | `{mfa_token, mfa_method}` | `200 {status: emitido, signed_at}` | JWT supervisor |
| `PATCH` | `/api/v1/reports/{id}/iscn-override` | Override manual ISCN | `{final_iscn, justification, mfa_token}` | `200 {iscn_override, audit_id}` | JWT supervisor |
| `WS` | `/ws/samples/{id}` | Notificaciones tiempo real | — | Push events | JWT |
| `GET` | `/api/v1/admin/users` | Lista usuarios | `?role=&active=` | `200 [UserDetail]` | JWT admin |
| `POST` | `/api/v1/admin/users` | Crea usuario | `{email, name, role, lab_code}` | `201 UserDetail` | JWT admin |
| `GET` | `/api/v1/metrics/operational` | Métricas operativas | `?from=&to=` | `200 MetricsReport` | JWT admin/supervisor |

---

## §8. Prompt Contracts (Contratos de Prompt)

### PM-FSD-001 — Segmentación U-Net

```
Role: Eres un pipeline de visión computacional especializado en citogenética.

Task: Recibir imagen de metafase anonimizada (CHN path de S3) y producir:
  1. Segmentación de cromosomas individuales (polígonos + bounding boxes)
  2. Flag de calidad de metafase (HIGH_OVERLAP si superposición >30%)
  3. Conteo de cromosomas detectados

Context:
  - Entrada: TIFF/PNG anonimizado, ≥1024×1024px, <50MB
  - Restricción tiempo: inferencia <15s en GPU T4 o superior
  - Usar tiling 1024×1024 con overlap 64px si imagen >4000px
  - Modelo: U-Net con backbone ResNet34

Reasoning:
  1. CLAHE preprocessing (clipLimit=3.0, tileGridSize=8×8)
  2. U-Net segmentación → polígonos y bounding boxes por tile
  3. NMS para eliminar duplicados en bordes de tiles (IoU threshold 0.3)
  4. Calcular overlap index; si >30% → HIGH_OVERLAP
  5. Verificar conteo; si <40 o >55 → ABNORMAL_COUNT

Stop Condition: Todos los cromosomas detectados procesados o timeout de 30s.

Output: JSON con chromosomes[], quality_flags[], inference_time_ms

Invariants: IoU segmentación >0.90. No procesar PII. confidence en [0.000, 1.000].
Failure modes: timeout → activar modo degradado UC-007. Conteo anormal → quality_flag ABNORMAL_COUNT.
```

### PM-FSD-002 — Clasificación EfficientNet-B3

```
Role: Eres un clasificador de cromosomas especializado en citogenética clínica.

Task: Recibir crops de cromosomas (224×224px) en batch y clasificar cada uno en:
  par cromosómico (1-22, X, Y) + confidence_score Softmax

Context:
  - Batch size: máximo 16 cromosomas por request a TorchServe
  - Modelo: EfficientNet-B3 con 24 clases de salida
  - Umbral crítico: score < 0.85 → requires_review = True
  - NUNCA redondear confidence_score antes de persistir

Reasoning:
  1. Recibir batch de crops base64 (máximo 16)
  2. Forward pass EfficientNet-B3
  3. Aplicar Softmax → vector de 24 probabilidades por cromosoma
  4. confidence_score = max(softmax_vector)
  5. predicted_class = argmax(softmax_vector)
  6. requires_review = (confidence_score < 0.85)

Stop Condition: Todos los cromosomas del batch clasificados.

Output: Lista [{pair_number, confidence_score, requires_review}] × N

Invariants: confidence_score SIN redondear. requires_review boolean calculado en backend.
Failure modes: TorchServe no disponible → activar modo degradado UC-007.
```

### PM-FSD-003 — XAI Grad-CAM

```
Role: Eres un motor de explicabilidad de IA especializado en cariotipado citogenético.

Task: Generar mapa de calor Grad-CAM para un cromosoma dado, mostrando qué bandas
  cromosómicas influyeron en la clasificación de EfficientNet-B3.

Context:
  - Entrada: crop 224×224 RGB, logits EfficientNet-B3, clase predicha
  - Tiempo máximo: <1 segundo por cromosoma
  - Capa objetivo: última capa convolucional (features.dense_block5)

Reasoning:
  1. Obtener feature maps de la última capa convolucional
  2. Calcular gradientes de la clase predicha respecto a los feature maps
  3. Promediar gradientes por canal → pesos de importancia
  4. Combinación lineal ponderada de feature maps
  5. ReLU para mantener solo influencia positiva
  6. Redimensionar mapa de calor a 224×224
  7. Superponer sobre crop con opacidad 0.5
  8. Mapear región de máxima intensidad a lookup table de bandas G

Stop Condition: Mapa de calor generado y región identificada.

Output: {heatmap_base64, salient_region, explanation_text}

Invariants: Heatmap cubre imagen completa del crop. Tiempo <1s.
Failure modes: Si región no identificable → explanation_text genérico, no error.
```

---

## §9. Integraciones Externas

| Sistema | Tipo | Protocolo | Operaciones | SLA | Autenticación |
|:---|:---|:---|:---|:---|:---|
| TorchServe (GPU) | Síncrono interno | REST HTTPS | `POST /predictions/unet_karyotype` `POST /predictions/efficientnet_b3` | 99.5% / p95 <15s | API Key + mTLS |
| MinIO / S3 | Asíncrono | S3 API | `PUT`, `GET`, `DELETE` por chn_code | 99.9% / p95 <3s | IAM / Access Key |
| PostgreSQL 15 | Síncrono | TCP/TLS | SQL queries (CRUD + audit trail) | 99.99% | User/pass + TLS |
| Redis 7 | Síncrono | Redis Protocol | Pub/Sub + Queue | 99.9% | ACL + TLS |
| Email SMTP | Asíncrono | SMTP/TLS | Notificaciones usuario | 99% / <5min | SMTP credentials |
| Timestamping (opcional) | Síncrono | HTTPS | `POST /timestamp` (21 CFR Part 11) | 99.9% / <500ms | API Key |

---

## §10. NFRs Consolidados ISO 25010

| ID | Característica ISO 25010 | Sub-característica | Requisito | Métrica | Umbral | Verificación |
|:---|:---|:---|:---|:---|:---|:---|
| NFR-001 | Eficiencia de rendimiento | Comportamiento temporal | Inferencia IA por imagen | Mediana | <15s GPU | k6 carga 100 imágenes |
| NFR-002 | Eficiencia de rendimiento | Comportamiento temporal | Latencia WebSocket push | p95 | <500ms | Playwright timing |
| NFR-003 | Eficiencia de rendimiento | Comportamiento temporal | TTK total por caso | p95 | <15 min | Logs del sistema |
| NFR-004 | Eficiencia de rendimiento | Comportamiento temporal | Render cariotipo en UI | Mediana | <2s | Lighthouse CI |
| NFR-005 | Fiabilidad | Disponibilidad | Uptime horario laboral 07-19 | SLA mensual | ≥99.5% | UptimeRobot + Grafana |
| NFR-006 | Fiabilidad | Tolerancia a fallos | Tiempo máximo modo degradado | Continuo | <2 horas | Monitoreo + simulación |
| NFR-007 | Seguridad | Integridad | Audit Trail hash chain | Cumplimiento | 21 CFR Part 11 | Auditoría externa |
| NFR-008 | Seguridad | Autenticidad | Firma Supervisor | Autenticación | MFA obligatorio (TOTP/bio) | Pruebas auth |
| NFR-009 | Seguridad | Confidencialidad | PII en tránsito/reposo | Almacenamiento | 0 PII fuera del nodo | Auditoría de red |
| NFR-010 | Mantenibilidad | Modificabilidad | Verificación hash chain | Tiempo | <100ms para 1000 registros | Test unitario |
| NFR-011 | Portabilidad | Adaptabilidad | Navegadores soportados | Cobertura | Chrome 120+, Firefox 121+, Edge 120+ | Playwright cross-browser |
| NFR-012 | Usabilidad | Facilidad de aprendizaje | Curva de aprendizaje Analista | Tiempo | <1 hora primer caso completo | Test usabilidad think-aloud |
| NFR-013 | Eficiencia de rendimiento | Capacidad | Throughput laboratorio | Muestras/mes | ≥500 | k6 + Docker Compose scale |

---

## §11. Trazabilidad MRD → PRD → FSD → NFR → Prueba

| MRD | PRD | FSD | NFR | Prueba QA |
|:---|:---|:---|:---|:---|
| MRD-01 Anonimización | PRD-REQ-001 | UC-001 | NFR-009 | TC-001: PII no en S3 |
| MRD-02 Segmentación | PRD-REQ-002 | UC-002 | NFR-001 | TC-002: IoU >0.90 |
| MRD-03 Clasificación | PRD-REQ-003 | UC-002 | NFR-001 | TC-003: 46 cromosomas |
| MRD-04 Semaforización | PRD-REQ-004 | UC-002 | — | TC-004: verde/naranja correcto |
| MRD-05 Bloqueo | PRD-REQ-005 | UC-004 | — | TC-005: botón inhabilitado |
| MRD-06 XAI | PRD-REQ-006 | UC-003 | NFR-004 | TC-006: heatmap <1s |
| MRD-07 Corrección | PRD-REQ-007 | UC-003 | — | TC-007: audit trail drag&drop |
| MRD-08 Auditoría 5% | PRD-REQ-008 | UC-005 | — | TC-008: selección reproducible |
| MRD-09 Audit Trail | PRD-REQ-009 | UC-005 | NFR-007, NFR-010 | TC-009: hash chain íntegro |
| MRD-10 Firma MFA | PRD-REQ-010 | UC-005 | NFR-008 | TC-010: bloqueo 3 fallos |
| MRD-11 ISCN | PRD-REQ-011 | UC-006 | — | TC-011: "46,XY" correcto |
| MRD-12 Modo degradado | PRD-REQ-012 | UC-007 | NFR-006 | TC-012: operación sin IA |
| MRD-13 Notificaciones | PRD-US-014 | UC-008 | NFR-002 | TC-013: push <500ms |
| MRD-14 Métricas | PRD-US-019 | UC-009 | — | TC-014: TTK mediano correcto |
| MRD-15 Usuarios | PRD-US-018 | UC-010 | — | TC-015: segregación roles |

---

## §12. Plan de Pruebas

**Estrategia:**
- **Unitarias:** pytest (backend >80% cobertura en dominio y servicios) + Jest/RTL (frontend >70% componentes críticos)
- **Integración:** FastAPI TestClient para endpoints · Verificación integridad hash chain · Validación pipeline CV con imágenes sintéticas
- **E2E:** Playwright para flujos completos (carga → IA → validación → firma)
- **Carga:** k6 para NFR de rendimiento (100 imágenes simultáneas) + `docker compose scale celery_worker=5`
- **Seguridad:** OWASP ZAP para endpoints públicos · Auditoría de logs para detección de PII
- **Prompt-contract:** Verificación que outputs de agentes IA cumplen invariants y failure modes del §8

**Herramientas:** pytest · pytest-asyncio · pytest-cov · locust · Jest · Playwright · k6 · torchtest · OWASP ZAP

**Cobertura mínima:** 80% dominio + use cases · 70% infraestructura (repositorios, API)

---

## §13. Riesgos Funcionales

| Riesgo | Prob. | Impacto | Mitigación | Responsable |
|:---|:---|:---|:---|:---|
| U-Net no alcanza IoU >0.90 | Media | Alto | Dataset validación 2000 imágenes anotadas. Threshold ajustable por laboratorio. | ML Engineer |
| Grad-CAM lento (>1s) afecta TTK | Media | Medio | Precomputar heatmaps durante inferencia inicial, no bajo demanda | Backend |
| MFA genera fricción inaceptable en Supervisores | Media | Medio | Múltiples métodos (TOTP, huella, tarjeta). Capacitación pre-lanzamiento | Product |
| Modo degradado excede 2 horas por fallo GPU | Baja | Alto | Failover a GPU secundaria automático. SLA contractual con proveedor cloud | DevOps |
| Override ISCN sin justificación adecuada | Baja | Medio | Audit Trail alerta si tasa override >10%. Dashboard para monitoreo | Product |
| Pérdida de mapeo CHN en laboratorio | Baja | Alto | Backup diario del vault CHN. Laboratorio responsable de su clave de cifrado | Soporte |
| Hash chain causa bottleneck en DB alta carga | Baja | Bajo | Escritura por lotes cada 10 eventos. Índices optimizados en PostgreSQL | Backend |

---

## §14. Glosario

| Término | Definición |
|:---|:---|
| **CHN** | Código de Historia Clínica Normalizado. Formato `CHN-YYYY-MM-DD-NNNN`. Anonimiza al paciente antes de cualquier transmisión cloud. |
| **Confidence Score** | Valor float entre 0.000 y 1.000 (SIN redondear) que indica la certeza del modelo EfficientNet-B3 en su clasificación. |
| **EfficientNet-B3** | Red neuronal convolucional para clasificación de cromosomas (24 clases: pares 1-22, X, Y). |
| **Grad-CAM** | Gradient-weighted Class Activation Mapping. Técnica XAI que genera mapas de calor sobre la imagen de entrada. |
| **HITL** | Human-in-the-Loop. Paradigma donde la IA asiste pero el especialista toma la decisión clínica final. |
| **IoU** | Intersection over Union. Métrica de calidad de segmentación (target >0.90). |
| **ISCN** | International System for Human Cytogenomic Nomenclature 2024. Estándar mundial para nomenclatura citogenética. |
| **MFA** | Multi-Factor Authentication. Requiere dos o más métodos: algo que tienes (TOTP) + algo que eres (huella) o tienes (tarjeta). |
| **NMS** | Non-Maximum Suppression. Algoritmo para eliminar detecciones duplicadas en bordes de tiles. |
| **Override** | Edición manual de un valor generado automáticamente por el sistema. Requiere justificación y MFA. |
| **PII** | Personally Identifiable Information. Datos que identifican a un paciente (nombre, DNI, fecha nacimiento). |
| **Softmax** | Función matemática que convierte logits del modelo en probabilidades sumando 1.0. |
| **TTK** | Time to Karyotype. Tiempo total desde carga de imagen hasta reporte firmado. Meta: ≤15 minutos. |
| **U-Net** | Arquitectura de red neuronal para segmentación semántica de imágenes. Usada para detectar cromosomas individuales. |
| **XAI** | Explainable Artificial Intelligence. Capacidad del sistema de justificar sus decisiones con evidencia visual. |
| **21 CFR Part 11** | Regulación FDA para registros electrónicos en industria farmacéutica/médica. BIOMED cumple mediante Audit Trail con hash chain. |

---

## §15. Checklist de Cumplimiento — Nivel EXCELENTE ✅

| Criterio rúbrica | Estado | Evidencia |
|:---|:---|:---|
| **≥30 elementos totales** (UC + BR + Gherkin + ER + API contracts + glosario + anexos) | ✅ **50+ elementos** | 10 UC + 11 BR + 30 Gherkin + ER + 17 API endpoints + 15 glosario + 15 trazabilidad |
| **≥10 casos de uso críticos** con flujo principal, alternos y Gherkin | ✅ **10 UC completos** | UC-001 a UC-010 cada uno con flujo principal, alternativos y 2-3 escenarios Gherkin |
| **Modelo de datos** con diagrama ER + diccionario | ✅ | §6.1 Mermaid + §6.2 diccionario 10 campos |
| **Contratos API REST** formales | ✅ **17 endpoints** | §7 tabla completa con método, request, response, auth |
| **Prompt contracts** con 6 elementos + invariants + failure modes | ✅ **3 contratos FSD** | §8 PM-FSD-001/002/003 + 7 en PROMPT_MAPPINGS.md = 10 total |
| **NFRs ISO 25010** con métrica, umbral y verificación | ✅ **13 NFRs** cubriendo 6 características | §10 tabla con característica ISO específica |
| **Trazabilidad MRD → PRD → FSD → NFR → Prueba** | ✅ | §11 — 15 cadenas de trazabilidad |
| **Plan de pruebas** con estrategia, herramientas y cobertura | ✅ | §12 — unitarias + integración + E2E + carga + seguridad |
| **Glosario técnico** ≥10 términos | ✅ **15 términos** | §14 |
| **Tasks ejecutables** vinculadas a UC y prompt | ✅ **12 tasks** | §2.4 con PM asociado |

---

## §16. Registro de Cambios

| Versión | Fecha | Autor | Cambio |
|:---|:---|:---|:---|
| v0.1 | Mayo 2026 | G. Mamani | Versión inicial FSD clásico |
| v0.2 | Mayo 2026 | G. Mamani | Tasks, prompt contracts, trazabilidad M2 |
| v1.0 | Mayo 2026 | G. Mamani | Versión aprobada, alineada PRD v1 + BRD v3.5 |
| **v2.0** | **Mayo 2026** | **G. Mamani** | **10 UC completos, 17 API contracts, ISO 25010 NFRs, glosario 15 términos, formato Markdown limpio** |
