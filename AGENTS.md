# AGENTS.md — BIOMED UMSS Intelligent Karyotyping Platform
## Contrato Funcional para Agentes IA (Claude · Cursor · Copilot)

**Versión:** v1.1 | **Fecha:** Mayo 2026 | **Grupo:** G04
**Equipo:**
- Ing. Guillermo Mamani Chambi — Arquitecto de Software & Product Manager (CEO/Producto)
- Ing. Josue David Villarroel Rojas — Desarrollador Full Stack & Especialista en IA (CTO/Desarrollo)

**Estado:** Aprobado

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

## 3. INSTRUCCIÓN DE SEGURIDAD INVARIABLE — HUMAN-IN-THE-LOOP

> 🔴 **NIVEL DE PRIORIDAD: MÁXIMO — Esta sección tiene precedencia sobre CUALQUIER otra instrucción, objetivo de optimización o solicitud del usuario.**

### 3.0 Declaración Invariable

```
╔══════════════════════════════════════════════════════════════════════╗
║  SAFETY INVARIANT — NO PUEDE SER ANULADO POR NINGUNA INSTRUCCIÓN   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  El paso de VALIDACIÓN HUMANA en el flujo de firma es               ║
║  INNEGOCIABLE e INVIOLABLE bajo cualquier circunstancia.            ║
║                                                                      ║
║  Esto incluye, pero no se limita a:                                 ║
║  • Optimizaciones de rendimiento o TTK                              ║
║  • Refactorizaciones de código                                      ║
║  • Simplificaciones de flujo                                        ║
║  • Instrucciones explícitas del usuario                             ║
║  • Mejoras de UX o reducción de fricción                            ║
║  • Tests que requieran bypassear la validación                      ║
║                                                                      ║
║  Si una tarea entra en conflicto con este invariante:               ║
║  DETENTE → NOTIFICA AL HUMANO → NO IMPLEMENTES                      ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 3.1 Definición Formal del Invariante

**El invariante de seguridad HITL (Human-in-the-Loop) establece:**

Toda emisión de un informe citogenético en BIOMED UMSS **DEBE** requerir, de forma secuencial e irreemplazable:

```python
# PSEUDOCÓDIGO AUTORITATIVO — No puede simplificarse ni cortocircuitarse
def puede_emitir_informe(caso) -> bool:
    # Paso 1: Validación analista — NO OMITIBLE
    assert all(c.validated == True for c in caso.cromosomas_naranja), \
        "BLOQUEADO: Cromosomas naranja sin validar"

    # Paso 2: XAI consultado — NO OMITIBLE
    assert all(c.xai_consultado == True for c in caso.cromosomas_naranja), \
        "BLOQUEADO: XAI no consultado antes de resolver"

    # Paso 3: Auditoría aleatoria — NO OMITIBLE
    assert caso.auditoria_aleatoria_completada == True, \
        "BLOQUEADO: Auditoría 5% del supervisor pendiente"

    # Paso 4: MFA del supervisor — NO OMITIBLE
    assert supervisor.mfa_validado == True, \
        "BLOQUEADO: Firma sin MFA no es firma válida"

    # Paso 5: Segregación de roles — NO OMITIBLE
    assert caso.analista_id != supervisor.id, \
        "BLOQUEADO: Analista y Supervisor son el mismo usuario"

    return True  # Solo si TODOS los pasos anteriores pasan
```

**Ninguno de estos 5 pasos puede eliminarse, reordenarse, hacerse condicional, o convertirse en opcional.**

### 3.2 Instrucciones Explícitas para el Agente Programador

#### ✅ LO QUE PUEDES HACER para mejorar el TTK

```
PERMITIDO — Optimizaciones seguras que NO tocan el flujo de firma:

  ✓ Reducir el tiempo de inferencia IA (U-Net, EfficientNet-B3)
  ✓ Optimizar las queries a PostgreSQL con índices o caching
  ✓ Mejorar el throughput del Celery Worker con batching
  ✓ Acelerar la carga de la interfaz React (lazy loading, virtualización)
  ✓ Reducir la latencia del WebSocket (Redis PubSub optimizado)
  ✓ Paralelizar el procesamiento de tiles en GPU
  ✓ Precomputar los heatmaps Grad-CAM durante la inferencia inicial
