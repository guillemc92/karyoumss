---
id: ADR-0024
title: LLM local (Ollama) para la narrativa del informe — IA generativa vía SDK
date: 2026-07-27
status: accepted
refines: [ADR-0003, ADR-0007, ADR-0023]
---

# ADR-0024: LLM local para la narrativa del informe clínico

## Contexto

El sistema ya incorpora **IA discriminativa**: EfficientNet-B3 entrenada sobre el
dataset MetaClass (ADR-0007, Fase C) clasifica cada cromosoma en 24 clases, con
segmentación OpenCV/watershed previa. Esa IA responde *«qué cromosoma es este»*.

Existe una necesidad distinta que ese modelo **no puede cubrir por construcción**:
redactar en lenguaje natural la interpretación que acompaña al informe. Una CNN de
clasificación emite una etiqueta y una confianza; no genera texto.

**Requisito académico (módulo de IA, maestría UMSS):** la asignatura evalúa la
integración de un **SDK de IA generativa** — arquitectura cliente-servidor contra
un LLM: SDK, endpoint, request/response, tokens, latencia. La CNN entrenada, pese
a ser IA en sentido estricto, no ejercita esos conceptos: no hay SDK ni endpoint,
los pesos son locales y la inferencia es un `forward()` de PyTorch.

**Restricción dominante (RN-03, ADR-0003):** cero fuga de PII. Todo dato que
salga del sistema debe pasar por el CHN Anonymizer. Un LLM SaaS (Anthropic,
OpenAI, Gemini) implicaría transmisión externa de contenido clínico.

**Restricción de hardware (2026-07):** la máquina de desarrollo es un Intel
i5-3317U (2 núcleos, 1.7 GHz), 16 GB RAM, GPU integrada HD 4000 sin capacidad de
inferencia. Solo son viables modelos ≤3B cuantizados, en CPU.

**Restricción de arquitectura ya decidida (ADR-0023 D4):** la nomenclatura ISCN
la produce una **función pura determinística** `generate_iscn(chromosomes)`. Esa
decisión está firmada y **este ADR no la deroga**.

## Decisión

### D1 — El LLM redacta; NUNCA calcula el dato clínico

Separación estricta e innegociable:

| Responsabilidad | Componente | Naturaleza |
|---|---|---|
| Clasificar cromosomas | EfficientNet-B3 (ADR-0007) | IA discriminativa, local |
| Validar naranjas | Analista humano (RN-01) | HITL |
| Generar ISCN | `generate_iscn()` (ADR-0023 D4) | **Función pura determinística** |
| Redactar narrativa | LLM local (este ADR) | IA generativa vía SDK |

El LLM recibe el ISCN **ya calculado** y el conteo **ya validado**, y produce
únicamente prosa explicativa. No cuenta cromosomas, no infiere el cariotipo, no
decide el diagnóstico.

*Razón:* `47,XY,+21` es un diagnóstico de síndrome de Down. Un LLM puede alucinar
una anomalía inexistente; una función pura no. Delegar el dato clínico a un modelo
generativo sería un riesgo para el paciente inaceptable, e invalidaría la
testabilidad exigida por RN-09.

### D2 — Ollama en localhost como proveedor (no SaaS)

El LLM corre vía **Ollama** en `http://localhost:11434`. Ningún dato clínico
abandona la máquina, de modo que **RN-03 se satisface estructuralmente**, no por
convención: no hay egreso que anonimizar porque no hay egreso.

Ollama expone una API **compatible con el SDK de OpenAI**, por lo que la
integración usa el SDK estándar (`openai>=1.0`) apuntando a `base_url` local. Se
ejercitan los mismos conceptos que un proveedor de pago (SDK, request, response,
`usage.total_tokens`, latencia) con costo cero.

*Alternativa considerada y rechazada:* SDK de Anthropic/OpenAI en la nube.
Rechazada por RN-03 — obligaría a anonimizar antes de cada llamada y a asumir el
riesgo residual de fuga. El modo local elimina la clase de riesgo entera.

**Modelo por defecto:** `llama3.2:3b` (~2 GB, cuantizado), dimensionado para el
hardware actual. El modelo es configurable por variable de entorno
(`CLINIC_LLM_MODEL`): al migrar a hardware con más memoria unificada, subir de
modelo es un cambio de configuración, no de arquitectura.

