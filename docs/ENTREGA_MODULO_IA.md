# Entrega — Módulo de IA: primera llamada a un modelo de lenguaje

Guía para armar el PDF/Word de la entrega. Todo lo que pide la consigna ya está
implementado; esto indica **qué mostrar y cómo capturarlo**.

---

## 1. Datos para la portada

| Campo | Valor |
|---|---|
| Proyecto | BIOMED UMSS — Plataforma de Cariotipado Inteligente |
| Grupo | G04 (individual) |
| Integrante | Ing. Guillermo Mamani Chambi |
| **Modelo** | `llama3.2:3b` |
| **Proveedor** | **Ollama** (local, `http://localhost:11434/v1`) |
| SDK | `openai>=1.0` (Ollama expone API compatible) |
| Lenguaje | Python 3.12 / Django 5 (el stack que ya usa el proyecto) |
| Repositorio | *(pegar el enlace de GitHub)* |

---

## 2. La consigna, punto por punto

| Requisito | Dónde está |
|---|---|
| Una función que manda un prompt y recibe la respuesta | `backend-clinic/apps/samples/llm_client.py` → `LlmClient.generate_narrative()` |
| Una ejecución exitosa que muestre la respuesta | `python manage.py demo_llm` (ver §3) |
| **Extra:** el prompt viene de un dato real de la app | El prompt se arma con el código CHN, el tipo de muestra y el conteo de cromosomas **de un caso de la base**, no de un texto de ejemplo |
| **Extra:** exponerlo como endpoint | `POST /api/clinic/samples/{id}/narrative/` |

**Los dos extras están cubiertos**, no solo el mínimo.

---

## 3. La captura que pide la consigna

Necesita verse **a la vez el código de la llamada y la salida real**. La forma más
limpia: VS Code con `llm_client.py` abierto y la terminal integrada abajo.

```bash
cd backend-clinic
.venv/Scripts/python manage.py demo_llm --chn CHN-DEMO-T21
```

Salida real (i5-3317U sin GPU). Este caso es un **síndrome de Down**: el motor
determinístico derivó `47,XY,+21` del cariotipo validado, y el LLM redactó sobre
ese dato.

```
========================================================================
DEMO - Integracion con LLM (ADR-0024)  |  BIOMED UMSS
========================================================================

[1] Proveedor y modelo
    proveedor : Ollama (local, API compatible con el SDK de OpenAI)
    endpoint  : http://localhost:11434/v1
    modelo    : llama3.2:3b
    habilitado: True

[2] Dato real de la aplicacion
    caso (CHN)  : CHN-DEMO-T21
    tipo muestra: sangre
    cromosomas  : 47 activos
    ISCN        : 47,XY,+21
    origen ISCN : campo persistido del caso (S3)
    (lo calcula una funcion pura deterministica, NO el LLM - ADR-0024 D1)

[3] Llamando al modelo...

[4] Respuesta del modelo
------------------------------------------------------------------------
  El cariotipo de la muestra presentado como 47,XY,+21 indica una
  aneuploidia del cromosoma 21, con un numero adicional de este
  cromosoma en comparacion con el esperado normal (46,XY). Este hallazgo
  sugiere trisomia 21, caracterizada por la presencia de una copia
  adicional del cromosoma 21. El resultado requiere correlacion clinica
  para determinar su significado en el contexto de los sintomas y
  antecedentes del paciente.
------------------------------------------------------------------------
    latencia total: 129102 ms

[5] Persistencia y auditoria
    Sample.narrative_draft : 422 chars
    Sample.narrative_model : llama3.2:3b
    AuditEvent             : NARRATIVE_GENERATED
    hash encadenado        : 7a09a22dfd939c269c87d21f2f4e12b6...
```

**Por qué esta captura es fuerte:** se ve el dato real (47 cromosomas contados en
la base), el ISCN que produjo la función determinística, y el LLM redactando sobre
ese dato — no sobre un prompt inventado. La línea `origen ISCN` prueba que el dato
clínico no lo generó el modelo.

### Preparar el caso de la demo

Un solo comando deja el caso listo (47 cromosomas, tres copias del 21, ISCN ya
generado por el motor de S3):

```bash
.venv/Scripts/python manage.py seed_demo_iscn
# Caso CHN-DEMO-T21: ISCN=47,XY,+21 estado=REPORTED (47 cromosomas)

.venv/Scripts/python manage.py demo_llm --chn CHN-DEMO-T21
```

Otras variantes:

```bash
.venv/Scripts/python manage.py seed_demo_iscn --trisomia 18   # Edwards
.venv/Scripts/python manage.py seed_demo_iscn --sexo XX       # femenino
.venv/Scripts/python manage.py demo_llm                       # último caso de la base
```

