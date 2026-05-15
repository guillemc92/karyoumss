# Aportes Individuales — Release 1.0.0
## BIOMED UMSS — Grupo G04

| Campo | Valor |
|:---|:---|
| **Release** | v1.0.0 |
| **Fecha de corte** | 13/05/2026 |
| **Branch evaluado** | `release/1.0.0` |
| **Integrantes** | 2 |

---

## Integrante 1: Ing. Guillermo Mamani Chambi
**Rol:** Arquitecto de Software & Product Manager · CEO/Producto

### Tareas completadas

| # | Tarea | Documento/Artefacto | Fecha |
|:---|:---|:---|:---|
| 1 | BRD v1.0 inicial | `docs/BRD.md` | May 2026 |
| 2 | BRD v2.0 refinado con mecanismos anti-sesgo | `docs/BRD_v2.md` | May 2026 |
| 3 | BRD v3.5 definitivo (XAI, 21 CFR, RACI, ROI/NPV) | `docs/BRD_v3.5.md` | May 2026 |
| 4 | MRD v1.0 (mercado, TAM/SAM/SOM, personas JTBD) | `docs/MRD_v1.md` | May 2026 |
| 5 | PRD v1.0 con 17 User Stories | `docs/PRD_v1.md` | May 2026 |
| 6 | PRD v2.0 definitivo con Constitution | `docs/PRD_v2.md` | May 2026 |
| 7 | PRD v2.1 — Constitution 5 principios + Discovery Track + Vibe Coding | `docs/PRD_v2.md` | May 2026 |
| 8 | FSD v1.0 borrador a priori | `docs/FSD_v1.md` | May 2026 |
| 9 | FSD v2.0 definitivo (U-Net, EfficientNet-B3, 10 UC, API contracts) | `docs/FSD_v2.md` | May 2026 |
| 10 | LFSD v1.0 (versión ágil y viva) | `docs/LFSD.md` | May 2026 |
| 11 | PROMPT_MAPPINGS v2.0 (10 contratos + failure modes) | `docs/PROMPT_MAPPINGS.md` | May 2026 |
| 12 | DTI v0.1 con C4 Nivel 1 | `docs/dti/DTI_borrador.md` | May 2026 |
| 13 | DTI v1.2 completo (C4 N1+N2+N3, DFD, ER, 3 ADRs) | `docs/dti/DTI_borrador.md` | May 2026 |
| 14 | AGENTS.md v1.0 completo (5 skills + guardrails) | `AGENTS.md` | May 2026 |
| 15 | .cursorrules (7 reglas de dominio clínico) | `.cursorrules` | May 2026 |
| 16 | 12 diagramas Mermaid .mmd (secuencia, estado, ER, Gantt) | `docs/diagrams/` | May 2026 |
| 17 | Métricas AI-SDLC (prompt coverage, spec fidelity, Gherkin) | `docs/metrics/ai-sdlc-metrics.md` | May 2026 |
| 18 | Prototipo HTML funcional (7 pantallas M3) | `*.html` en prototipo | May 2026 |
| 19 | Release branch 1.0.0 | `release/1.0.0` | May 2026 |
| 20 | Incorporación Ing. Josue Villarroel — onboarding y actualización docs | Todos los metadatos | May 2026 |

### Total de tareas: 20

---

## Integrante 2: Ing. Josue David Villarroel Rojas
**Rol:** Desarrollador Full Stack & Especialista en IA · CTO/Desarrollo

### Tareas completadas

| # | Tarea | Documento/Artefacto | Fecha |
|:---|:---|:---|:---|
| 1 | Revisión técnica BRD v3.5 (validación de restricciones de negocio) | `docs/BRD_v3.5.md` | May 2026 |
| 2 | Revisión PRD v2.1 — validación de User Stories desde perspectiva técnica | `docs/PRD_v2.md` | May 2026 |
| 3 | Setup del entorno de desarrollo local (Docker Compose + GPU) | `docker-compose.yml` | May 2026 |
| 4 | Revisión y validación de los 10 casos de uso del FSD v2.0 | `docs/FSD_v2.md` | May 2026 |
| 5 | Coordinación hipótesis Discovery Track S3 (XAI con analistas IIBISMED) | `docs/PRD_v2.md §Discovery` | May 2026 |
| 6 | Revisión de arquitectura C4 N2 y N3 — validación contra stack real | `docs/dti/DTI_borrador.md` | May 2026 |

### Total de tareas: 6

---

## Cálculo de factor de aporte

```
total_tareas_grupo   = 20 (Guillermo) + 6 (Josue) = 26
n_integrantes        = 2
aporte_promedio      = 26 / 2 = 13 tareas

factor_Guillermo = clamp(20 / 13, 0.5, 1.1) = clamp(1.54, 0.5, 1.1) = 1.1  → nota_grupal × 1.1
factor_Josue     = clamp( 6 / 13, 0.5, 1.1) = clamp(0.46, 0.5, 1.1) = 0.5  → nota_grupal × 0.5
```

> **Nota:** El factor reducido de Josue refleja su incorporación tardía al equipo durante el sprint final. A partir del siguiente ciclo su contribución será equiparada con el arquitecto principal.

---

## Evidencia de commits

```bash
git log --oneline release/1.0.0
```

Los commits de `release/1.0.0` son de autoría de Ing. Guillermo Mamani Chambi. Ing. Josue David Villarroel Rojas se incorporó en la fase final — sus aportes de revisión y coordinación se documentan en las reuniones del equipo y en los issues del repositorio.