### D3 — La narrativa es SUGERENCIA, nunca dato firmado

El texto generado se persiste en `Sample.narrative_draft` — **campo separado**,
explícitamente un borrador. No se mezcla con `iscn_nomenclature` (read-only por
RN-04) ni entra en el reporte firmado sin revisión humana.

- El Supervisor **debe** revisar el borrador antes de que llegue al informe.
- La generación emite el evento de auditoría `NARRATIVE_GENERATED` (ADR-0022),
  registrando modelo, versión y si el texto fue editado después.
- El borrador se genera **solo** en estado `REPORTED` (ISCN ya existente): sin
  ISCN determinístico no hay nada que narrar.

### D4 — Validación de la salida (defensa contra alucinación)

Toda respuesta del LLM se valida antes de persistirse:

1. **Consistencia con el ISCN:** el texto no puede mencionar cromosomas o
   anomalías ausentes en el ISCN de entrada. Se verifica que todo patrón de
   anomalía (`+N`, `-N`, `del`, `dup`, `t(`) presente en la narrativa exista en el
   ISCN. Discrepancia → se descarta el borrador.
2. **Cota de longitud:** respuesta fuera de rango razonable → descarte.
3. **Fallo del servicio → degradación limpia:** si Ollama no responde o la
   validación falla, `narrative_draft` queda vacío y el flujo continúa. **La
   narrativa nunca bloquea la emisión del informe** (RN-07, degradación elegante).

### D5 — Cliente con circuit breaker (patrón establecido)

`llm_client.py` replica el patrón de `pipeline_client` (ADR-0015 #6) y
`admin_client` (ADR-0023 D3): timeout, umbral de fallos, cooldown. Ollama en CPU
es lento (~2-5 tok/s en el hardware actual), por lo que el timeout por defecto es
holgado (`CLINIC_LLM_TIMEOUT = 60s`) y la llamada **no** es parte del camino
crítico de firma.

### D6 — Sin PII en el prompt (refuerzo de RN-03)

Aunque el modelo es local, el prompt se construye **solo** con: código CHN
(seudónimo), string ISCN, conteo por clase, y tipo de muestra. Nombre, documento y
fecha de nacimiento del paciente viven cifrados en `PatientVault` (ADR-0016 D2) y
**no** se incluyen. Así, si el proveedor se sustituyera por uno remoto en el
futuro, el prompt ya sería seguro por diseño.

## Trade-offs

- **Pros:** satisface el requisito académico con un caso de uso real, no
  decorativo; costo cero; RN-03 satisfecha por construcción; el dato clínico sigue
  siendo determinístico y testeable; portable a otro proveedor cambiando `base_url`.
- **Cons:** el modelo local de 3B produce prosa de calidad inferior a un modelo
  frontera; la inferencia en CPU es lenta (medido en el hardware actual: 100-107 s
  por narrativa, y un caso superó los 190 s), aceptable solo por ser asíncrona
  respecto de la firma; la validación anti-alucinación es heurística, no una
  garantía formal — por eso la revisión humana de D3 es obligatoria.

  **Límite conocido de la validación (medido, no hipotético):** en la prueba real
  con `llama3.2:3b` sobre `47,XY,+21`, el modelo describió la trisomía 21 como
  *«una deficiencia crónica y progresiva de la función cerebral»* — clínicamente
  falso. La validación de D4.1 **no lo detectó**, porque la anomalía citada (`+21`)
  sí estaba en el ISCN: lo que falla es la corrección médica de la prosa, no la
  consistencia citogenética. Esto confirma que D3 (revisión humana obligatoria) no
  es una formalidad sino la capa que efectivamente contiene este error.

## Consecuencias

- Migración en `apps/samples`: campo `narrative_draft` y evento de auditoría
  `NARRATIVE_GENERATED`.
- Nueva dependencia `openai>=1.0` (SDK), apuntando a Ollama local.
- Nuevas settings: `CLINIC_LLM_URL`, `CLINIC_LLM_MODEL`, `CLINIC_LLM_TIMEOUT`,
  `CLINIC_LLM_ENABLED`.
- Requisito operativo: Ollama corriendo con el modelo descargado. Si no está, el
  sistema funciona igual sin narrativa (D4.3).
- **No deroga ADR-0023 D4**: `generate_iscn()` sigue siendo la única fuente de la
  nomenclatura.
