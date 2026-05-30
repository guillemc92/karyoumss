---
name: skill-read-context
description: >-
  Lee e interpreta requerimientos funcionales del repositorio KaryouMSS (PRD, FSD,
  BRD, AGENTS.md): extrae actores, casos de uso, user stories, pre/postcondiciones,
  reglas de negocio y valida completitud. Usar cuando el usuario pide leer contexto
  de specs, Skill_Read_Context, interpretar FSD-UC, o antes de implementar sin inventar requisitos.
allowed-tools:
  - read
  - run
model-tier: sonnet
fsd-version-min: v0.1
status: stable
owner: KaryouMSS Core Agent — G04 BIOMED UMSS
---

# Skill: Skill_Read_Context

**Convención KaryouMSS:** carpeta `.cursor/skills/skill-read-context/`. Copia opcional a `~/.cursor/skills/skill-read-context/` para alcance global.

## 1. Cuándo activarlo (triggers)

- **DURANTE:** planificación de implementación, trazabilidad PM, revisión de specs, onboarding de agentes.
- **ARRANCA cuando:** el usuario invoca `Skill_Read_Context`, `@skill-read-context`, o pide "leer/interpretar requerimientos", "contexto del FSD/PRD", o cita `docs/fsd/FSD_vFinal.md` / `docs/prd/PRD_vFinal.md` sin pegar el fragmento.
- **NO ACTIVAR cuando:** el usuario solo pide código sin spec y rechaza leer documentos; o el artefacto es puramente de marketing (meta-ads).

## 2. Parámetros de entrada (Inputs)

| Parámetro | Tipo | Obligatorio | Descripción |
|-----------|------|-------------|-------------|
| `file_path` | `string` (ruta) | Sí* | Ruta al artefacto. Default del repo: `docs/fsd/FSD_vFinal.md`, `docs/prd/PRD_vFinal.md`, `docs/brd/BRD_vFinal.md`, `AGENTS.md` |
| `format` | `enum` | No | `auto` \| `markdown` \| `md` (default: `auto`) |
| `detail_level` | `enum` | No | `summary` \| `standard` \| `full` (default: `standard`) |
| `uc_id` | `string` | No | Filtrar un UC concreto, ej. `FSD-UC-002` (post-proceso sobre JSON) |
| `us_id` | `string` | No | Filtrar user story, ej. `US-02` |

\*Si falta `file_path`, pedir: *"Indica la ruta del artefacto (ej. docs/fsd/FSD_vFinal.md) o el ID FSD-UC-NNN."*

### Fuentes de verdad (precedencia)

1. Fragmento citado por el usuario (UC / US / BR / Gherkin).
2. Salida JSON del script `scripts/read_context.py` (no inventar campos extra).
3. `AGENTS.md` (RN-01…RN-08) al cruzar reglas de negocio.
4. `docs/PROMPT_MAPPING.md` para trazabilidad PM.

## 3. Lógica de procesamiento (Procedimiento)

1. **Validar entrada:** archivo existe y extensión `.md` (o formato declarado).
2. **Ejecutar parser** (preferido — datos verificables):

```bash
python .cursor/skills/skill-read-context/scripts/read_context.py docs/fsd/FSD_vFinal.md --detail standard
```

3. **Interpretar JSON:** resumir en lenguaje técnico; mapear IDs a capas (`backend/app/`, `frontend/src/`) según `AGENTS.md`.
4. **Validar integridad:** revisar `validation.completeness_score` e `validation.issues`; si `is_valid` es false, **STOP** e informar gaps antes de codificar.
5. **Cruzar invariantes:** contrastar `business_rules` / `invariants` con RN de `AGENTS.md`; reportar contradicciones (no resolverlas por cuenta propia).

### Extracción por tipo de documento

| Tipo | Extrae |
|------|--------|
| **FSD** | `FSD-UC-NNN`, actores, pre/postcondiciones, flujo principal, BR aplicables, Gherkin (`full`) |
| **PRD** | `US-NN`, actor, criterios BDD inline, BR-NN |
| **BRD** | Reglas de negocio narrativas |
| **AGENTS** | `RN-NN` invariantes operativos |

## 4. Salida esperada

### 4.1 Formato JSON (contrato)

