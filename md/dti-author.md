---

name: dti-author description: \> Puebla secciones del Documento Técnico Inicial (`docs/DTI.md`) siguiendo `plantillas/DOCUMENTO_TECNICO_INICIAL_TEMPLATE.md`. Mantiene sincronía atómica ADR ↔ DTI ↔ `AGENTS.md` (un cambio significativo viaja en un único commit). Activar cuando el usuario edita `docs/DTI.md` o pide explícitamente "poblar §N del DTI" / "actualizar AGENTS.md desde el DTI". allowed-tools:

- read  
- edit model-tier: sonnet fsd-version-min: v0.1 status: stable owner: docente / grupo

---

# Skill: dti-author (poblar DTI y sincronizar con AGENTS.md)

**Convención del módulo**: este skill vive en `docs/skills/dti-author.md`. Para activarlo en Claude Code, copiar a `.claude/skills/dti-author/SKILL.md` en el repo del grupo o a `~/.claude/skills/dti-author/` para alcance global del usuario.

## 1\. Cuándo activarlo (triggers)

- DURANTE: edición de `docs/DTI.md` o de un ADR en `docs/adr/`.  
- ARRANCA cuando: el usuario invoca `"@dti-author §N <tema>"` o abre `docs/DTI.md`.  
- NO ACTIVAR cuando: el usuario está definiendo capacidades de producto (PRD) o requerimientos (FSD); este skill asume que el FSD ya existe.

## 2\. Entradas obligatorias (Inputs)

El usuario MUST proporcionar al menos una de:

- Sección del DTI a poblar (`§0`–`§21`).  
- Ruta a un ADR recién creado en `docs/adr/<NNNN>-<slug>.md`.  
- Decisión arquitectónica que se quiere reflejar en el DTI \+ AGENTS.md.

Si falta cualquiera, responder: `"Necesito la sección del DTI o el ADR fuente antes de redactar."`

## 3\. Fuentes de verdad (orden de precedencia)

1. `plantillas/DOCUMENTO_TECNICO_INICIAL_TEMPLATE.md` (estructura, frontmatter, tags de audiencia).  
2. MRD, PRD y FSD vigentes (`docs/mrd/`, `docs/prd/`, `docs/fsd/`).  
3. ADRs vigentes en `docs/adr/` (decisiones que el DTI debe reflejar).  
4. `AGENTS.md` actual (estado declarado para los agentes).  
5. Convenciones de versionado y release del módulo (`release/1.0.1` para el DTI v1.0).

## 4\. Procedimiento

1. **Verificar plantilla**: leer la plantilla y confirmar que el frontmatter YAML está presente en `docs/DTI.md`. Si falta, generarlo desde la plantilla.  
2. **Identificar audiencia de la sección** (`[humano]`, `[máquina]`, `[humano+máquina]`) y respetar el estilo:  
   - `[humano]`: prosa estructurada, *trade-offs*, riesgos, *roadmap*.  
   - `[máquina]`: YAML, tablas semánticas, comandos copiables; cero prosa ambigua.  
   - `[humano+máquina]`: mezcla — narrativa breve \+ tabla o YAML al final.  
3. **Poblar la sección** con datos derivados del MRD/PRD/FSD/ADRs vigentes; cero invención.  
4. **Detectar drift**: comparar el contenido propuesto contra `AGENTS.md`. Si la decisión implica cambio para los agentes (nuevo stack, nuevo invariante, nueva ruta crítica), proponer un **diff de `AGENTS.md`** que viaje en el **mismo commit**.  
5. **Aplicar checklist de legibilidad IA** (Anexo A de S06) antes de cerrar.

## 5\. Salida esperada

- Sección del DTI poblada según la plantilla, con tag de audiencia correcto.  
- Si la sección modificó decisiones arquitectónicas significativas:  
  - Diff propuesto para `AGENTS.md` (sección afectada).  
  - Mensaje de commit sugerido en formato `docs(dti+agents): <decisión> [ADR-NNNN]`.  
- Tabla de trazabilidad obligatoria cuando aplique:

| Decisión | ADR fuente | Sección del DTI | Sección de `AGENTS.md` |
| :---- | :---- | :---- | :---- |
| Estilo monolito modular | ADR-0001 | §3.1 | `## Stack` y `## Capas` |

## 6\. Verificación (criterios de "bien hecho")

- Frontmatter YAML del DTI válido y completo (parseable sin errores).  
- Tag de audiencia consistente con el tipo de contenido de la sección.  
- Cada decisión nueva cita su ADR (`[ADR-NNNN]`); cero decisiones huérfanas.  
- `AGENTS.md` y DTI quedan coherentes en el mismo commit (verificable con `git show`).  
- Cero secretos ni PII en el documento.  
- Checklist de legibilidad IA (Anexo A de S06) cumplido para esa sección.

## 7\. Anti-patrones específicos

- **Decisiones sin ADR**: si va al DTI, va con un ADR; si no tiene ADR, no entra.  
- **Drift silencioso**: actualizar el DTI sin tocar `AGENTS.md` cuando la decisión los afecta a ambos.  
- **Prosa ambigua en `[máquina]`**: usar YAML o tablas, no párrafos narrativos.  
- **Tablas decorativas**: usar tablas solo cuando aportan estructura semántica.  
- **Sobre-poblar §0–§21**: si una sección no aplica al producto, marcarla `N/A` con 1 línea de justificación; no inventar contenido.

## 8\. Mini ejemplo de invocación

"@dti-author Pobla §3 (Arquitectura de Alto Nivel) del DTI a partir del ADR-0001 que decide monolito modular con Spring Modulith. Después propón el diff de `AGENTS.md` que corresponda."

## 9\. Modos de fallo conocidos

- ADR fuente está en estado `proposed`, no `accepted` → STOP, pedir confirmación al humano antes de propagar al DTI.  
- El frontmatter de la plantilla tiene campos que el grupo aún no decidió (ej. `release_objetivo`) → completar con `<pendiente>` y crear `TODO(spec)` en el cuerpo.  
- Conflicto entre el FSD y un ADR → STOP, escalar al docente; no resolver por cuenta propia.

## 10\. Registro de cambios del Skill

| Versión | Fecha | Autor | Cambio |
| :---- | :---- | :---- | :---- |
| 0.1.0 | 13/05/2026 | docente | versión inicial liberada en S06 |

