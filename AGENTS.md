# AGENTS.md — BIOMED UMSS Intelligent Karyotyping Platform
## Contrato Funcional para Agentes IA (Claude · Cursor · Copilot)

**Versión:** v1.0 | **Fecha:** Mayo 2026 | **Grupo:** G04
**Autor:** Ing. Guillermo Mamani Chambi | **Estado:** Aprobado

> **Regla de oro:** Este archivo es la fuente de verdad para cualquier agente IA que trabaje en este repositorio. Si una decisión arquitectónica no está aquí o en los docs/ referenciados, no existe y no debe asumirse.

---

## 1. Identidad del Producto

| Campo | Valor |
|:---|:---|
| **Nombre** | BIOMED UMSS – Intelligent Karyotyping Platform |
| **Tipo** | Plataforma web SaaS de Inteligencia Aumentada |
| **Dominio** | Citogenética clínica — diagnóstico de cromosomas |
| **Propósito** | Reducir el Time to Karyotype (TTK) de 45 min a ≤15 min con Human-in-the-loop |
| **URL prototipo** | https://guillemc92.github.io/karyoumss/ |
| **Branch entrega** | `release/1.0.0` |

---

## 2. Stack Tecnológico Autoritativo

```yaml
frontend:
  framework: React 18 + Vite 5
  canvas: Konva.js 9          # Manipulación drag&drop de cromosomas
  state: Zustand               # Estado global de la mesa de edición
  language: TypeScript 5

backend:
  framework: FastAPI (Python 3.11+)
  auth: JWT + OAuth2 + MFA (TOTP)
  websocket: FastAPI nativo + asyncio
  queue: Redis 7 + Celery 5

ai_engine:
  serving: TorchServe 0.12+ / NVIDIA Triton
  segmentation: U-Net (PyTorch 2.0+)        # Segmentación semántica cromosómica
  classification: EfficientNet-B3             # Clasificación pares 1-22, X, Y
  xai: Grad-CAM                              # Saliency maps para explicabilidad
  confidence_threshold: 0.85                 # Umbral crítico — no negociable

database:
  primary: PostgreSQL 15+    # Datos clínicos + audit trail ACID
  broker: Redis 7             # Cola de tareas + pub/sub WebSocket
  storage: S3 / MinIO         # Imágenes metafase >10MB

infrastructure:
  containers: Docker + Docker Compose
  scaling: docker compose scale celery_worker=N
  gpu: NVIDIA (mínimo 8GB VRAM)
```

---

## 3. Reglas de Negocio — Invariantes CRÍTICOS

> ⚠️ El agente NUNCA debe generar código que viole estas reglas. Son no-negociables.

```
RN-01: Ningún informe puede emitirse sin:
        (a) validación manual del analista de TODOS los cromosomas naranjas
        (b) firma digital del supervisor (MFA obligatorio)

RN-02: Cromosomas con confidence_score < 0.85 SIEMPRE bloquean la exportación
        del informe hasta ser revisados y aceptados manualmente.

RN-03: NUNCA se transmiten datos de paciente (PII) fuera del entorno local.
        El CHN Anonymizer se ejecuta ANTES de cualquier llamada a servicios cloud.
        Formato CHN: CHN-YYYY-MM-DD-NNNN (ej: CHN-2026-05-13-0001)

RN-04: El campo ISCNNomenclature es READ-ONLY después de generado.
        Ningún endpoint debe permitir PATCH sobre iscn_nomenclature.

RN-05: La tabla `edits` es INALTERABLE.
        Solo INSERT. REVOKE UPDATE, DELETE al rol de aplicación.
        Cada edición humana → registro con timestamp, user_id (del JWT, nunca del body).

RN-06: El Supervisor y el Analista NO pueden ser el mismo usuario en casos críticos.

RN-07: El sistema opera en "modo degradado elegante" si la IA falla:
        permite análisis manual puro sin bloquear al especialista.

RN-08: Auditoría aleatoria del 5% de cromosomas con score ≥ 86% (anti-sesgo).
        El supervisor revisa este 5% incluso si fueron marcados como "verde".
```

---

## 4. Arquitectura — Decisiones Firmadas (ADRs)

| ADR | Decisión | Archivo |
|:---|:---|:---|
| ADR-0001 | Tiling 1024×1024 con overlap 64px + NMS para imágenes >4K | `docs/adr/0001-tiling.md` |
| ADR-0002 | Pipeline asíncrono Redis+Celery (no síncrono, no Kafka) | `docs/adr/0002-async-pipeline.md` |
| ADR-0003 | CHN Anonimización en el borde antes de transmisión cloud | `docs/adr/0003-chn-anonymization.md` |

