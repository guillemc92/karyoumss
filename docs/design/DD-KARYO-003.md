# DD-KARYO-003 — Corrección manual: reclasificar (drag & drop) + separar/unir/cruce sobre Konva.js (P3)

| Campo | Valor |
|---|---|
| **ID** | DD-KARYO-003 |
| **ADR origen** | [ADR-0021](../adr/0021-visor-correccion-cariotipo.md) §D4/§D5 (P3) + [ADR-0022](../adr/0022-audit-trail-clinico-django.md) |
| **FSD** | FSD-UC-003 (corrección manual del cariotipo) |
| **Reglas** | RN-02 (semaforización), RN-05 (audit append-only), BR-003 (override manual del analista) |
| **Estado** | En implementación |
| **Fecha** | 2026-07-24 |

## 1. Alcance de P3

Sobre el visor de P1/P2, habilitar la **corrección manual** del cariotipo con
un lienzo interactivo **Konva.js** (`react-konva`), que ADR-0021 §D4 difirió a
esta fase (YAGNI: el drag & drop de crops es lo que justifica el canvas):

1. **Reclasificar (drag & drop)** — arrastrar un cromosoma de un slot a otro
   (`1..22/X/Y`) corrige su clase → `CORRECT_CLASS`. Override manual autoritativo
   (BR-003): marca el cromosoma como `RESOLVED` (deja de bloquear el caso).
2. **Separar (touching)** — un blob segmentado como un solo cromosoma que en
   realidad son dos → se divide en 2 cromosomas (bbox partido) → `SPLIT`.
3. **Unir fragmentos** — dos fragmentos que son un solo cromosoma → se fusionan
   (bbox unión, uno queda inactivo) → `JOIN`.
4. **Resolver cruce** — dos cromosomas que se solapan/cruzan → se individualizan
   (marca el cromosoma como resuelto) → `RESOLVE_CROSS`.

Cada acción emite su evento en la **misma transacción atómica** (ADR-0022) y se
refleja en la bitácora de P2. Los tipos de evento ya estaban declarados en
`AuditEventType` (RECLASSIFY/CORRECT_CLASS/SPLIT/JOIN/RESOLVE_CROSS) desde P2.

**Nota de fidelidad (mock vs. real):** sobre datos mock los `bbox` son
placeholders; las operaciones morfológicas (separar/unir/cruce) manipulan esos
`bbox` de forma geométrica simple. La segmentación real (máscaras U-Net) llega
con el pipeline de inferencia (ADR-0007); este DD deja el modelo, la API y la
UX listos para conectarlos, sin acoplarse a la máscara real.

**Fuera de P3:** herramientas de imagen (zoom/pan/rotar/brillo) y modo
degradado → P4 (ADR-0021 §D5).

## 2. Backend

### 2.1 Cambio de modelo — `Chromosome.is_active`
`is_active = BooleanField(default=True)`. **JOIN** hace soft-remove del fragmento
absorbido (no `DELETE` físico: preservar la trazabilidad de `AuditEvent`, cuyo FK
a `Chromosome` es `SET_NULL`). El visor, el `summary` y `_unresolved_count` solo
consideran cromosomas `is_active=True`. Migración `0007`.

### 2.2 Servicios (`services.py`) — todos en `transaction.atomic` + audit
| Servicio | Efecto | Audit | Errores |
|---|---|---|---|
| `reclassify_chromosome(sample, chromo, target_class, actor)` | `predicted_class=target`, `resolution_status=RESOLVED` | `CORRECT_CLASS` `{from,to}` | `InvalidClassError` (clase ∉ 1..22/X/Y), `SameClassError` (target == actual) |
| `split_chromosome(sample, chromo, actor)` | crea 2º `Chromosome` (misma clase, `position_index` siguiente, bbox mitad derecha; el original toma la mitad izquierda) | `SPLIT` `{origin, created}` | — |
| `join_chromosomes(sample, keep, absorbed, actor)` | `keep.bbox = unión`; `absorbed.is_active=False` | `JOIN` `{kept, absorbed}` | `JoinSelfError` (mismo id), `CrossKaryotypeError` (distinto cariotipo) |
| `resolve_cross(sample, chromo, actor)` | `resolution_status=RESOLVED` (individualizado) | `RESOLVE_CROSS` `{predicted_class}` | — |

**Case-lock (BR-003 / FSD-UC-004):** las 4 operaciones rechazan `409 CASE_LOCKED`
si `sample.status ∈ {ANALYST_VALIDATED, VALIDATED}` (el caso ya salió del analista).
Se implementa con un guard `_assert_editable(sample)` reutilizado.

