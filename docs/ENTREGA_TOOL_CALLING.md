# Entrega — Tool calling en el sistema propio (Módulo 6, semana 3)

Contenido para el documento Word de la entrega. Todo lo que pide la consigna está
implementado y verificado contra Ollama real.

---

## 1. Portada

| Campo | Valor |
|---|---|
| Proyecto | BIOMED UMSS — Plataforma de Cariotipado Inteligente |
| Grupo | Individual |
| Integrante | Ing. Guillermo Mamani Chambi |
| **Repositorio** | `https://github.com/guillemc92/karyoumss` |
| **Rama** | `feature/clinic-django-stack` |
| **Modelo** | `llama3.2:3b` — **versión fija, nunca `latest`** |
| Proveedor | Ollama local (`http://localhost:11434/v1`) |
| **Feature flag** | `CLINIC_LLM_ENABLED` en `backend-clinic/.env` |

---

## 2. La regla que ordena el diseño

> **El modelo ELIGE la herramienta. El código PRODUCE la respuesta.**

El LLM nunca ve la base de datos, nunca redacta un dato y nunca inventa un
número. Recibe una pregunta y devuelve **el nombre de una herramienta**; a partir
de ahí corre Django ORM y nada más.

Es la misma separación que ya rige el ISCN en este proyecto (ADR-0024 D1: el LLM
redacta pero no calcula el diagnóstico), aplicada ahora a las consultas.

### Los dos caminos

```
pregunta ──> ¿coincide una palabra clave del catálogo?
             │
             ├── sí ──> KEYWORD: ejecuta la herramienta. NO llama al modelo.
             │
             └── no ──> LLM: el modelo elige entre las herramientas publicadas.
                        Si no encaja ninguna, dice que no sabe.
```

El camino `KEYWORD` no es una optimización: **es lo que hace que el sistema siga
respondiendo con la IA apagada**.

---

## 3. Herramientas publicadas

| Herramienta | Responde | Fuente (tabla) |
|---|---|---|
| `CROMOSOMAS_PARA_REVISION` | Cromosomas naranjas: confianza < 85% sin resolver (RN-02) | `clinic_chromosomes` |
| `CASOS_PENDIENTES_FIRMA` | Casos validados esperando la firma del Supervisor | `clinic_samples` |
| `CASOS_REPORTADOS` | Casos cerrados con nomenclatura ISCN emitida | `clinic_samples` |
| `CASOS_EN_PROCESO` | Muestras que el pipeline de IA todavía procesa | `clinic_samples` |

Cada respuesta declara `tool`, `source` y `camino`. **Sin procedencia, un usuario
no puede distinguir un dato consultado de uno inventado** — que es exactamente lo
que esta arquitectura busca hacer imposible.

---

## 4. Los cuatro escenarios (salida real)

```bash
cd backend-clinic
.venv/Scripts/python manage.py seed_demo_tools   # siembra cromosomas naranjas
.venv/Scripts/python manage.py demo_tools        # corre los cuatro
```

> En Windows, `chcp 65001` antes del comando para que los acentos se vean bien.

### Escenario 1 — Controlado

**Pregunta:** «¿Qué cromosomas están naranjas?»
La palabra `naranjas` está en el catálogo → resuelve **sin llamar al modelo**.

```
Camino      : KEYWORD
Herramienta : CROMOSOMAS_PARA_REVISION
Fuente      : clinic_chromosomes
Latencia    : 7 ms
4 resultado(s).
  - caso=CHN-DEMO-TOOLS | clase=X  | confianza=54.8% | estado=Pendiente de revisión
  - caso=CHN-DEMO-TOOLS | clase=9  | confianza=61.2% | estado=Pendiente de revisión
  - caso=CHN-DEMO-TOOLS | clase=13 | confianza=70.4% | estado=Pendiente de revisión
  - caso=CHN-DEMO-TOOLS | clase=21 | confianza=78.3% | estado=Pendiente de revisión
```

### Escenario 2 — Sinónimo

**Pregunta:** «¿Cuáles necesitan que el analista los mire de nuevo?»
Ninguna palabra del catálogo coincide → escala al modelo, que elige la misma
herramienta. **Mismos 4 cromosomas que el escenario 1.**

```
Camino      : LLM
Herramienta : CROMOSOMAS_PARA_REVISION
Fuente      : clinic_chromosomes
Motivo (LLM): Revisión manual para confirmar clasificación
Latencia    : 97515 ms
4 resultado(s).   ← idénticos al escenario 1
```

### Escenario 3 — Fuera de alcance

**Pregunta:** «¿Cuál es el presupuesto del laboratorio para 2027?»
Ninguna herramienta responde eso. **No es un error ni una respuesta inventada.**