> La llamada tarda **1-3 minutos** en CPU sin GPU. Es normal — no está colgado.

### Captura del endpoint (extra)

```bash
# terminal 1
.venv/Scripts/python manage.py runserver 8010

# terminal 2
curl -X POST http://localhost:8010/api/clinic/samples/<UUID>/narrative/ \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d "{\"iscn\": \"47,XY,+21\"}"
```

---

## 4. Seguridad — lo que la consigna penaliza

> *«Una clave visible en una imagen es una clave comprometida.»*

**Este proyecto no tiene ese riesgo, y conviene decirlo explícitamente en la
entrega:**

- **Ollama corre en localhost y no usa API key.** No hay credencial que filtrar.
- La configuración vive en `.env`, ignorado por git (`backend-clinic/.gitignore`
  línea 4). En el repositorio solo está `.env.example`, con valores de ejemplo.
- Verificado: `git ls-files | grep .env` devuelve **solo** archivos `.env.example`.
- No hay claves en el código: `git grep -E "sk-[a-zA-Z0-9]{20}"` no da resultados.
- `demo_llm` no imprime ninguna credencial, por diseño.

**Antes de capturar:** revisá que no haya un `.env` abierto en el editor ni
variables de entorno visibles en la terminal.

---

## 5. Qué contar sobre el diseño (esto suma)

**El proyecto ya usaba IA antes de este ejercicio**, pero de otro tipo:

| | IA discriminativa | IA generativa (este ejercicio) |
|---|---|---|
| Modelo | EfficientNet-B3 entrenada por mí | `llama3.2:3b` vía SDK |
| Pregunta | ¿qué cromosoma es este? | ¿cómo se redacta este resultado? |
| Ejecución | `forward()` de PyTorch, local | request HTTP a un endpoint |

Son complementarias: la CNN no redacta, el LLM no clasifica.

**La decisión de diseño central (ADR-0024 D1): el LLM redacta, nunca calcula el
dato clínico.** `47,XY,+21` es un diagnóstico de síndrome de Down; lo produce
`generate_iscn()`, una **función pura** (`apps/samples/iscn.py`): sin ORM, sin I/O,
sin estado — mismo conteo, mismo resultado, siempre. El LLM recibe ese ISCN ya
calculado y solo escribe el párrafo interpretativo.

Esa separación es lo que hace **auditable** el diagnóstico. Un modelo generativo
puede alucinar una trisomía; una función determinística no, y se prueba con tests
contra síndromes reales (Down, Edwards, Patau, Turner, Klinefelter).

**Por qué local y no la nube:** la regla RN-03 del proyecto prohíbe que salgan
datos de paciente. Con Ollama en localhost eso se cumple **por construcción** — no
hay egreso que anonimizar. Costo cero, además.

### Un hallazgo honesto que vale la pena mostrar

En una prueba real, el modelo describió la trisomía 21 como *«una deficiencia
crónica y progresiva de la función cerebral»* — **clínicamente falso**. La
validación automática **no lo detectó**, porque solo verifica que las anomalías
citadas existan en el ISCN (`+21` sí estaba); lo que falla es la corrección médica
de la prosa.

No invalida el diseño, lo confirma: por eso el texto va a un campo llamado
`narrative_draft` y requiere revisión del Supervisor antes del informe firmado.
Mostrar una alucinación encontrada en la propia demo, y la capa que la contiene, es
mejor defensa que una demo donde todo salió perfecto.

---

## 6. Archivos a referenciar en el PDF

| Archivo | Qué es |
|---|---|
| `backend-clinic/apps/samples/llm_client.py` | **La llamada al modelo** (SDK, prompt, validación) |
| `backend-clinic/apps/samples/iscn.py` | El motor determinístico que produce el dato clínico |
| `backend-clinic/apps/samples/services.py` → `generate_narrative()` | Persistencia + auditoría + degradación |
| `backend-clinic/apps/samples/views.py` → `CaseNarrativeView` | El endpoint |
| `backend-clinic/apps/samples/management/commands/demo_llm.py` | El script de la demo |
| `docs/adr/0024-llm-local-narrativa-informe.md` | La decisión arquitectónica |
| `backend-clinic/.env.example` | Configuración sin secretos |

**Tests:** 34 (17 del cliente + 17 del servicio y el endpoint). Corren sin
necesidad de Ollama:

```bash
.venv/Scripts/python -m pytest apps/samples/tests/test_llm_client.py \
    apps/samples/tests/test_narrative_service.py -v --no-cov
```