```json
{
  "meta": {
    "source_file": "absolute/path",
    "doc_type": "FSD|PRD|BRD|AGENTS|UNKNOWN",
    "detail_level": "standard",
    "parsed_at": "ISO-8601 UTC"
  },
  "actors": [{ "name": "...", "type": "humano|sistema|agente IA" }],
  "use_cases": [{
    "id": "FSD-UC-001",
    "title": "...",
    "main_actor": "...",
    "preconditions": ["..."],
    "postconditions": ["..."],
    "actions": ["..."],
    "business_rules": ["BR-001"],
    "gherkin": []
  }],
  "user_stories": [{
    "id": "US-01",
    "actor": "...",
    "story": "...",
    "acceptance": "...",
    "gherkin": { "given": null, "when": null, "then": null },
    "priority": "Must"
  }],
  "business_rules": [{ "id": "BR-01", "description": "..." }],
  "invariants": [{ "id": "RN-01", "description": "..." }],
  "nfrs": ["NFR-01"],
  "validation": {
    "completeness_score": 0.95,
    "is_valid": true,
    "issues": [{ "code": "...", "message": "...", "severity": "warning|error" }]
  }
}
```

### 4.2 Resumen para el agente (markdown breve)

Tras el JSON, emitir:

- **Alcance leído:** doc + UC/US IDs
- **Actores implicados**
- **Reglas críticas** (BR + RN)
- **Bloqueadores de implementación** (`validation.issues` con severity `error`)

## 5. Manejo de errores

| Código | Causa | Acción del agente |
|--------|-------|-------------------|
| `FILE_NOT_FOUND` | Ruta inválida | Pedir ruta correcta; listar `docs/*.md` disponibles |
| `UNSUPPORTED_FORMAT` | No es `.md` | Convertir a Markdown o usar `--format markdown` tras conversión |
| `MISSING_USE_CASES` | FSD sin `FSD-UC-NNN` | Verificar normalización del MD; pedir sección §4 al autor del FSD |
| `INCOMPLETE_UC` | UC sin precondiciones/flujo | **STOP** — no implementar; escalar spec |
| `PARSE_ERROR` | MD corrupto/encoding | Revisar UTF-8; re-exportar documento |
| Contradicción BR vs RN | Spec inconsistente | **STOP** — abrir issue; citar ambos IDs |

Exit codes del script: `0` OK, `2` warnings/invalidación, `1` error fatal.

## 6. Dependencias

| Dependencia | Versión | Notas |
|-------------|---------|-------|
| Python | 3.11+ | Ejecución del parser |
| Biblioteca estándar | — | `re`, `json`, `argparse`, `pathlib` — **sin pip install** |
| Artefactos repo | — | `docs/fsd/FSD_vFinal.md`, `docs/prd/PRD_vFinal.md`, `AGENTS.md` |

## 7. Verificación (criterios de "bien hecho")

- Toda afirmación sobre requisitos cita `id` del JSON (`FSD-UC-xxx`, `US-xx`, `BR-xx`, `RN-xx`).
- Cero requisitos inventados: huecos → `TODO(spec)` explícito.
- `completeness_score` documentado en el resumen.
- Cruce con `AGENTS.md` §3 cuando la tarea toque PII, 0.85, audit trail o IA.

## 8. Anti-patrones

- Resumir el FSD de memoria sin ejecutar lectura del archivo.
- Asumir umbrales o modelos no presentes en el doc leído.
- Ignorar `validation.issues` con severity `error`.
- Mezclar requisitos de `PRD_v1` y `PRD_vFinal` sin declarar versión.

## 9. Ejemplos de invocación

### Ejemplo 1 — Contexto completo del FSD

```
@skill-read-context Lee docs/fsd/FSD_vFinal.md con detail standard y resume los UC críticos para el pipeline IA.
```

```bash
python .cursor/skills/skill-read-context/scripts/read_context.py docs/fsd/FSD_vFinal.md --detail standard
```

### Ejemplo 2 — Solo user stories del PRD (resumen)

```
Skill_Read_Context: interpreta docs/prd/PRD_vFinal.md nivel summary para listar US Must-have.
```

```bash
python .cursor/skills/skill-read-context/scripts/read_context.py docs/prd/PRD_vFinal.md --detail summary -o /tmp/prd_context.json
```

### Ejemplo 3 — Invariantes antes de implementar auth

```
Antes de codificar JWT, ejecuta Skill_Read_Context sobre AGENTS.md y cruza RN-05 con FSD-UC-005.
```

```bash
python .cursor/skills/skill-read-context/scripts/read_context.py AGENTS.md --detail full
```

## 10. Modos de fallo conocidos

- `FSD_vFinal.md` con escapes `\#` → el script normaliza; si falla, pedir export limpio.
- Tablas US rotas (pipes desalineados) → `MISSING_USER_STORIES` warning.
- BR duplicados (`BR-01` vs `BR-001`) → listar ambos; no fusionar sin confirmación.

## 11. Registro de cambios del Skill

| Versión | Fecha | Autor | Cambio |
|---------|-------|-------|--------|
| 1.0.0 | 22/05/2026 | KaryouMSS Core Agent | Migración desde `md/SKILL_TEMPLATE`; parser JSON + SKILL.md |
