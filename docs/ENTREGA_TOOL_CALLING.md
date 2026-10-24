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

## 1-bis. Contexto del dominio (para quien no viene del área)

Esta sección existe para que la entrega se pueda evaluar sin conocer
citogenética. **Nada de lo que sigue es requisito de la consigna**: es el mínimo
para que las cuatro herramientas tengan sentido.

### Qué es un cariotipo

Un **cariotipo** es el retrato ordenado de los 46 cromosomas de una persona.
Sirve para detectar alteraciones genéticas: un cromosoma de más, uno de menos, un
trozo cambiado de sitio. El síndrome de Down, por ejemplo, es una tercera copia
del cromosoma 21.

El resultado se escribe en una nomenclatura internacional, **ISCN**:

```
46,XY        varón sin alteraciones numéricas
47,XX,+21    mujer con una copia extra del cromosoma 21 (síndrome de Down)
```

### Cómo se produce en el laboratorio

1. Se cultiva una muestra de sangre y se detiene la división celular en
   **metafase**, el único momento en que los cromosomas se ven al microscopio
   como cuerpos separados.
2. Se fotografía una célula. Esa imagen —la metafase— muestra los 46 cromosomas
   **desordenados, girados y a menudo tocándose entre sí**.
3. Alguien recorta cada cromosoma y los ordena por parejas, del 1 al 22 más los
   sexuales. A ese resultado ordenado se le llama **cariograma**.
4. Se redacta el informe con la nomenclatura ISCN.

Hecho a mano, el paso 3 es el caro: entre 20 y 30 minutos de trabajo experto por
caso. **Eso es lo que este sistema automatiza.**

### Dónde entra la IA, y por qué hay dos IA distintas

| | Qué hace | Tipo |
|---|---|---|
| EfficientNet-B3 | Mira el recorte de un cromosoma y dice **cuál de los 24 es** | IA **discriminativa** (imagen → etiqueta) |
| `llama3.2:3b` (este módulo) | Elige **qué consulta** responde una pregunta escrita en castellano | IA **generativa** (texto → texto) |

No compiten: la primera clasifica imágenes y **nunca ve texto**; la segunda
enruta preguntas y **nunca ve la base de datos**.

### El semáforo: por qué existen los «cromosomas naranjas»

El clasificador no solo dice qué cromosoma es, también **cuánta confianza tiene**.
El sistema lo traduce a un color:

| Color | Condición | Significado |
|---|---|---|
| Verde | confianza ≥ 0,85 | La IA está segura |
| **Naranja** | confianza < 0,85 | **La IA duda: lo revisa una persona** |
| Rojo | sin confianza | La clasificación falló |

Una regla clínica del proyecto (**RN-02**) obliga a que ningún caso con naranjas
sin resolver pueda emitir informe. Es el mecanismo *human-in-the-loop*: un
cariotipo es un diagnóstico, y un modelo que acierta el 70% no puede firmarlo
solo. En vez de exigir revisión manual de los 46 cromosomas —lo que anularía el
valor de automatizar— **se concentra la atención humana donde la máquina flaquea**.

### El flujo de un caso, que es lo que consultan las herramientas

```
   registrada ──> EN PROCESO ──> VALIDADA ──> FIRMADA ──> REPORTADA
                  (la IA          (el analista  (el supervisor   (informe
                   analiza)        resolvió      firmó con        emitido
                                   los naranjas)  segundo factor)  con ISCN)
```

Las cuatro herramientas publicadas responden **«¿qué hay en cada etapa?»**:

| Herramienta | Pregunta que responde |
|---|---|
| `CASOS_EN_PROCESO` | ¿Qué está analizando el sistema ahora? |
| `CROMOSOMAS_PARA_REVISION` | ¿Qué le toca revisar al analista? (los naranjas) |
| `CASOS_PENDIENTES_FIRMA` | ¿Qué espera la firma del supervisor? |
| `CASOS_REPORTADOS` | ¿Qué ya se entregó al médico? |