**Regla para el agente:** Si se te pide cambiar estas decisiones, solicita confirmación explícita del arquitecto y documenta el nuevo ADR antes de codificar.

---

## 5. Estructura del Proyecto

```
karyoumss/
├── AGENTS.md                    # Este archivo — fuente de verdad para agentes
├── .cursorrules                 # Reglas específicas para Cursor Agent
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── EditorCanvas/    # Mesa de edición Konva.js + semáforo
│   │   │   ├── ChromosomeList/  # Lista de revisión con filtro <85%
│   │   │   ├── SampleUpload/    # Carga + validación de imagen
│   │   │   └── ReportViewer/    # Visualización informe ISCN
│   │   ├── store/               # Zustand stores (chromosome, sample, auth)
│   │   ├── services/            # API calls + WebSocket client
│   │   └── types/               # TypeScript interfaces
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI routers (samples, chromosomes, reports)
│   │   ├── core/                # Config, auth JWT, CHN anonymizer
│   │   ├── domain/              # Aggregates: Sample, Chromosome, Report
│   │   ├── services/            # Use cases: CreateSample, Validate, GenerateReport
│   │   ├── tasks/               # Celery tasks: segmentation, classification
│   │   ├── ws/                  # WebSocket manager + event publisher
│   │   └── db/                  # SQLAlchemy models + repositories
│   └── tests/
├── ai_engine/
│   ├── models/                  # U-Net + EfficientNet-B3 + Grad-CAM
│   ├── pipeline/                # CLAHE → segmentación → clasificación → XAI
│   └── serving/                 # TorchServe config + model archive
├── docs/
│   ├── BRD_v3.5.md
│   ├── MRD_v1.md
│   ├── PRD_v2.md
│   ├── FSD_v2.md
│   ├── PROMPT_MAPPINGS.md
│   ├── dti/DTI_borrador.md
│   ├── diagrams/                # Diagramas Mermaid .mmd
│   ├── adr/                     # Architecture Decision Records
│   └── aportes/                 # Contribuciones individuales
└── docker-compose.yml
```

---

## 6. Modelo de Datos — Entidades Core

```python
# Sample (Aggregate Root)
Sample:
  id: UUID (PK)
  chn_code: str (UNIQUE, format: CHN-YYYY-MM-DD-NNNN)
  s3_path: str
  status: Enum["queued","processing","ready","pending_validation",
               "pending_signature","emitido","error"]
  analyst_id: UUID (FK → users)
  created_at: datetime
  processed_at: datetime | None

# Chromosome (Entity)
Chromosome:
  id: UUID (PK)
  sample_id: UUID (FK → samples)
  pair_number: int  # 1-22, 23=X, 24=Y
  confidence_score: float  # Softmax output — NO redondear
  polygon_coords: JSON  # GeoJSON-like array
  requires_review: bool  # True si score < 0.85
  validated: bool
  validated_by: UUID | None (FK → users)
  validated_at: datetime | None

# EditTrail (Entity — INALTERABLE)
EditTrail:
  id: UUID (PK)
  chromosome_id: UUID (FK)
  user_id: UUID (FK — siempre del JWT, nunca del body)
  action: Enum["rotate","move","split","merge","reclassify","validate"]
  before_state: JSON
  after_state: JSON
  created_at: datetime  # DEFAULT NOW() — no recibir del cliente

# Report (Aggregate Root)
Report:
  id: UUID (PK)
  sample_id: UUID (FK — UNIQUE)
  iscn_nomenclature: str  # READ ONLY después de creado
  status: Enum["pending_validation","pending_signature","emitido"]
  signed_by: UUID | None (FK → users)
  signed_at: datetime | None
```

---

## 7. API Contracts — Endpoints Principales

```
POST   /api/v1/samples                    → 202 Accepted {sample_id, chn_code, task_id}
GET    /api/v1/samples/{id}               → SampleDetail
POST   /api/v1/samples/{id}/image         → 202 Accepted (inicia pipeline IA)
GET    /api/v1/samples/{id}/chromosomes   → List[ChromosomeDetail]
PATCH  /api/v1/chromosomes/{id}/validated → {all_validated: bool, remaining: int}
PATCH  /api/v1/chromosomes/{id}/position  → ChromosomeDetail (registra en edits)
POST   /api/v1/reports                    → 201 Created {report_id, iscn}
POST   /api/v1/reports/{id}/sign          → 200 OK {status: "emitido", signed_at}
GET    /api/v1/samples/{id}/audit-trail   → List[EditTrail]
WS     /ws/samples/{id}                   → WebSocket push events
```