```
Camino      : SIN_MATCH
Herramienta : -
No puedo responder eso. Ninguna herramienta del catálogo responde esa pregunta.
Lo que SÍ puedo responder:
  - CROMOSOMAS_PARA_REVISION  (clinic_chromosomes)
  - CASOS_PENDIENTES_FIRMA    (clinic_samples)
  - CASOS_REPORTADOS          (clinic_samples)
  - CASOS_EN_PROCESO          (clinic_samples)
```

### Escenario 4 — Modelo apagado

**Pregunta:** la misma del escenario 1, con `CLINIC_LLM_ENABLED=false`.

```
Camino      : KEYWORD
Herramienta : CROMOSOMAS_PARA_REVISION
Fuente      : clinic_chromosomes
Latencia    : 7 ms
4 resultado(s).   ← idénticos al escenario 1
```

### Escenario 4-bis — Lo que aporta la IA, medido

La pregunta del escenario 2, ahora sin modelo:

```
Camino      : SIN_MATCH
No puedo responder eso. La asistencia por IA está desactivada y la consulta
no usa el vocabulario del catálogo.
```

**Eso está bien y es el punto:** apagar la IA no rompe el sistema, solo le quita
la tolerancia a sinónimos. Esa diferencia es exactamente lo que el modelo aporta.

---

## 4-bis. Los cuatro escenarios no bastan: la medición

Cuatro escenarios demuestran que el mecanismo funciona, pero no dicen **con qué
frecuencia acierta**. Para saberlo se construyó un banco de 30 preguntas
etiquetadas —escritas como las diría un analista, no como las escribiría quien
ya conoce el catálogo— y se midió:

```bash
python manage.py eval_enrutado     # ~11 min: cada paráfrasis cuesta una llamada
```

El reparto importa más que el total. Fallar **dentro** de alcance manda al
usuario a «no sé»; fallar **fuera** le entrega datos reales que no responden su
pregunta, que es mucho peor.

| | Primera medición | Prompt endurecido | Descripciones equilibradas |
|---|---|---|---|
| **Fuera de alcance** | 2/6 — **33%** | 6/6 — 100% | 6/6 — **100%** |
| Dentro de alcance | 22/24 — 92% | 21/24 — 88% | 23/24 — **96%** |
| **Global** | 24/30 — 80% | 27/30 — 90% | 29/30 — **97%** |

**El hallazgo que justificó el cambio:** con la regla de abstención escrita como
una línea suelta, el modelo elegía una herramienta en 4 de cada 6 preguntas fuera
de alcance. Enrutaba por parecido temático:

```
«¿Cuántos pacientes atendimos el año pasado?»  -> CASOS_REPORTADOS
«¿Quién es el jefe del servicio de genética?»  -> CASOS_PENDIENTES_FIRMA
«¿Qué dice el manual sobre el bandeo G?»       -> CROMOSOMAS_PARA_REVISION
«¿Cuándo vence el reactivo de tripsina?»       -> CROMOSOMAS_PARA_REVISION
```

Es exactamente el fallo que el escenario 3 existe para descartar, y **el
escenario 3 no lo detectaba**: su pregunta —el presupuesto de 2027— resultó ser
una de las dos que sí acertaba. Un escenario que pasa por la elección afortunada
de la pregunta no prueba nada.

**La corrección** fue darle a la abstención lo que la regla suelta no daba:
categorías explícitas de lo que ninguna herramienta cubre (estadísticas,
personas, documentación, inventario, dinero, pacientes concretos), la aclaración
de que las herramientas solo listan el estado **actual** del flujo, y la
prioridad invertida —elegir mal es peor que abstenerse—.

**El peaje, medido y no escondido:** endurecer la abstención costó una pregunta
válida (92% → 88% dentro de alcance). Los dos errores no cuestan lo mismo, así
que el intercambio compensaba — pero era un intercambio real, y se resolvió en
la segunda iteración.

### Segunda iteración — el atractor era un problema de redacción

Tras el primer arreglo, los 3 fallos restantes caían **todos** en
`CROMOSOMAS_PARA_REVISION`. La causa no era que las otras herramientas
estuvieran mal definidas: era que esa descripción estaba **mucho mejor escrita
que las demás** —cuatro líneas con umbral, sinónimos y casos de uso, frente a
dos líneas escuetas del resto—. El modelo se iba a la que mejor entendía.

Además, las preguntas que fallaba usaban vocabulario ausente de toda
descripción: «máquina», «corriendo», «trabajando», «sistema».

La corrección fue **equilibrar las cuatro** y darle a cada una su frontera:

- Cada descripción declara su etapa del flujo («es el trabajo en curso, antes de
  que haya resultados que revisar»; «es la última etapa antes de reportar»).
