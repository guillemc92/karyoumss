# Prompt derivado de Especificación – Plantilla

**Propósito**: normalizar la forma en que los grupos convierten un artefacto de especificación (BRD, MRD, PRD, FSD, DTI, ADR) en un **prompt ejecutable** que un agente de IA pueda consumir de forma determinística y auditable.

Todo prompt del repositorio vive en `docs/prompts/<area>/<id>.md` y es referenciado desde `docs/PROMPT_MAPPING.md`.

---

## 0\. Metadatos del prompt

| Campo | Valor |
| :---- | :---- |
| ID del prompt | `PR-<area>-NNN` (p. ej. `PR-UC-001`) |
| Título | `<…>` |
| Artefacto origen | BRD / MRD / PRD / FSD / DTI / ADR |
| ID origen | `<BR-001 / MRD-N-01 / PRD-REQ-05 / FSD-UC-001 / ADR-0001>` |
| Tipo de prompt | generación / transformación / revisión / auditoría / clasificación / extracción |
| Modelo recomendado | Haiku / Sonnet / Opus |
| Temperatura | `<0.0 – 1.0>` |
| Versión | `v0.1` |
| Fecha | `<dd/mm/aaaa>` |
| Autor(es) | `<…>` |
| Estado | Borrador / Aprobado / Obsoleto |

## 1\. Anatomía del prompt (contenido principal)

**Regla**: los 6 elementos son obligatorios. Si alguno falta, el prompt no puede marcarse como `Aprobado`.

### 1.1 Role

Eres \<rol específico con nivel de senioridad y dominio\>.

### 1.2 Task

\<Acción verificable y atómica. Un solo objetivo por prompt.\>

### 1.3 Context

\- Documento fuente: \<enlace al artefacto\>

\- Entradas esperadas: \<estructura y tipos\>

\- Restricciones de dominio: \<BR-…, reglas, cumplimiento\>

\- Restricciones técnicas: \<stack, versiones\>

\- Ejemplos relevantes (few-shot): \<opcional\>

### 1.4 Reasoning (chain‑of‑thought estructurado)

Sigue estos pasos en orden:

1\. \<Paso 1\>

2\. \<Paso 2\>

3\. \<Paso 3\>

No expongas el razonamiento interno en el output final, salvo que se pida.

### 1.5 Stop condition

Detente cuando:

\- \<condición objetiva 1\>, o

\- \<condición objetiva 2\>.

No continues produciendo contenido más allá de estas condiciones.

### 1.6 Output

Formato: \<JSON Schema / Markdown estructurado / bloque de código\>

Ejemplo:

{

  "...": "..."

}

## 2\. Invariantes del prompt

Lista de propiedades que **toda salida válida** debe cumplir (verificables):

- La salida **debe** respetar el esquema declarado en §1.6.  
- La salida **no debe** contener información personal identificable.  
- La salida **debe** citar los IDs de los artefactos origen (`<FSD-UC-001>`).  
- La salida **no debe** exceder `<N>` tokens.  
- `<otras reglas de dominio>`.

## 3\. *Failure modes* declarados

| Código | Descripción | Acción del consumidor |
| :---- | :---- | :---- |
| `E_MISSING_CONTEXT` | falta documento fuente | abortar con error |
| `E_AMBIGUOUS_INPUT` | entrada con varios significados posibles | pedir aclaración |
| `E_POLICY_VIOLATION` | el output quebraría una invariante | rechazar y reintentar |

## 4\. Guardrails

- **MUST**: validar que el output cumple el esquema antes de consumirlo.  
- **MUST**: registrar `promptId`, `versión`, `modelo`, `tokens`, `latencia` en telemetría.  
- **MUST NOT**: exponer secretos ni credenciales en el context.  
- **MUST NOT**: almacenar PII en logs del prompt.  
- **MUST**: revisar el output humano si la confianza reportada por el modelo es \< `<0.7>`.

## 5\. Trazabilidad

| Origen | ID origen | Este prompt | Consumidor(es) | Artefacto generado |
| :---- | :---- | :---- | :---- | :---- |
| FSD | FSD-UC-001 | PR-UC-001 | `dev-agent` | código en `src/…` |

## 6\. Pruebas del prompt (*prompt tests*)

Al menos **3 casos de prueba** por prompt crítico:

### 6.1 Caso feliz

- **Input**: `<…>`.  
- **Output esperado**: `<…>` (puede expresarse como *assertion* JSON Schema).

### 6.2 Caso borde

- **Input**: `<entrada en el límite>`.  
- **Output esperado**: `<…>`.

### 6.3 Caso adversarial

- **Input**: `<entrada que intenta violar una invariante>`.  
- **Comportamiento esperado**: rechazo con `E_POLICY_VIOLATION`.

## 7\. Instrumentación

- Herramienta de observabilidad: `<Langfuse / LangSmith / OpenTelemetry>`.  
- Métricas esperadas: `success_rate, schema_pass_rate, avg_tokens, p95_latency, hallucination_rate`.

## 8\. Versionado

| Versión | Fecha | Autor | Cambio | Modelo validado |
| :---- | :---- | :---- | :---- | :---- |
| v0.1 |  |  | creación | Sonnet |
| v0.2 |  |  | endurecimiento de invariantes | Sonnet |

## 9\. Revisión humana

| Revisor | Fecha | Veredicto | Notas |
| :---- | :---- | :---- | :---- |
|  |  | aprobado / devuelto |  |

---

## Plantilla express (copiar y pegar)

\# Role

\<rol\>

\# Task

\<tarea\>

\# Context

\- \<…\>

\# Reasoning

1\. \<…\>

\# Stop condition

Detente cuando \<…\>.

\# Output

\<formato \+ ejemplo\>

\# Invariants

\- \<…\>

\# Failure modes

\- E\_...

## Mapeo rápido: artefacto → tipo de prompt sugerido

| Artefacto origen | Tipo de prompt típico | Modelo sugerido |
| :---- | :---- | :---- |
| BRD | clasificación de stakeholders, generación de RACI | Sonnet |
| MRD | análisis competitivo, *positioning* | Sonnet / Opus |
| PRD | generación de *user stories*, INVEST review | Sonnet |
| FSD | generación de casos de uso, prompt‑contrato por UC | Sonnet |
| DTI | generación de diagramas C4, auditoría de antipatrones | Opus |
| ADR | propuesta de alternativas, análisis de trade‑offs | Opus |
| POC | generación de scripts de carga, análisis de métricas | Sonnet / Haiku |

## Checklist para dar de alta un prompt en el repositorio

- [ ] Metadatos completos.  
- [ ] 6 elementos anatómicos presentes y no vacíos.  
- [ ] Invariantes declaradas.  
- [ ] Failure modes declarados.  
- [ ] 3 pruebas mínimas.  
- [ ] Trazabilidad al artefacto origen.  
- [ ] Revisión humana registrada.

