# DD-KARYO-001 — Visor de Cariotipo read-only con Semaforización (P1)

| Campo | Valor |
|---|---|
| **ID** | DD-KARYO-001 |
| **ADR origen** | [ADR-0021](../adr/0021-visor-correccion-cariotipo.md) §D1–D5 (P1) |
| **FSD** | FSD-UC-002 (semaforización), base de FSD-UC-003/004 |
| **Bounded context** | Clínico (backend-clinic + frontend-clinic, ADR-0015) |
| **Estado** | En implementación |
| **Fecha** | 2026-07-23 |

## 1. Alcance de P1

Visor **read-only**: dado un `Sample` con cariotipo generado, mostrar el
grid de cromosomas 1–22/X/Y con su semaforización (verde ≥0.85 / naranja
<0.85 / rojo si falló), y un panel de propiedades al seleccionar un
cromosoma. **Sin edición, sin XAI, sin drag & drop** (P2/P3).

Fuera de alcance P1: resolver naranjas, gating de bloqueo, transiciones de
estado, audit trail de correcciones, Konva.

## 2. Modelo de datos (`backend-clinic/apps/samples/models.py`)

```python
CONFIDENCE_THRESHOLD = Decimal('0.850')   # RN-02, ADR-0006 / ADR-0021 D2

class ChromosomeResolution(models.TextChoices):
    AUTO     = 'AUTO', 'Automático (verde)'      # confidence >= umbral
    PENDING  = 'PENDING', 'Pendiente (naranja)'  # confidence < umbral, sin resolver
    RESOLVED = 'RESOLVED', 'Resuelto'            # naranja resuelto por analista (P2)

class Karyotype(models.Model):
    id            = UUIDField(pk)
    sample        = OneToOneField(Sample, related_name='karyotype')
    model_version = CharField(default='u-net-v2.1+efficientnet-b3-v1.4')
    image_path    = CharField(blank)            # metafase fuente
    generated_at  = DateTimeField(auto_now_add)

class Chromosome(models.Model):
    id                = UUIDField(pk)
    karyotype         = ForeignKey(Karyotype, related_name='chromosomes')
    predicted_class   = CharField(choices=CHROMOSOME_CLASSES)  # '1'..'22','X','Y'
    position_index    = IntegerField(default=0)    # copia dentro del par (0/1)
    confidence_score  = DecimalField(max_digits=4, decimal_places=3, null=True)  # null = red
    bbox              = JSONField(default=dict)    # {x,y,w,h} crop en la metafase (P3)
    measures          = JSONField(default=dict)    # {length_um, centromeric_index, band_count, quality}
    resolution_status = CharField(choices=ChromosomeResolution, default=AUTO)
    xai_viewed        = BooleanField(default=False)  # gate FSD-UC-003 (P2)
    order             = IntegerField(default=0)    # orden estable de render

    @property
    def semaphore(self) -> str:
        if self.confidence_score is None: return 'red'
        return 'green' if self.confidence_score >= CONFIDENCE_THRESHOLD else 'orange'
```

`SampleStatus` += `BLOCKED_BY_CONFIDENCE`, `ANALYST_VALIDATED` (declarados,
sin transiciones en P1 — ADR-0021 D3).

## 3. Endpoint

| Método | URL | Permiso | Respuesta |
|---|---|---|---|
| GET | `/api/clinic/samples/{id}/karyotype/` | `HasOpcion('sample.view')` + owner/staff scope | `KaryotypeSerializer` |

- **404** si el `Sample` no tiene `Karyotype` (aún no procesado).
- **403** si el analista no es dueño de la muestra (mismo scope que
  `SampleDetailView`, RN-06).

### Shape de respuesta

```json
{
  "id": "uuid",
  "sample_id": "uuid",
  "model_version": "u-net-v2.1+efficientnet-b3-v1.4",
  "generated_at": "ISO-8601",
  "summary": {
    "total": 46, "green": 43, "orange": 3, "red": 0,
    "unresolved_orange": 3, "is_blocked": true
  },
  "chromosomes": [
    {
      "id": "uuid", "predicted_class": "18", "position_index": 0,
      "confidence_score": "0.720", "semaphore": "orange",
      "resolution_status": "PENDING", "xai_viewed": false,
      "measures": {"length_um": 5.2, "centromeric_index": 0.38,
                   "band_count": 320, "quality": "alta"},
      "bbox": {"x": 120, "y": 84, "w": 40, "h": 96}, "order": 34
    }
  ]
}
```

`summary` es **derivado** en el serializer (no persiste). `is_blocked =
unresolved_orange > 0` — en P1 es informativo (el bloqueo real es P2).

## 4. Componente React (`frontend-clinic`)

- **`KaryotypePage`** (`/clinic/samples/:id/karyotype`) — carga vía
  `karyotypeClient.get(sampleId)`, maneja loading/error/404.
- **`KaryotypeViewer`** — grid SVG/CSS de 24 slots (1–22, X, Y). Cada slot
  agrupa sus cromosomas (por `predicted_class`), cada cromosoma es un
  rectángulo SVG coloreado por `semaphore` (verde `#1e8868`, naranja
  `#d45100`, rojo `#E30613`). Click selecciona.
- **`ChromosomePropertiesPanel`** — muestra clase, confianza %, semáforo,
  medidas del cromosoma seleccionado.
- **`SemaphoreLegend` + banner de resumen** — "3 cromosomas requieren
  revisión" (naranjas), leyenda de colores.
- Link "Ver cariotipo" en `SampleDetailPage` cuando `status ∈ {READY,
  VALIDATED, ...}` (has_karyotype).

## 5. Tests (RN-09 ≥90%)

**Backend** (`test_karyotype.py`):
- `semaphore` verde/naranja/rojo según umbral 0.85 (incluye borde exacto 0.85 → verde).
- summary cuenta green/orange/red/unresolved_orange correctamente.
- `is_blocked` true si hay naranjas sin resolver, false si todos AUTO/RESOLVED.
- GET 200 con cariotipo; GET 404 sin cariotipo; GET 403 analista no-dueño; 401 sin auth.

**Frontend** (`KaryotypeViewer.spec.tsx`, `KaryotypePage.spec.tsx`):
- render de 46 cromosomas con colores correctos por semáforo.
- click selecciona y el panel de propiedades muestra los datos.
- banner de resumen lista los naranjas; leyenda visible.
- loading / error / 404 (sin cariotipo) manejados.

## 6. Seed / MSW

- Management command `seed_karyotype <sample_id>`: 46 cromosomas, ~3 naranjas
  (confidences 0.72/0.80/0.84) para ejercitar la semaforización.
- MSW: handler `GET /api/clinic/samples/:id/karyotype/` con el mismo mock de
  46 cromosomas para el demo `dev:msw`.
