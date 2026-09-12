# LLM local (Ollama) — puesta en marcha y defensa

Guía operativa de la integración descrita en **ADR-0024**. Cubre cómo levantarla,
cómo demostrarla y cómo explicarla.

---

## 1. Por qué esta integración existe

El proyecto ya usaba IA antes de esto: **EfficientNet-B3** entrenada sobre el
dataset MetaClass clasifica cromosomas en 24 clases (ADR-0007). Eso es IA
**discriminativa** — recibe una imagen, devuelve una etiqueta.

El módulo de la maestría evalúa algo distinto: la integración de un **SDK de IA
generativa**, es decir la arquitectura cliente-servidor contra un LLM (SDK,
endpoint, request, response, tokens, latencia). Una CNN no ejercita esos
conceptos: no hay SDK ni endpoint, la inferencia es un `forward()` local.

Son capacidades complementarias, no sustitutas:

| | IA discriminativa | IA generativa |
|---|---|---|
| Modelo | EfficientNet-B3 (propio, entrenado) | LLM (de terceros, vía SDK) |
| Pregunta | ¿qué cromosoma es este? | ¿cómo se redacta este resultado? |
| Entrada / salida | imagen → etiqueta | texto → texto |
| Ejecución | `forward()` de PyTorch | request HTTP a un endpoint |

**Ninguna puede hacer el trabajo de la otra.** La CNN no redacta; el LLM no
clasifica cromosomas.

---

## 2. La decisión de diseño que importa

> **El LLM redacta. NUNCA calcula el dato clínico.**

`47,XY,+21` es un diagnóstico de síndrome de Down. Ese string lo produce
`generate_iscn()`, una **función pura determinística** (ADR-0023 D4): mismo
input, mismo output, testeable. Un LLM podría alucinar una trisomía inexistente.

El LLM recibe el ISCN **ya calculado** y solo escribe el párrafo que lo acompaña:

```
CNN clasifica → Analista valida naranjas (RN-01) → generate_iscn() calcula el
ISCN → LLM redacta la narrativa → Supervisor revisa antes de firmar
```

Nótese que esto **no deroga** ADR-0023: la nomenclatura sigue siendo
determinística. Se agrega una capa encima, no se reemplaza nada.

---

## 3. Por qué local y no la nube

Dos razones que apuntan al mismo lado:

1. **RN-03 (cero fuga de PII).** Con Ollama en `localhost`, ningún dato clínico
   sale de la máquina. La regla se cumple **por construcción**: no hay egreso que
   anonimizar porque no hay egreso. Con un proveedor SaaS habría que anonimizar
   antes de cada llamada y aceptar el riesgo residual.
2. **Costo cero.** Sin tokens facturados.

Ollama expone una **API compatible con el SDK de OpenAI**, así que el código usa
el SDK estándar de la industria — se demuestran exactamente los mismos conceptos
que con un proveedor de pago, cambiando solo `base_url`.

Refuerzo adicional (ADR-0024 D6): aunque el modelo es local, el prompt **nunca**
lleva PII. Solo van código CHN (seudónimo), ISCN, tipo de muestra y conteo. El
nombre y el documento viven cifrados en `PatientVault` (ADR-0016 D2). Si algún día
se cambiara a un proveedor remoto, el prompt ya sería seguro.

---

## 4. Puesta en marcha

### 4.1 Descargar el modelo

```bash
ollama serve                 # si no está corriendo ya
ollama pull llama3.2:3b      # ~2 GB
ollama list                  # verificar
```

**Elección del modelo según hardware.** En un i5-3317U sin GPU, la inferencia va a
~2-5 tokens/s: unos 30 s por narrativa. Aceptable para demo, no para producción.

| Hardware | Modelo sugerido |
|---|---|
| i5-3317U / 16 GB / sin GPU | `llama3.2:3b`, o `llama3.2:1b` si va muy lento |
| Mac M4 Pro / 48 GB unificada | `qwen2.5:32b` o similar |

> No uses **DeepSeek Coder** para esta tarea: está especializado en código y
> rechaza el chat conversacional. Es el error que apareció en clase.

Cambiar de modelo es una variable de entorno (`CLINIC_LLM_MODEL`), no un cambio
de arquitectura.

### 4.2 Instalar el SDK

```bash
cd backend-clinic
.venv/Scripts/python -m pip install "openai>=1.0"
```

### 4.3 Activar

Está **apagado por defecto** a propósito (RN-07: sin narrativa el informe se emite
igual). Para encenderlo, en el `.env` de `backend-clinic`:

