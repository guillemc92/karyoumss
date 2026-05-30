# Defensa Final — Checklist de Preparación (G04)

**Rama evaluada:** `release/2.0.0`  
**Repositorio:** https://github.com/guillemc92/karyoumss/tree/release/2.0.0

## 1. Entrega `release/2.0.0`
- [x] Todo el contenido crítico está en el branch `release/2.0.0`.
- [x] `docs/DTI.md` — 24 secciones (§0–§23), vFinal v2.0.
- [x] `docs/fsd/FSD_vFinal.md`, `docs/prd/PRD_vFinal.md`, `docs/mrd/MRD_vFinal.md`, `docs/brd/BRD_vFinal.md`.
- [x] `AGENTS.md` v1.2 sincronizado con rutas vFinal y ADR-0005.
- [x] `docs/PROMPT_MAPPING.md` + `prompts/PR-*.md` (mapeo rápido con métricas antes/después).
- [x] `docs/roadmap.md` con hitos post-defensa.
- [x] `docs/aportes/release-2.0.0.md` (aportes individuales).
- [x] `docs/diagrams/` — 12 archivos `.mmd` versionados.
- [x] `pocs/POC-01` … `POC-05` con `metrics.json` + README.
- [x] `docs/adr/` — ADR 0001–0005 (incluye cloud provider).

## 2. Estructura de la presentación (15 min — grupo individual)
- [ ] 0–8 %: Producto y problema (MRD/PRD) — ~1 min
- [ ] 8–25 %: FSD — 1 UC + aviso-contrato (ej. UC-02 + `prompts/PR-UC02-SEM.md`) — ~2 min
- [ ] 25–58 %: C4 L1+L2 + hexagonal del core — ~5 min
- [ ] 58–75 %: Distribuido / event-driven / AWS (ADR-0002, ADR-0005) — ~3 min
- [ ] 75–83 %: IA + agentes + barandillas (RN-02, RN-03, Grad-CAM) — ~1 min
- [ ] 83–92 %: POCs — 2–3 con métricas de `metrics.json` — ~1 min
- [ ] 92–100 %: Roadmap + riesgos — ~1 min

## 3. Presentación unificada
- [ ] Abrir `DEFENSA_MAGISTRAL.html` (13 slides + demo integrada).
- [ ] Teclas: `←` `→` slides · `N` notas del presentador · `1` `2` `3` secciones.

## 4. Demo recomendada (5 min)
- [ ] Pestaña **Corrección** en `DEFENSA_MAGISTRAL.html` (iframe al prototipo)
- [ ] O abrir: `correccion de cariotipo.html` / https://guillemc92.github.io/karyoumss/
- [ ] Mostrar semaforización / mesa de edición (UC-03 FSD).
- [ ] En GitHub: `docs/PROMPT_MAPPING.md` → símbolo RN-02 → archivo HTML.
- [ ] Opcional: `python .cursor/skills/skill-read-context/scripts/read_context.py docs/fsd/FSD_vFinal.md --detail summary`

## 5. Q&A docente (3 min) — respuestas preparadas
- [ ] Trazabilidad: MRD → PRD → FSD → DTI (misma cadena en §12 AGENTS.md).
- [ ] Trade-off ADR-0005: vendor lock-in vs Terraform; latencia us-east-1 vs costo Multi-AZ.
- [ ] RN-09 / BR-R5: bloqueo de emisión si cromosomas naranjas sin validar.

## 6. Puntos críticos de la rúbrica (auto-evaluación)
| # | Criterio | Nivel esperado | Evidencia en repo |
|---|----------|----------------|-------------------|
| 1 | Coherencia documental | Excelente | DTI 24§ + vFinal + C4 en DTI §2–§3 |
| 2 | Arquitectura + AWS | Excelente | ADR-0005 + DTI §8.4 |
| 3 | AGENTS.md | Excelente | v1.2 + skill-read-context |
| 4 | POCs ejecutadas | Excelente | 5 POCs + metrics.json |
| 5 | Defensa oral | (en vivo) | Este checklist |
| 6 | Mapeo rápido | Excelente | PROMPT_MAPPING § tabla símbolos |
| 7 | Diagramas .mmd | Excelente | 12 en `docs/diagrams/` |

## 7. Riesgos a mitigar en Q&A
- POC-01: README dice U-Net; `metrics.json` histórico Mask R-CNN → explicar evolución a U-Net (ADR/stack definitivo).
- No hay carpeta `backend/` en release → demo = prototipo HTML + documentación; sin penalización según rúbrica.
- FSD_vFinal con escapes Markdown → normalizar si el docente abre el archivo en vivo.