Por eso la herramienta de cromosomas no responde una curiosidad: responde
**«¿qué trabajo tengo pendiente?»**. Y por eso importó descubrir que la lista
truncaba en silencio —mostraba 50 de 100— sin avisar: un analista podía creer
tener su cola vacía faltándole la mitad.

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
Latencia    : 33 ms
50 resultado(s) — se muestran los primeros 50, puede haber más.
  - caso=CHN-2026-08-06-0001 | clase=1 | confianza=17.2% | estado=Pendiente de revisión
  - caso=CHN-2026-08-06-9208 | clase=1 | confianza=17.2% | estado=Pendiente de revisión
  - caso=CHN-2026-08-06-9329 | clase=1 | confianza=17.2% | estado=Pendiente de revisión
  - caso=CHN-2026-08-06-0001 | clase=5 | confianza=25.9% | estado=Pendiente de revisión
  - caso=CHN-2026-08-06-9208 | clase=5 | confianza=25.9% | estado=Pendiente de revisión
  ... y 45 más
```

> Los datos son **reales**, de casos registrados por el pipeline, no sembrados
> para la demo. Las confianzas bajas (17,2%) vienen de la segmentación clásica
> sobre metafases crudas, que es una limitación conocida del pipeline de visión y
> ajena a este módulo. La consulta ordena por confianza ascendente: se muestran
> primero los cromosomas más dudosos, que es lo que el analista debe mirar antes.

### Escenario 2 — Sinónimo

**Pregunta:** «¿Cuáles necesitan que el analista los mire de nuevo?»
Ninguna palabra del catálogo coincide → escala al modelo, que elige la misma
herramienta. **Mismas filas que el escenario 1.**

```
Camino      : LLM
Herramienta : CROMOSOMAS_PARA_REVISION
Fuente      : clinic_chromosomes
Motivo (LLM): dudosos o mal clasificados
Latencia    : 190386 ms
50 resultado(s) — se muestran los primeros 50, puede haber más.
  - caso=CHN-2026-08-06-0001 | clase=1 | confianza=17.2% | estado=Pendiente de revisión
  - caso=CHN-2026-08-06-9208 | clase=1 | confianza=17.2% | estado=Pendiente de revisión
  ... y 48 más   ← idénticas al escenario 1
```

> **La latencia varía mucho entre corridas.** Esta dio 190 s; otras sobre el
> mismo equipo dieron 22 s y 335 s para la misma pregunta, según lo que Ollama
> tuviera cargado. Lo estable es el orden de magnitud frente a los 28 ms del
> camino KEYWORD, no la cifra concreta.

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
Latencia    : 28 ms
50 resultado(s) — se muestran los primeros 50, puede haber más.
  - caso=CHN-2026-08-06-0001 | clase=1 | confianza=17.2% | estado=Pendiente de revisión
  ... y 49 más   ← idénticas al escenario 1, con la IA apagada
```

**28 ms contra 190 386 ms del escenario 2**: el mismo dato, por el camino que no
llama al modelo. Esa es la prueba de que la respuesta la produce el código.

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

| Banco de **30** preguntas | Primera medición | Prompt endurecido | Descripciones equilibradas |
|---|---|---|---|
| **Fuera de alcance** | 2/6 — **33%** | 6/6 — 100% | 6/6 — 100% |
| Dentro de alcance | 22/24 — 92% | 21/24 — 88% | 23/24 — 96% |
| **Global** | 24/30 — 80% | 27/30 — 90% | 29/30 — **97%** |

> **Ese 97% no era real.** Al ampliar el banco a 56 preguntas se derrumbó a 80%.
> El apartado 4-ter explica por qué, y es el hallazgo más importante del trabajo.

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

## 4-ter. El 97% era un espejismo del banco pequeño

Las 6 preguntas fuera de alcance del primer banco (presupuesto, jefe del
servicio, precio de un cariotipo…) **no compartían ni una palabra con el
catálogo**. Abstenerse ante ellas es fácil. Al ampliar el banco a 56 preguntas,
con 18 fuera de alcance —seis de ellas **adversarias**: fuera de alcance pero
escritas con el vocabulario del propio dominio— el resultado fue otro:

