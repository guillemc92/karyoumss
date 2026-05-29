---

name: poc-runner description: \> Toma una ficha `pocs/POC-NN/POC-NN.md` y bootstrapea un scaffold ejecutable (branch \+ scripts \+ README) reproducible por Claude Code. Ejecuta la POC, registra el log y, si falla, propone diffs a ADR-0001 / DTI §12 / `AGENTS.md`. Activar cuando el usuario invoca `"@poc-runner POC-NN"` sobre una ficha válida según `plantillas/POC_TEMPLATE.md`. allowed-tools:

- read  
- edit  
- run-tests model-tier: sonnet fsd-version-min: v0.1 status: stable owner: docente / grupo

---

# Skill: poc-runner (bootstrapea y ejecuta POCs reproducibles)

**Convención del módulo**: este skill vive en `docs/skills/poc-runner.md`. Para activarlo en Claude Code, copiar a `.claude/skills/poc-runner/SKILL.md` en el repo del grupo o a `~/.claude/skills/poc-runner/` para alcance global del usuario. En Cursor existe un mecanismo paralelo (`.cursor/rules/*.mdc`); este skill no se activa automáticamente allí, pero la cursor rule de POCs valida la ficha al guardar.

## 1\. Cuándo activarlo (triggers)

- DURANTE: ejecución de una POC time-boxed, desde su ficha hasta el log de resultado.  
- ARRANCA cuando: el usuario invoca `"@poc-runner POC-NN"` o `"@poc-runner bootstrapea POC-NN"`.  
- NO ACTIVAR cuando: la ficha de la POC aún no tiene criterio SMART verificable ni *time-box*; pedir refinar la ficha antes.

## 2\. Entradas obligatorias (Inputs)

El usuario MUST proporcionar al menos una de:

- Ficha de la POC: `pocs/POC-NN/POC-NN.md` (creada con `plantillas/POC_TEMPLATE.md`).  
- Identificador `POC-NN` cuando el repo está accesible y la ficha existe.

La ficha de la POC MUST contener:

- Hipótesis (1 línea).  
- Alcance (qué entra y qué no).  
- **Criterio SMART verificable por script** (umbral numérico, comando o aserción).  
- ***Time-box*** explícito (máximo en horas-persona).  
- Señales de abandono (cuándo parar antes del *time-box*).  
- Decisión que se desbloquea si la POC pasa o falla.

Si falta cualquiera, responder: `"La ficha POC-NN está incompleta; me falta <campo>. No bootstrapeo hasta que esté completa."`

## 3\. Fuentes de verdad (orden de precedencia)

1. Ficha `pocs/POC-NN/POC-NN.md` (autoritativa para alcance y criterio).  
2. NFRs del FSD §10 (umbrales numéricos que la POC debe validar).  
3. `AGENTS.md` (stack, comandos, restricciones de ejecución).  
4. ADRs vigentes en `docs/adr/` (decisiones que la POC valida o cuestiona).  
5. Convenciones del repositorio (estructura de branches, scripts, CI).

## 4\. Procedimiento

1. **Validar ficha**: verificar que todos los campos obligatorios existen y que el criterio SMART es verificable por script (no prosa).  
2. **Crear branch**: `poc/POC-NN-<slug>` desde `release/1.0.1` o desde la rama del grupo según convención.  
3. **Generar scaffold mínimo viable**: estructura de carpetas, dependencias, scripts de ejecución y verificación, `README.md` con comandos copiables.  
4. **Ejecutar la POC**: correr los scripts; capturar logs de salida.  
5. **Verificar contra criterio SMART**: el script de verificación retorna `pass` o `fail` con métrica concreta.  
6. **Registrar resultado**: append a `pocs/POC-NN/log.md` con timestamp, comando, métrica obtenida y veredicto.  
7. **Si `fail` o si la decisión que se desbloquea cambia**: proponer diffs a:  
   - `docs/adr/0001-estilo-arquitectonico.md` (si la decisión arquitectónica se invalida).  
   - `docs/DTI.md` §12 (resultado de la POC).  
   - `AGENTS.md` (si el stack o restricciones cambian para los agentes).  
8. **Cerrar la POC**: marcar la ficha como `concluida: pass` o `concluida: fail` con fecha y link al log.

## 5\. Salida esperada

- Branch `poc/POC-NN-<slug>` con el scaffold ejecutable commiteado.  
- `pocs/POC-NN/README.md` con comandos reproducibles por Claude Code (`claude --read pocs/POC-NN/POC-NN.md ...`).  
- `pocs/POC-NN/log.md` con el resultado registrado.  
- Si `fail`: 3 diffs propuestos (ADR / DTI §12 / `AGENTS.md`) en un único commit candidato.  
- Tabla de resultado al final:

| Campo | Valor |
| :---- | :---- |
| POC | POC-NN — `<titulo>` |
| Hipótesis | `<1 línea>` |
| Criterio SMART | `<umbral / comando>` |
| Métrica observada | `<valor numérico>` |
| *Time-box* (gastado) | `<horas-persona reales / máximo>` |
| Veredicto | `pass` / `fail` / `abandono` |
| Decisión desbloqueada | `<texto>` |

## 6\. Verificación (criterios de "bien hecho")

- Branch `poc/POC-NN-<slug>` existe y solo tiene commits relativos a la POC.  
- README de la POC tiene comandos copiables sin variables `<x>` sin definir.  
- Claude Code puede re-ejecutar el scaffold de cero (sin estado oculto en la máquina del autor).  
- El criterio SMART se verifica por **script** (no por inspección visual).  
- Log con timestamp, comando, métrica y veredicto está commiteado.  
- Si la POC falla, los 3 diffs (ADR / DTI / AGENTS) están propuestos en el mismo commit candidato.

## 7\. Anti-patrones específicos

- **POC infinita**: ignorar el *time-box*. El skill debe parar al alcanzarlo y registrar `abandono` con justificación.  
- **POC sin criterio de abandono**: el skill rechaza ejecutar la POC si la ficha no lo tiene.  
- **POC que se vuelve producto**: el código de la POC viaja a `release/*`. El skill enfatiza "la rama `poc/*` muere; los aprendizajes viajan al ADR, no el código".  
- **Criterio difuso**: "que sea rápido". El skill rechaza si no hay umbral numérico verificable.  
- **POC no reproducible**: scripts que solo corren en la máquina del autor.  
- **Una POC sobre lo conocido, ninguna sobre la capa IA**: si el grupo tiene 2 POCs sin tocar IA, el skill sugiere reorientar al menos una hacia RAG / agentes / guardrails.

## 8\. Mini ejemplo de invocación

"@poc-runner POC-01. Hipótesis: `pgvector` resuelve búsqueda semántica con p95 \< 200 ms para 10k embeddings. *Time-box*: 4 horas-persona. Criterio SMART: `pytest tests/poc01_latency.py` retorna 0 y reporta p95 \< 200 ms."

## 9\. Modos de fallo conocidos

- La ficha cita un NFR-NNN inexistente → STOP, pedir aclaración.  
- El criterio SMART no es ejecutable (es prosa) → STOP, pedir reformular la ficha.  
- La POC corre pero el log no se puede capturar (timeout, OOM) → registrar `abandono` con causa y proponer rediseño de la POC.  
- Conflicto entre el resultado de la POC y un ADR `accepted` → STOP, escalar al docente; el skill no actualiza ADRs `accepted` sin curación humana.

## 10\. Registro de cambios del Skill

| Versión | Fecha | Autor | Cambio |
| :---- | :---- | :---- | :---- |
| 0.1.0 | 13/05/2026 | docente | versión inicial liberada en S06 |

