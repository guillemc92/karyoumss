# DD-KARYO-004 — Herramientas de imagen (zoom/pan/rotar/brillo) + Modo degradado integrado (P4)

| Campo | Valor |
|---|---|
| **ID** | DD-KARYO-004 |
| **ADR origen** | [ADR-0021](../adr/0021-visor-correccion-cariotipo.md) §D5 (P4) + [ADR-0022](../adr/0022-audit-trail-clinico-django.md) |
| **FSD** | FSD-UC-007 (modo degradado elegante), FSD-UC-003 (herramientas de imagen) |
| **Reglas** | RN-07 (degradación elegante), RN-05 (audit append-only), BR-008 (modo degradado ≤2h, facturable) |
| **Estado** | En implementación |
| **Fecha** | 2026-07-24 |

## 1. Alcance de P4

Cuarta y última fase del núcleo clínico (ADR-0021 D5). Dos piezas:

### 1.1 Herramientas de imagen (canvas Konva)
Toolbar de manipulación del **viewport** del cariograma: zoom (in/out + %),
pan (arrastre), rotar (izq/der), brillo, contraste, restablecer. En el
prototipo `correccion de cariotipo.html` era la barra superior del panel
central (`zoomInBtn`, `panBtn`, `rotateLeftBtn`, `brightnessToolBtn`, …).

### 1.2 Modo degradado integrado (FSD-UC-007, RN-07)
Cuando el pipeline de IA está caído (circuit breaker abierto), el visor:
- Muestra banner **"Modo Manual — IA no disponible"**.
- Mantiene disponibles las **herramientas manuales P3** (reclasificar,
  separar, unir, cruce) — el analista corrige sin IA.
- Marca **cada evento de audit con `mode: "degradado"`** (FSD-UC-007 §7,
  para la facturación de BR-008).
- Monitorea la disponibilidad de IA cada 30 s (§8) y, al restaurarse, ofrece
  volver a modo automático (§9).

**Fuera de P4** (requiere imágenes reales / pipeline ADR-0007): editor de
segmentación manual desde cero (dibujar bounding boxes, §5). Se difiere.

## 2. Backend

### 2.1 `AuditEvent.mode` (migración 0008)
`mode = CharField(choices=[auto, degradado], default='auto')`. Materializa el
flag de FSD-UC-007 §7 como **campo consultable** (para BR-008: tiempo/eventos
en degradado son facturables), no enterrado en el payload.

### 2.2 Threading del modo
- `emit_audit_event(..., mode='auto')` setea `event.mode`.
- Cada servicio que emite audit (view_xai, resolve, mark_anomaly, validate,
  reclassify, split, join, resolve_cross) gana un `mode='auto'` que pasa a
  `emit_audit_event`.
- Las vistas leen el modo del header **`X-Biomed-Mode`** (`_request_mode()`):
  degradado es un estado del sistema, cross-cutting → header, no body de cada
  endpoint. Default `'auto'` si ausente.

### 2.3 `GET /api/clinic/pipeline/health/`
`PipelineHealthView` → `{available: bool, mode: 'auto'|'degradado'}` a partir de
`pipeline_client._circuit_open()` (chequeo barato, sin llamada de red — apto
para polling cada 30 s). Permiso `sample.view`.

### 2.4 Serializer
`AuditEventSerializer` expone `mode` (read-only).

## 3. Frontend

### 3.1 Herramientas de imagen
- **`lib/viewport.ts` (puro, 100% testeable):** estado
  `{scale, rotation, offsetX, offsetY, brightness, contrast}` + reducer con
  acciones `zoomIn/zoomOut/rotateLeft/rotateRight/setBrightness/setContrast/
  pan/reset`. Clamps: scale ∈ [0.5, 3], rotation mod 360, brillo/contraste
  ∈ [50, 150] %.
- **`components/KaryoImageToolbar.tsx`:** botones zoom−/%/+, rotar ◄/►,
  sliders brillo/contraste, toggle "Mover" (pan), "Restablecer".
  `data-testid="viewport-*"`.
- **`KaryotypeCanvas`:** aplica el viewport — `Stage` `scaleX/scaleY`,
  `rotation`, `x/y` (offset); brillo/contraste vía **CSS filter** en el
  contenedor `.karyo-canvas` (los cromosomas son vectoriales, no hay imagen
  real todavía — ADR-0007). Pan: en modo "Mover" el `Stage` es `draggable` y
  los cromosomas NO (evita conflicto con el drag de reclasificación);
  `onDragEnd` del stage → `viewport.pan`.

### 3.2 Modo degradado
- **`api/samplesClient`:** variable de módulo `clinicMode` + `setClinicMode()`;
  `clinicRequest` añade header `X-Biomed-Mode: <clinicMode>` en toda petición
  clínica (cross-cutting, sin tocar cada método del client).
- **`hooks/useDegradedMode`:** react-query a `/pipeline/health/`, `refetchInterval`
  30 s. Al detectar `available=false` → `setClinicMode('degradado')` y devuelve
  `degraded=true`; al restaurarse → `setClinicMode('auto')`.
- **`pages/KaryotypePage`:** toolbar de imagen + estado de viewport; banner
  "Modo Manual" cuando degradado; indicador "IA restaurada — modo automático"
  al reconectar. Las herramientas P3 permanecen activas en degradado.

## 4. Tests (RN-09 ≥90%)
**Backend** (`test_karyotype_p4.py`): audit registra `mode='degradado'` con el
header, `'auto'` sin él; endpoint health reporta `available/mode` según el
circuit breaker (abierto/cerrado); serializer expone `mode`.

**Frontend:** `viewport.spec.ts` (reducer puro: clamps, zoom, rotate, pan,
reset), `KaryoImageToolbar` (dispara acciones), `KaryotypeCanvas` (aplica
scale/rotation/filter, pan mode desactiva drag de cromosoma), `useDegradedMode`
(setea clinicMode), `karyotypeP4.spec` de página (toolbar zoom/rotar/reset,
banner degradado, acción manual marcada `degradado` en la bitácora).

## 5. MSW / seed
- Handler `GET /pipeline/health/` usando `forceDegraded` → `{available, mode}`.
- `pushAudit` acepta `mode` (lee el header `X-Biomed-Mode` de la request) y lo
  guarda en el evento; los handlers P2/P3 lo propagan.
- `AUDIT_LABELS` / UI muestran un distintivo cuando `mode='degradado'`.