| | Banco de 30 | Banco de 56 | Banco de 56, tras corregir |
|---|---|---|---|
| Global | 29/30 — 97% | 45/56 — 80% | **48/56 — 86%** |
| Dentro de alcance | 23/24 — 96% | 34/38 — 89% | 34/38 — 89% |
| **Fuera de alcance** | 6/6 — 100% | **11/18 — 61%** | 14/18 — **78%** |

El patrón de los fallos es nítido: **las preguntas sobre los conceptos que las
herramientas manipulan van a parar a la herramienta dueña del concepto.**

```
«¿Cómo se calcula la nomenclatura ISCN?»      -> CROMOSOMAS_PARA_REVISION
«¿Quién tiene permiso para firmar un caso?»   -> CASOS_PENDIENTES_FIRMA
«¿Cuánto tarda en procesar una muestra?»      -> CASOS_EN_PROCESO
«¿Qué umbral de confianza deberíamos usar?»   -> CROMOSOMAS_PARA_REVISION
```

### Los dos puntos ciegos del camino rápido

El banco ampliado destapó además dos límites **estructurales** de la
coincidencia literal, no defectos del catálogo:

```
[KEYWORD] «¿Qué significa que un cromosoma esté naranja?»      -> CROMOSOMAS_PARA_REVISION
[KEYWORD] «¿Qué estudios están validados pero NO cerrados?»    -> CASOS_REPORTADOS
```

La primera es una pregunta de documentación que contiene «naranja»: **el atajo
no sabe abstenerse**, porque abstenerse exige entender, y él solo mira si una
cadena aparece. La segunda pide lo contrario de lo que devuelve: **el atajo no
ve la negación**. Ninguna de las dos llega siquiera al modelo.

**La corrección** fue enseñarle al atajo a reconocer cuándo *no* debe opinar y
ceder la pregunta al modelo: cuando pide una explicación («qué significa», «por
qué», «quién puede», «cuánto tarda») o cuando niega. Y en el prompt se añadió la
categoría que faltaba —reglas, permisos, umbrales, metodología— con una regla de
forma como desempate: *si la pregunta se responde con una lista de casos o
cromosomas que existen ahora, hay herramienta; si pide una explicación, una
definición, un permiso o un número calculado, no la hay.*

### Una regresión que casi se cuela

Al escribir el detector de negación se incluyó « sin » como marca. Es negación en
castellano — pero también forma parte de dos claves del catálogo, `sin resolver`
y `sin firmar`. Con eso, «¿qué cromosomas están sin resolver?» dejaba de
resolverse por el atajo y, **con la IA apagada, habría respondido «no sé» en vez
de dar los datos**: justo la propiedad que el escenario 4 existe para demostrar.

Se detectó comprobando el detector contra el banco *antes* de medir (segundos)
en lugar de después (25 minutos). Tras corregirlo: cero colisiones con claves del
catálogo, y el atajo dispara en 5 preguntas con 5 aciertos y **0 falsos
positivos** — antes fallaba 3.

### Qué consiguió la corrección, y qué no

La abstención subió de 61% a 78%: se recuperaron las tres preguntas sobre reglas
y permisos («cómo se calcula el ISCN», «quién tiene permiso para firmar», «qué
umbral usar»). El global pasó de 80% a **86%**.

Pero conviene leer el detalle antes de darlo por resuelto:

**El guardián del atajo funcionó y aun así el resultado no cambió** para las dos
preguntas de «naranja». Ya no las intercepta la coincidencia literal —ahora
llegan al modelo, que es lo que se buscaba— y el modelo también las falla, hacia
la misma herramienta. El arreglo era correcto y necesario, pero **movió el fallo
de sitio en vez de eliminarlo**. Presentarlo como resuelto sería falso.