- Se distingue el grano: `CROMOSOMAS_PARA_REVISION` baja al detalle de los
  cromosomas **dentro** de un caso; las otras tres hablan de **casos** completos.
- Se añadió delimitación negativa donde hacía falta: «NO sirve para saber en qué
  está trabajando el sistema».
- Se incorporó el vocabulario real de los usuarios, no el del catálogo.

Resultado: **96% dentro de alcance sin perder el 100% de abstención**. Las dos
dimensiones quedaron por encima del punto de partida a la vez.

**El único fallo que queda** es de etiqueta discutible: «¿qué está listo para la
última revisión?» admite honestamente dos lecturas —la firma del supervisor o el
último repaso del analista—. Se deja en el banco a propósito: los usuarios
preguntan así, y quitarla porque el sistema la falla sería maquillar el número.

---

## 5. El interruptor

```env
# backend-clinic/.env  (gitignored)
CLINIC_LLM_ENABLED=true     # false apaga la IA sin tocar código
CLINIC_LLM_MODEL=llama3.2:3b
CLINIC_LLM_URL=http://localhost:11434/v1
```

Se reutiliza el flag que ya gobierna la narrativa asistida (ADR-0024): es el
mismo interruptor conceptual —«¿hay IA disponible?»— y dos banderas separadas se
desincronizan.

Para probarlo sin editar el `.env`: `manage.py demo_tools --sin-ia`.

---

## 6. El código, explicado

### 6.1 Una herramienta es un dato, no un `if`

Cada herramienta se declara una sola vez. `description` es lo único que el modelo
lee para decidir, así que se escribe **para el modelo**, no para un humano.
`keywords` son las palabras del dominio que la resuelven sin gastar el modelo, y
`source` es la tabla real, que viaja hasta la pantalla como procedencia.

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str                 # lo único que ve el LLM para elegir
    source: str                      # tabla real, para la procedencia
    keywords: tuple[str, ...]        # resuelven SIN modelo
    run: Callable[[], list[dict]]    # la consulta: Django ORM puro


CATALOGO: tuple[ToolSpec, ...] = (
    ToolSpec(
        name='CROMOSOMAS_PARA_REVISION',
        description=(
            'Lista los cromosomas marcados en naranja: los que el modelo de IA '
            'clasificó con confianza por debajo del umbral (85%) y que el analista '
            'todavía no resolvió. Úsala para preguntas sobre qué cromosomas '
            'requieren atención, revisión manual o tienen baja confianza.'
        ),
        source='clinic_chromosomes',
        keywords=('naranja', 'naranjas', 'baja confianza', 'sin resolver'),
        run=cromosomas_para_revision,
    ),
    ...
)
```

Agregar una herramienta es agregar una entrada a esta tupla. El enrutador no se
toca: ni el catálogo que se le publica al modelo, ni el mensaje de «no sé», ni
el endpoint.

### 6.2 El modelo devuelve un NOMBRE, no una respuesta

Este es el punto entero de la tarea. Al modelo se le pide un JSON con el nombre
de una herramienta —`temperature=0.0`, porque enrutar es determinista, no
creativo— y ahí termina su participación.

```python
def _elegir_con_modelo(pregunta: str) -> tuple[str, str]:
    """Pide al modelo el NOMBRE de una herramienta. Devuelve (nombre, motivo)."""
    client = OpenAI(base_url=settings.CLINIC_LLM_URL, api_key='ollama')
    resp = client.chat.completions.create(
        model=settings.CLINIC_LLM_MODEL,          # fijo: llama3.2:3b
        messages=[{'role': 'system', 'content': _prompt_sistema()},
                  {'role': 'user',   'content': pregunta}],
        response_format=SELECCION_JSON_SCHEMA,    # enum de nombres válidos
        temperature=0.0,
        max_tokens=200,
    )
    datos = json.loads(resp.choices[0].message.content or '{}')
    return datos.get('herramienta', 'NINGUNA'), datos.get('motivo', '')
```

El modelo **nunca ve la base de datos**. No recibe filas, no recibe conteos y no
redacta ningún dato: recibe la pregunta y devuelve una cadena.

### 6.3 Los tres caminos, en orden

```python
def responder(pregunta: str) -> Respuesta:
    inicio = time.time()

    # Camino 1 — vocabulario del dominio. NO llama al modelo.
    tool = buscar_por_palabra_clave(pregunta)
    if tool is not None:
        return _ejecutar(tool, 'KEYWORD', inicio)

    # Camino 2 — el modelo elige. Solo si la IA está habilitada.
    if not settings.CLINIC_LLM_ENABLED:              # ← EL INTERRUPTOR
        return _sin_match(inicio, 'La asistencia por IA está desactivada y la '
                                  'consulta no usa el vocabulario del catálogo.')
    try:
        nombre, motivo = _elegir_con_modelo(pregunta)
    except Exception as exc:                          # degradación, no caída
        logger.warning('Enrutador LLM no disponible: %s', exc)
        return _sin_match(inicio, 'La asistencia por IA no está disponible.')

    # El modelo puede devolver un nombre inexistente pese al enum: se verifica
    # contra el catálogo en vez de confiar en que respetó el contrato.
    if nombre == 'NINGUNA' or nombre not in POR_NOMBRE:
        return _sin_match(inicio, 'Ninguna herramienta del catálogo responde eso.')

    # Camino 3 — ejecuta la herramienta que el MODELO eligió.
    return _ejecutar(POR_NOMBRE[nombre], 'LLM', inicio, motivo)