```env
CLINIC_LLM_ENABLED=true
CLINIC_LLM_MODEL=llama3.2:3b
CLINIC_LLM_URL=http://localhost:11434/v1
CLINIC_LLM_TIMEOUT=60.0
```

### 4.4 Probar

```bash
.venv/Scripts/python -m pytest apps/samples/tests/test_llm_client.py -v --no-cov
```

17 tests, sin necesidad de Ollama corriendo (el SDK se sustituye por dobles).

---

## 5. Defensa contra alucinación

Un LLM puede inventar. En un sistema clínico eso es inaceptable, así que hay tres
capas de defensa (ADR-0024 D4):

1. **Validación de consistencia.** Toda anomalía mencionada en el texto (`+21`,
   `del(`, `t(`) debe existir en el ISCN de entrada. Si el texto afirma `+21` pero
   el ISCN dice `46,XX`, el borrador se descarta.
2. **Cota de longitud.** Respuestas absurdamente cortas o largas se rechazan.
3. **Revisión humana obligatoria.** El texto va a `narrative_draft`, un campo
   explícitamente de borrador. No entra al informe firmado sin que el Supervisor
   lo revise.

Un detalle de diseño: **una alucinación no abre el circuit breaker.** Si el modelo
respondió, el servicio está sano — el problema es de contenido, no de
disponibilidad. Abrir el circuito ahí dejaría al LLM fuera de servicio por un error
de redacción.

Y si todo falla, la narrativa queda vacía y el flujo continúa. **Nunca bloquea la
emisión del informe** (RN-07).

---

## 6. Qué mostrar en la presentación

1. **El pipeline completo**, no solo el LLM: la CNN entrenada, el dataset
   construido extrayendo etiquetas por posición de los cariogramas, y el
   diagnóstico de los dos defectos del entrenamiento v1 (fuga de datos entre
   train/val y preprocesamiento que borraba la señal de tamaño). Eso está por
   encima de lo que pide la rúbrica.
2. **La arquitectura cliente-servidor** contra el LLM: `llm_client.py`, el SDK, el
   request, el response, `usage.total_tokens`, la latencia medida.
3. **La separación determinístico/generativo** y por qué el dato clínico nunca lo
   produce el LLM. Este es el punto fuerte de ingeniería.
4. **La coincidencia entre el requisito académico y la restricción clínica**: el
   docente pide local por costo; RN-03 lo exige por seguridad. La misma decisión
   satisface ambos.

---

## 7. Archivos

| Archivo | Rol |
|---|---|
| `docs/adr/0024-llm-local-narrativa-informe.md` | Decisión arquitectónica |
| `backend-clinic/apps/samples/llm_client.py` | Cliente SDK + validación + circuit breaker |
| `backend-clinic/apps/samples/services.py` → `generate_narrative()` | Persistencia + auditoría + degradación |
| `backend-clinic/apps/samples/models.py` | Campos `narrative_*` + evento `NARRATIVE_GENERATED` |
| `backend-clinic/apps/samples/migrations/0013_*` | Migración |
| `backend-clinic/apps/samples/tests/test_llm_client.py` | 17 tests del cliente |
| `backend-clinic/apps/samples/tests/test_narrative_service.py` | 11 tests del servicio |
| `backend-clinic/clinic_backend/settings.py` | Configuración (`CLINIC_LLM_*`) |

---

## 8. Estado: qué está y qué falta

**Implementado y verificado contra Ollama real:**

- Cliente SDK con validación anti-alucinación y circuit breaker.
- `generate_narrative(sample, actor, iscn)`: llama al LLM, persiste el borrador
  en `Sample.narrative_draft`, emite `NARRATIVE_GENERATED` encadenado en el hash
  chain, y **degrada sin lanzar** si el LLM falla.
- 28 tests (17 cliente + 11 servicio), sin necesidad de Ollama corriendo.

Prueba end-to-end real (i5-3317U): `46,XX` → narrativa persistida, 460 tokens,
**99.8 s**, evento de auditoría con `iscn_input`, `model`, `tokens` y hash.

**Falta:**

- **`generate_iscn()` — la fase S3 del ADR-0023 no está implementada.** Hoy el
  ISCN se pasa como parámetro. Sin S3 no hay informe final completo: el LLM
  redacta, pero el dato clínico que narra todavía no lo produce nadie.
- Endpoint REST para que el Supervisor dispare la generación (hoy el servicio se
  invoca desde código).
- UI de revisión del borrador en `frontend-clinic`.

> El orden correcto es **S3 primero, endpoint después**. Invertirlo tentaría a
> pedirle el ISCN al LLM, que es exactamente lo que ADR-0024 D1 prohíbe.