**Dentro de alcance el número no se movió (34/38), pero cambió la composición.**
Se arregló la pregunta con negación y apareció otra: «¿cuánto falta para que
terminen las muestras de hoy?» ahora se abstiene. Revisándola, **la etiqueta del
banco estaba mal**: la herramienta lista las muestras en proceso, no puede
calcular cuánto tiempo falta. Abstenerse es la respuesta correcta y el error
estaba en lo que se esperaba, no en el sistema. Se deja anotado en vez de
corregir la etiqueta a posteriori, que sería ajustar la vara al resultado.

### Limitación metodológica

Este número sale de tres iteraciones de ajuste contra **el mismo banco**. Los
arreglos atacan clases de fallo (preguntas explicativas, negación, preguntas
sobre reglas) y no ejemplos concretos, pero a partir de aquí la medida está
contaminada: refleja lo bien que se ajustó a *estas* 56 preguntas, no lo bien que
enruta en general. La prueba honesta sería un conjunto nuevo, escrito sin mirar
los fallos. Queda pendiente y se declara.

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

**La latencia del camino LLM es alta y empeoró al corregir la abstención**,
contra 28 ms del camino KEYWORD. Y es muy **inestable**: en corridas distintas
sobre el mismo equipo se midieron **22 s, 190 s y 335 s** para la misma pregunta,
según lo que Ollama tuviera cargado en memoria. Antes de endurecer el prompt
rondaba los 94 s. Son entre tres y cuatro órdenes de magnitud sobre el camino
rápido, con una varianza que por sí sola desaconseja el uso interactivo.

La causa es directa: enseñar al modelo a abstenerse exigió
un prompt de sistema mucho más largo (categorías de lo que no cubre, regla de
forma, fronteras entre herramientas), y en un modelo de 3B sobre CPU cada token
del prompt se paga en cada consulta.

**Es un intercambio deliberado, no un descuido:** se cambió velocidad por no dar
datos equivocados. En producción se resuelve con GPU o con un catálogo de
palabras clave más amplio; la arquitectura de dos caminos existe justamente para
que la mayoría de las preguntas no paguen ese coste.

**El modelo puede devolver un nombre que no está en el enum**, pese a declarar
`strict: true` en el esquema. Por eso el enrutador verifica que el nombre exista
en el catálogo antes de ejecutar, en vez de confiar en que el modelo respetó el
contrato. Está cubierto por un test.

**La respuesta truncaba en silencio: mostraba 50 de 100 cromosomas naranjas
diciendo «50 resultado(s)».** El `[:50]` estaba escrito a pelo en tres consultas,
sin nombre y sin comentario, así que nada delataba que fuera un tope. En una
consulta cualquiera sería un detalle; aquí la respuesta significa «estos son los
cromosomas que hay que revisar», y un analista que la leyera creería haber visto
toda su cola de trabajo cuando le faltaba la mitad. Corregido con `LIMITE_FILAS`
y un aviso explícito («se muestran los primeros 50, puede haber más»), fijado con
tres tests. **Apareció por consultar datos reales en vez de datos sembrados.**

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
| `backend-clinic/apps/samples/management/commands/eval_enrutado.py` | Banco de 56 preguntas etiquetadas + medición |
| `backend-clinic/apps/samples/management/commands/demo_codigo_salida.py` | Imprime el código que llama al modelo y su salida, en la misma pantalla |
| `backend-clinic/apps/samples/tests/test_tool_router.py` | 34 tests |

**Tests:** 34, sin necesidad de Ollama corriendo (el modelo se sustituye por
dobles). El más importante verifica que **el escenario 1 y el 2 devuelvan
exactamente los mismos datos** — si difirieran, significaría que el modelo influyó
en la respuesta. Los 3 últimos fijan el aviso de truncado (§8).

### Código y salida en una sola captura

```bash
python manage.py demo_codigo_salida
```

Imprime `_elegir_con_modelo()` y **acto seguido lo ejecuta** con la pregunta del
escenario 2. El código no está copiado en el comando: se lee de la fuente real
con `inspect.getsource()`, así que lo que se ve impreso es literalmente la
función que corre un segundo después — no pueden divergir.

```bash
.venv/Scripts/python -m pytest apps/samples/tests/test_tool_router.py -v --no-cov
```
