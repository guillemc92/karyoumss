# DD-ML-002 — Wiring backend-clinic ↔ backend-ml (flujo real, Fase B2)

| Campo | Valor |
|---|---|
| **ID** | DD-ML-002 |
| **ADR origen** | [ADR-0007](../adr/0007-microservicio-inferencia.md) + [ADR-0015](../adr/0015-arquitectura-clinica-django.md) (#6 pipeline_client) + [DD-ML-001](DD-ML-001.md) |
| **Reglas** | RN-02 (semaforización), RN-07 (degradación elegante) |
| **Estado** | En implementación |
| **Fecha** | 2026-07-24 |

## 1. Alcance
Conectar el flujo real: **registro con imagen real → backend-ml segmenta →
backend-clinic ingesta los cromosomas reales → visor**. Reemplaza el mock: el
cariotipo sale de la imagen subida, no de datos inventados. Baseline (DD-ML-001):
segmentación real, clasificación placeholder (todo naranja → clasificación manual).

## 2. Backend-clinic

### 2.1 Almacenamiento de imagen real
`MEDIA_ROOT`/`MEDIA_URL` en settings. `SampleRegistrationService._create_images`
**guarda los bytes** decodificados en `MEDIA_ROOT/<chn>/<ts>_<idx>.<ext>` (hoy los
descarta). `SampleImage.image_path` = ruta relativa.

### 2.2 `pipeline_client.segment_image(image_bytes) -> dict`
POST multipart a `{CLINIC_FASTAPI_URL}/api/v1/segment/` (backend-ml). Falla de red
/HTTP → `MLDegradedError` (RN-07). Reusa el circuit breaker existente.

### 2.3 `services.ingest_segmentation(sample, result) -> Karyotype`
Crea (o reemplaza) el `Karyotype` 1:1 + las filas `Chromosome` desde
`result['chromosomes']`: `predicted_class`, `confidence_score` (Decimal), `bbox`
{x,y,w,h}, `order`, `position_index` (contador por clase), `resolution_status`
= `PENDING` si confianza < 0.85 (naranja, RN-02) si no `AUTO`. `model_version` =
`result['model_version']`.

### 2.4 Flujo
- **Registro no-borrador:** tras guardar imágenes → carga la 1ª → `segment_image`
  → `ingest_segmentation` → estado `READY`. Si `MLDegradedError` → `PENDING_AI`
  degradado (sin cariotipo, la muestra se persiste igual, RN-07).
- **`POST /samples/{id}/process/`** (reprocesar): carga la imagen almacenada →
  `segment_image` → `ingest_segmentation` → `READY`. 503 `ML_DEGRADED` si cae.

## 3. Backend-ml
Sin cambios: `/api/v1/segment/` (DD-ML-001) ya cumple. `CLINIC_FASTAPI_URL` de
backend-clinic ya apunta a `:8000`.

## 4. Frontend
Sin cambios de código: en modo **proxy** (no MSW) el registro real pega a
backend-clinic → backend-ml → visor muestra los cromosomas reales. El fix
registro→visor (commit previo) ya deja el flujo apuntando al visor React.

## 5. Tests
**backend-clinic** (`pipeline_client.segment_image` mockeado): registro no-borrador
→ crea `Karyotype` + N `Chromosome` con los datos del result; naranja→PENDING;
degradado (MLDegradedError) → PENDING_AI sin cariotipo; process reprocesa.
**Integración real (manual/E2E):** levantar backend-ml + backend-clinic, registrar
por API con una metafase MetaClass real → `GET /karyotype/` devuelve cromosomas
reales.

## 6. Fuera de alcance
Async (Celery/Redis) — sync alcanza para el baseline (POC-03 ya validó el async).
Grad-CAM real y clasificación precisa → Fase C (modelo entrenado).