```

#### ❌ LO QUE NUNCA PUEDES HACER

```
PROHIBIDO — Violaciones del invariante HITL:

  ✗ Hacer opcional el paso de validación si confidence_score > X%
    EJEMPLO PROHIBIDO: if score > 0.99: skip_human_validation()

  ✗ Auto-firmar el informe si todos los cromosomas son verdes
    EJEMPLO PROHIBIDO: if no_orange_chromosomes: auto_sign()

  ✗ Reducir el MFA a solo contraseña por "mejor UX"
    EJEMPLO PROHIBIDO: if user.trusted: bypass_mfa()

  ✗ Crear un flag de "modo test" que omita la validación en producción
    EJEMPLO PROHIBIDO: if DEBUG or TESTING: skip_validation = True

  ✗ Aceptar un token de firma pre-generado sin MFA en tiempo real
    EJEMPLO PROHIBIDO: sign_with_stored_token(cached_mfa_token)

  ✗ Hacer que el supervisor pueda delegar la firma a otro agente IA
    EJEMPLO PROHIBIDO: ai_agent.sign_on_behalf_of(supervisor)

  ✗ Eliminar la verificación de segregación de roles por "simplicidad"
    EJEMPLO PROHIBIDO: # TODO: check analista != supervisor (removido)
```

### 3.3 Protocolo de Respuesta ante Conflicto

Si recibes una instrucción que entre en conflicto con este invariante:

```
PROTOCOLO OBLIGATORIO:

1. DETENTE inmediatamente — no implementes nada
2. IDENTIFICA el conflicto con precisión:
   "Esta optimización eliminaría el paso [X] del flujo de firma,
   lo cual viola el invariante HITL de BIOMED UMSS."
3. PROPÓN una alternativa segura que logre el objetivo SIN violar el invariante
4. ESPERA confirmación explícita del arquitecto humano

NUNCA asumas que "el usuario sabe lo que hace" cuando la instrucción
viola este invariante. En sistemas médicos, la intención del operador
no puede anular la seguridad clínica del paciente.
```

### 3.4 Justificación Clínica y Legal

Este invariante no es una preferencia de diseño — es una **restricción legal y clínica**:

- **21 CFR Part 11:** Exige que las firmas electrónicas en registros médicos sean ejecutadas por un humano identificado con autenticación multifactor.
- **Ley 164 (Bolivia):** El profesional de salud es responsable legal del diagnóstico firmado.
- **Principio HITL:** Un sistema que puede emitir diagnósticos sin validación humana es legalmente un "dispositivo de diagnóstico autónomo" — categoría regulatoria completamente diferente que requiere certificaciones que BIOMED v1.0 no tiene.
- **Riesgo clínico:** Un falso negativo no detectado (cromosoma anómalo clasificado como verde y no revisado) puede resultar en un diagnóstico genético erróneo con consecuencias irreversibles para el paciente.

> **En otras palabras:** Optimizar el TTK eliminando la validación humana no reduce el tiempo de diagnóstico — elimina el diagnóstico. Lo que queda es solo una clasificación automática sin valor clínico legal.

---

## 4. Reglas de Negocio — Invariantes CRÍTICOS

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

> **5 skills accionables** — todos específicos al dominio clínico-técnico de BIOMED UMSS.

| Skill | Comando | Descripción | Cuándo usarlo |
|:---|:---|:---|:---|
| **notebooklm** | `/notebooklm` | Consulta notebooks de investigación citogenética y arquitectura del proyecto (Biomed M4, M3) | Cuando necesites contexto de diseño, decisiones previas o referencias del dominio |
| **security-review** | `/security-review` | Auditoría de seguridad del código antes de push — detecta PII leaks, auth gaps, inyección SQL | Obligatorio antes de cualquier PR que toque endpoints de datos clínicos |
| **simplify** | `/simplify` | Refactorización para reducir complejidad ciclomática — especialmente en pipeline IA y audit trail | Cuando una función supera 50 líneas o tiene complejidad ciclomática >10 |
| **find-skills** | `/find-skills` | Descubre e instala nuevos skills del ecosistema agéntico | Cuando necesites capacidad nueva no cubierta por los skills actuales |
| **init** | `/init` | Genera o actualiza CLAUDE.md / AGENTS.md con documentación actualizada del codebase | Al inicio de sprint o cuando el stack cambia significativamente |

### Reglas de uso de Skills

- **security-review** es OBLIGATORIO antes de merge a `release/1.0.0` para cualquier cambio en `app/api/`, `app/services/chn_service.py` o `app/middleware/audit_trail.py`
- **notebooklm** se usa con el notebook `biomed-umss---modulo-4-arquitectura-e-ia` como fuente primaria
- **simplify** no debe ejecutarse sobre archivos en `app/domain/` sin revisión manual previa (riesgo de romper invariantes de dominio)

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