### 2.3 Endpoints (scope RN-06 owner/staff, permiso `sample.edit`)
| Método | URL | Servicio |
|---|---|---|
| POST | `/samples/{id}/chromosomes/{cid}/reclassify/` (body `{target_class}`) | reclassify |
| POST | `/samples/{id}/chromosomes/{cid}/split/` | split |
| POST | `/samples/{id}/chromosomes/{cid}/join/` (body `{other_id}`) | join |
| POST | `/samples/{id}/chromosomes/{cid}/cross/` | resolve_cross |

Errores: `400 INVALID_CLASS` / `400 SAME_CLASS` / `400 JOIN_SELF` /
`409 CASE_LOCKED` / `404 CHROMOSOME_NOT_FOUND` / `403 NOT_OWNER`.

## 3. Frontend (Konva.js)

- **Dependencias nuevas:** `konva` + `react-konva` (React 18). Es la primera
  adopción del canvas canónico de CLAUDE.md (ADR-0006/0021 D4).
- **`lib/karyoLayout.ts` (puro, 100% testeable):** `slotOrigin(slot)`,
  `chromosomePosition(chromo)`, `slotAtPoint(x,y)` (mapea coordenada→slot para
  el drop del drag & drop), `reclassifyTargetFromDrop(x,y,chromo)`.
- **`components/KaryotypeCanvas.tsx`:** `Stage/Layer/Group` con un rect por
  cromosoma (color = semáforo, resalte = seleccionado/`joinPick`, guiones =
  anomalía). Props: `chromosomes`, `selectedId`, `joinPickId`, `editable`,
  `onSelect`, `onReclassify`. El `Group` de cada cromosoma es `draggable`
  (salvo caso validado); `onDragEnd` usa `reclassifyTargetFromDrop`. Conserva
  los `data-testid` `karyotype-viewer` y `chromosome-{id}` para no romper specs
  P1/P2. **Solo maneja seleccionar + reclasificar-por-drag** — el canvas no
  lleva estado de herramientas.
- **Acciones P3 en el panel de propiedades (DOM, no canvas):** separar, unir
  (dos pasos con `joinPick`), resolver cruce y "Mover a par" (reclasificar por
  `<select>`) viven en `ChromosomePropertiesPanel` como fallback accesible y
  E2E-robusto (evita depender de clics por coordenadas sobre el canvas). Se
  activan pasando los callbacks P3; sin ellos el panel es P1/P2 (compat).
- **`hooks/useKaryotypeActions.ts`:** +`reclassify`, `split`, `join`,
  `resolveCross` (misma invalidación de `['clinic','karyotype',id]` y audit).
- **`pages/KaryotypePage.tsx`:** canvas + panel; estado `joinPick` (primer
  fragmento elegido para unir). Reclasificar por drag en el canvas **o** por
  "Mover a par" en el panel. Las acciones se ocultan si el caso está
  `validated` (paridad P2).

### Testabilidad Konva (RN-09 ≥90%)
`react-konva` no renderiza en jsdom (usa canvas). Se mockea **globalmente** en
`tests/setup.ts` (`vi.mock('react-konva')`) con primitivas que renderizan `<div>`
DOM conservando `data-testid`/`onClick`; el drag & drop se dispara en tests vía
un evento sintético (`globalThis.__konvaDrop`). La geometría real se valida en
E2E (Chromium). La lógica dura vive en `lib/karyoLayout.ts` (puro, 100%).

## 4. Tests
**Backend** (`test_karyotype_p3.py`): reclassify (ok + audit CORRECT_CLASS,
INVALID_CLASS, SAME_CLASS, resuelve naranja); split (crea 2º, bbox partido,
audit); join (soft-remove, bbox unión, JOIN_SELF, audit); cross (RESOLVED,
audit); case-lock 409 tras ANALYST_VALIDATED; cadena de audit intacta; permisos.

**Frontend:** `karyoLayout.spec.ts` (puro: slotAtPoint, reclassifyTargetFromDrop),
`karyotypeCanvas.spec.tsx` (select por click, drag→reclassify vía mock),
`chromosomePropertiesPanel` (acciones P3: reclassify/split/join/cross),
`karyotypeP3.spec.tsx` (page: reclasificar por drag y por "Mover a par",
separar, unir dos fragmentos, resolver cruce, bitácora refleja los eventos).

## 5. MSW / seed
Handlers de los 4 endpoints con estado mutable (reclassify muta clase+resolución;
split agrega cromosoma; join marca `is_active=false` y recalcula; cross marca
RESOLVED). `recomputeSummary` filtra `is_active`. `buildMockKaryotype` agrega
`is_active: true`.