**Regla para el agente:** Nunca cambiar el contrato de respuesta sin actualizar PROMPT_MAPPINGS.md y FSD_v2.md.

---

## 8. Flujo de Pipeline IA (Secuencia Obligatoria)

```
Imagen TIFF/PNG (>10MB)
  ↓ Validación formato + tamaño
  ↓ CHN Anonymizer (ANTES de cualquier transmisión)
  ↓ Upload a S3 (path: {chn_code}/{timestamp}.tiff)
  ↓ Enqueue en Redis {sample_id, s3_path, chn_code}
  ↓ FastAPI → 202 Accepted
  
  [Celery Worker — background]
  ↓ Download imagen de S3
  ↓ CLAHE preprocessing (clipLimit=3.0, tileGridSize=8x8)
  ↓ Tiling 1024×1024 con overlap 64px (si imagen >4K)
  ↓ U-Net → segmentación → polígonos + bounding boxes
  ↓ NMS (Non-Maximum Suppression) para bordes de tiles
  ↓ EfficientNet-B3 → clasificación batch×16 → pair + confidence_score
  ↓ Grad-CAM → saliency map por cromosoma (activable por demanda)
  ↓ Persist 46 chromosomes en PostgreSQL
  ↓ Redis PubSub → WebSocket push "Borrador listo" al cliente
```

---

## 9. Skills Disponibles para el Agente

| Skill | Comando | Descripción |
|:---|:---|:---|
| **notebooklm** | `/notebooklm` | Consultar notebooks de investigación (Biomed M4, Evaluación Docente) |
| **meta-ads** | `/meta-ads` | Gestión de campañas Facebook/Instagram para marketing de BIOMED |
| **find-skills** | `/find-skills` | Buscar e instalar nuevos skills del ecosistema |
| **security-review** | `/security-review` | Revisar seguridad del código antes de push |
| **simplify** | `/simplify` | Refactorizar código para reducir complejidad |

---

## 10. Restricciones para el Agente — LO QUE NUNCA DEBES HACER

```
❌ Generar código que transmita PII a servicios externos (viola RN-03)
❌ Crear endpoints PATCH sobre iscn_nomenclature (viola RN-04)
❌ Permitir UPDATE o DELETE en tabla edits (viola RN-05)
❌ Omitir el CHN Anonymizer en cualquier flujo que acceda a TorchServe/S3
❌ Redondear confidence_score antes de persistirlo en DB
❌ Asumir que analista == supervisor (verificar en firma de informes críticos)
❌ Usar Mask R-CNN o ResNet50 — los modelos definitivos son U-Net + EfficientNet-B3
❌ Generar código de diagnóstico autónomo sin revisión humana (prohibido por BRD)
❌ Pushear a main directamente — usar PRs con review
❌ Modificar ADRs sin crear un nuevo documento ADR primero
```

---

## 11. Trazabilidad Documental

```
BRD_v3.5.md          → Qué necesita el negocio
  └── MRD_v1.md       → Qué pide el mercado
       └── PRD_v2.md  → Qué hace el producto (User Stories + Gherkin)
            └── FSD_v2.md → Cómo lo implementa (casos de uso técnicos)
                 ├── PROMPT_MAPPINGS.md → Trazabilidad Requerimiento→Prompt→Código
                 ├── docs/diagrams/     → Diagramas Mermaid por UC
                 └── docs/dti/          → DTI con C4 Niveles 1-3 + ADRs
```

**Métricas AI-SDLC:**
- **Prompt Coverage:** % de User Stories del PRD con al menos 1 PM en PROMPT_MAPPINGS → Target ≥ 80%
- **Spec Fidelity:** % de contratos API del FSD implementados con firma exacta → Target ≥ 95%
- **Gherkin Coverage:** % de casos de uso críticos con escenarios Gherkin verificables → Target ≥ 100%

---

## 12. Cómo Contribuir (Para el Agente)

1. **Antes de codificar:** Verificar que existe un PM en PROMPT_MAPPINGS.md para la tarea
2. **Naming conventions:** `snake_case` Python · `camelCase` TypeScript · `kebab-case` archivos
3. **Cada PR debe:** Actualizar PROMPT_MAPPINGS.md + agregar test + pasar linter
4. **Commits:** `feat:` `fix:` `docs:` `test:` `refactor:` según conventional commits
5. **Branch:** trabajar en `feature/<nombre>` → PR a `release/1.0.0`

*AGENTS.md v1.0 — Fuente de verdad para Claude, Cursor Agent, Copilot y agentes custom*
*Actualizar este archivo ante cualquier cambio arquitectónico significativo*
