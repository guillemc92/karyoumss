# DD-ML-001 — Servicio de inferencia de cariotipado (baseline real) — Fase B

| Campo | Valor |
|---|---|
| **ID** | DD-ML-001 |
| **ADR origen** | [ADR-0007](../adr/0007-microservicio-inferencia.md) (motor de inferencia) + [ADR-0015](../adr/0015-...) (pipeline FastAPI que backend-clinic consume) |
| **FSD** | FSD-UC-001/002 (segmentación + clasificación), AGENTS.md §9 (pipeline U-Net → EfficientNet-B3 → Grad-CAM) |
| **Estado** | En implementación (baseline) |
| **Fecha** | 2026-07-24 |

## 1. Alcance
Materializar el **motor de inferencia** (`backend-ml/`, el FastAPI que
`backend-clinic.pipeline_client` ya espera en `:8000`, ADR-0015 #6). Convierte
una **imagen de metafase real** en cromosomas detectados (bbox + clase +
confianza). **Fase B (esta):** segmentación REAL (OpenCV) + clasificación
**placeholder**. El modelo entrenado (U-Net + EfficientNet-B3) se enchufa después
sin reescribir (puertos hexagonales, ADR-0007).

## 2. Diseño (hexagonal, ADR-0007)
- **`ports.py`** — `SegmenterPort.segment(gray) -> [Detection]`,
  `ClassifierPort.classify(crop, area) -> (clase, confianza)`. Interfaces para
  que el modelo entrenado reemplace los adaptadores sin tocar el pipeline/API.
- **`segmentation.py` — `OpenCVSegmenter` (REAL):** grises → Otsu invertido
  (cromosomas oscuros sobre fondo claro) → morfología → **watershed** sobre la
  transformada de distancia (separa cromosomas que se tocan) → componentes
  filtradas por área (descarta specks + el texto de los números anotados).
- **`classifier.py` — `PlaceholderClassifier` (STUB honesto):** asigna clase por
  **rango de tamaño** (heurística: pares 1→22 decrecen) con **confianza fija baja
  (0.55)** → en el visor todo cae naranja → el analista clasifica a mano (modo
  manual real, FSD-UC-007). NO es un modelo entrenado.
- **`pipeline.py`** — orquesta segmentar → clasificar → `SegmentResult`.
  `model_version = 'opencv-watershed-v0+placeholder-clf-v0'`.

## 3. API (FastAPI)
| Método | Ruta | Qué |
|---|---|---|
| GET | `/health/` | `{status, model_version, trained_model:false}` |
| POST | `/api/v1/segment/` | multipart imagen (BMP/PNG/JPG/TIFF) → `SegmentResult` (cromosomas: order, predicted_class, confidence_score, bbox, area) |

`SegmentResult.chromosomes[]` mapea al modelo `Chromosome` de backend-clinic
(ingesta directa en la Fase B2 de wiring).

## 4. Verificación
- `pytest` (11 tests): segmentación sobre imagen sintética (detecta N elipses,
  blanco→0), `load_gray` (decodifica/rechaza), placeholder por tamaño, pipeline
  (estructura completa, confianza baja), API (`/health`, `/segment`, 400/422).
- **E2E real:** `uvicorn` + POST de una metafase MetaClass real (1024×998) →
  200 → 60 cromosomas detectados (baseline sobre-segmenta en imágenes con ruido;
  el U-Net entrenado lo corrige). Segmentación real, confianza placeholder.

## 5. Fuera de alcance (siguiente)
- **Modelo entrenado** (U-Net + EfficientNet-B3) sobre el dataset MetaClass
  (`datasets/`, 460 metafases anotadas) — requiere torch + GPU + extraer las
  etiquetas visuales (OCR de los números). Reemplaza los adaptadores placeholder.
- **Grad-CAM real** (necesita CNN entrenada).
- **Fase B2 — wiring backend-clinic ↔ backend-ml:** `/api/v1/samples/{id}/process/`
  + `/status/`, almacenamiento de la imagen subida, e ingesta de resultados a las
  filas `Karyotype`/`Chromosome` reales; reemplazar el mock MSW del frontend.