```

Tres detalles deliberados:

1. **El interruptor está antes de la llamada al modelo**, no dentro. Apagado, el
   camino KEYWORD sigue intacto: eso es el escenario 4.
2. **Un fallo del modelo degrada, no rompe.** Si Ollama está caído, la respuesta
   es «no sé» con el catálogo, no un error 500 (RN-07).
3. **El nombre se valida contra el catálogo.** `strict: true` en el esquema no es
   garantía suficiente; el modelo puede inventar un nombre y hay un test que
   cubre exactamente ese caso.

### 6.4 El código produce la respuesta

`_ejecutar` es el único sitio donde se obtienen datos, y llama a Django ORM:

```python
def _ejecutar(tool, camino, inicio, motivo=''):
    filas = tool.run()                    # Django ORM. El modelo no interviene.
    return Respuesta(
        camino=camino, tool=tool.name, source=tool.source,
        filas=filas, motivo=motivo,
        latency_ms=int((time.time() - inicio) * 1000),
    )
```

Que `filas` salga siempre de `tool.run()` es lo que hace que el escenario 1 y el
2 devuelvan **exactamente los mismos datos** por caminos distintos. Hay un test
que compara ambas salidas: si difirieran, significaría que el modelo influyó en
la respuesta.

---

## 7. Endpoint

```
POST /api/clinic/tools/query/   {"pregunta": "..."}
GET  /api/clinic/tools/query/   → publica el catálogo
```

**Siempre responde 200.** Una pregunta fuera de alcance no es un error del
cliente: devuelve `camino: SIN_MATCH` con el catálogo de lo que sí se puede
consultar.

---

## 8. Qué no funcionó

Vale la pena documentarlo porque la consigna lo pide y porque son hallazgos
reales, no hipotéticos:

**La latencia del camino LLM es alta: ~97 segundos** contra 7 ms del camino
KEYWORD. Es el costo de un modelo de 3B en CPU sin GPU. En producción, o se
amplía el catálogo de palabras clave (que resuelve la mayoría de las preguntas
reales), o se corre el modelo en hardware con GPU. La arquitectura de dos caminos
existe justamente por esto.

**El modelo puede devolver un nombre que no está en el enum**, pese a declarar
`strict: true` en el esquema. Por eso el enrutador verifica que el nombre exista
en el catálogo antes de ejecutar, en vez de confiar en que el modelo respetó el
contrato. Está cubierto por un test.

**La consola de Windows (cp1252) rompe con caracteres Unicode** — flechas,
comillas angulares, guiones largos. La primera corrida del comando falló con
`UnicodeEncodeError`. Se resolvió usando solo ASCII en la salida.

**Los cromosomas naranjas del seed original ya estaban resueltos**, así que la
herramienta principal devolvía cero filas. Hubo que sembrar un caso específico
(`seed_demo_tools`) para que la demo mostrara datos reales.

---

## 9. Archivos

| Archivo | Rol |
|---|---|
| `backend-clinic/apps/samples/tools.py` | Catálogo + las consultas (Django ORM) |
| `backend-clinic/apps/samples/tool_router.py` | Enrutador: KEYWORD / LLM / SIN_MATCH |
| `backend-clinic/apps/samples/views.py` → `ToolQueryView` | Endpoint |
| `backend-clinic/apps/samples/management/commands/demo_tools.py` | Los cuatro escenarios |
| `backend-clinic/apps/samples/management/commands/seed_demo_tools.py` | Datos para la demo |
| `backend-clinic/apps/samples/management/commands/eval_enrutado.py` | Banco de 30 preguntas etiquetadas + medición |
| `backend-clinic/apps/samples/tests/test_tool_router.py` | 31 tests |

**Tests:** 31, sin necesidad de Ollama corriendo (el modelo se sustituye por
dobles). El más importante verifica que **el escenario 1 y el 2 devuelvan
exactamente los mismos datos** — si difirieran, significaría que el modelo influyó
en la respuesta.

```bash
.venv/Scripts/python -m pytest apps/samples/tests/test_tool_router.py -v --no-cov
```
