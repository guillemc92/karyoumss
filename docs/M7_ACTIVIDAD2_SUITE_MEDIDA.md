# Actividad 2 — Suite medida, sin duplicados, con tests nuevos en tres capas

| | |
|---|---|
| **Equipo** | **BIOMED UMSS** |
| **Integrante** | Ing. Guillermo Mamani Chambi (individual, G04) |
| Módulo | M7 — Pruebas y Validación de Modelos IA |
| Producto | Plataforma de Cariotipado Asistido por IA |
| Módulo medido | `backend-clinic` (bounded context clínico) |
| Rama | `feature/clinic-django-stack` |
| Fecha | 7 de septiembre de 2026 |

---

## 1 · Cobertura antes y después

**El número de pytest-cov no sirve para decidir.** Incluye los propios ficheros
de test, que están al 100 % por construcción. Y los `management/commands/` son
guiones de demostración y evaluadores que se lanzan a mano: cubrirlos con unit
tests sería inflar la cifra sin proteger nada.

Por eso se reportan tres, y la que manda es la última:

| Alcance | Antes | Actividad 2 | Frontera | Contrato | Últimos huecos | Δ total |
|---|---:|---:|---:|---:|---:|---:|
| Lo que reporta `pytest-cov` | 82,25 % | 84,04 % | 86,00 % | 86,82 % | 88,54 % | +6,29 pp |
| Sin ficheros de test | 65,41 % | — | — | — | — | — |
| **Código de producción** (sin tests ni CLI) | **85,63 %** | **88,60 %** | **91,74 %** | **93,38 %** | **96,33 %** | **+10,70 pp** |

```
antes     46 ficheros · 2.798 sentencias · 2.396 cubiertas
act. 2    47 ficheros · 2.806 sentencias · 2.486 cubiertas
frontera  47 ficheros · 2.809 sentencias · 2.577 cubiertas
contrato  47 ficheros · 2.809 sentencias · 2.623 cubiertas
final     47 ficheros · 2.809 sentencias · 2.706 cubiertas
tests     627 → 663 → 724 → 784 → 863   (+236)
```

**El código de producción del clínico pasa el 90 % que exige RN-09 y termina en
96,33 %.** De las 103 sentencias que quedan sin cubrir, **45 están en cuatro
migraciones de seed** —código que se ejecutó una vez al aplicar la migración y
no se vuelve a ejecutar—: descontadas esas, el código vivo está al **97,76 %**.

Las tres sentencias que aparecen de más entre la Actividad 2 y el cierre son el
guard que se añadió a `agente_acciones.ejecutar` — ver §4.

Reproducible con:

```bash
cd backend-clinic
.venv/Scripts/python -m pytest --cov=. --cov-report=json:cov.json --cov-fail-under=0
.venv/Scripts/python scripts/cobertura_produccion.py cov.json apps/
```

El segundo argumento acota el agregado a `apps/`, que es el alcance de las
mediciones anteriores: deja fuera `manage.py`, `wsgi/asgi` y los dos guiones MCP
sueltos, que no son código de dominio. Los porcentajes por fichero no dependen
de ese recorte; lo que cambia es sobre qué población se suman.

### Los huecos que la medición encontró

| Módulo | Antes | Después | Sentencias que faltaban |
|---|---:|---:|---:|
| **`rag_qa.py`** | **0,0 %** | **100 %** | **62** |
| `rag_index.py` | 37,8 % | **100 %** | 51 |
| `agente_acciones.py` | 40,7 % | **100 %** | 16 |
| `admin_client.py` | 52,9 % | **100 %** | 16 |
| `pipeline_client.py` | 67,5 % | **100 %** | 25 |

`rag_qa.py` es el que decide **si el sistema responde una pregunta clínica o
dice que no sabe**, y no tenía ni una prueba. Es el hueco que se atacó primero.

Los cinco están en la **frontera** —modelo, disco y red—, que es exactamente
donde la consigna pide dobles. Los cinco quedan cerrados: 170 sentencias que
antes nadie ejercitaba.

---

## 2 · Duplicados

### Cómo se buscaron

La consigna define duplicado como *misma función bajo prueba, mismos datos de
entrada y mismo assert, **aunque el nombre cambie***. Comparar texto no vale, así
que se compara una huella del **AST** de cada test: llamadas, literales, asserts
normalizados, fixtures y decoradores.

Se analizaron **820 tests con assert** de los tres backends. El detector está
versionado en [`scripts/detectar_duplicados.py`](../scripts/detectar_duplicados.py)
y se vuelve a correr sin argumentos:

```bash
python scripts/detectar_duplicados.py
```

Se volvió a correr tras cada tanda —**897** tras el cierre de frontera, **917**
tras el contrato de errores y **968** al final— y devolvió 0 grupos las tres
veces (§6).

### La primera pasada dio 9 grupos, y los 9 eran falsos

Es justo lo que la consigna advierte: *«el agente puede marcar como duplicado lo
que solo se parece»*. Los fallos eran de la huella, no de la suite:

| Qué ignoraba la huella | Ejemplo que confundía | Por qué importa |
|---|---|---|
| Las **fixtures** | `test_supervisor_ve` vs `test_admin_ve` | en pytest **la fixture ES el dato de entrada** |
| Las **constantes de módulo** | `URL` vs `MODELS_ACTIVE_URL` | son endpoints distintos |
| El cuerpo de las **comprensiones** | `all(e.fuente…)` vs `all(e.nombre…)` | afirman propiedades distintas |
| La **ruta del atributo** | `AppearancePreference…count()` vs `Notification…` | modelos distintos |

Corregidos los cuatro: **de 9 grupos a 1**.

### Tabla de duplicados

| Test | Con cuál se duplica | Decisión |
|---|---|---|
| `test_anon_returns_401` (`test_audit_endpoint.py:39`) | `test_anon_returns_401` (mismo fichero, **línea 20**) | **Omitido** — renombrado a `test_anon_returns_401_duplicado` |
| `test_supervisor_ve_cualquiera` | *(candidato descartado)* | **No es duplicado** — prueba un rol distinto |
| `test_admin_ve_cualquiera` | *(candidato descartado)* | **No es duplicado** — prueba un rol distinto |
| `test_analista_no_puede_eliminar_403` | *(candidato descartado)* | **No es duplicado** — rol distinto |
| `test_supervisor_no_puede_eliminar_403` | *(candidato descartado)* | **No es duplicado** — rol distinto |
| `test_toda_entrada_cita_su_fuente` | *(candidato descartado)* | **No es duplicado** — afirma `fuente`, el otro `nombre`+`descripcion` |
| `test_get_without_auth_returns_401` ×5 | *(candidatos descartados)* | **No son duplicados** — cada uno protege un endpoint distinto |
| `test_get_idempotent` (appearance / notifications) | *(candidato descartado)* | **No es duplicado** — modelos y URLs distintos |

### El duplicado real era peor de lo que parecía

Los dos `test_anon_returns_401` **compartían nombre dentro de la misma clase**.
En Python la segunda definición sustituye a la primera, así que pytest solo
recogía una: **el test de la línea 20 no se había ejecutado nunca**.

No es solo un duplicado — es un test muerto. Por eso no bastaba con marcar
`skip`: eso habría silenciado al único que sí corría. Se **renombró** el segundo
y se omitió, con lo que el original volvió a la vida. El fichero pasó de 12 a
**12 pasan + 1 omitido**.

---

## 3 · Tests omitidos, con su motivo

Ninguno se ha borrado. Siguen en el repositorio, marcados con `@pytest.mark.skip`
y su razón escrita en el propio código.

| Test | Fichero | Motivo |
|---|---|---|
| `test_anon_returns_401_duplicado` | `backend-admin/apps/audit/tests/test_audit_endpoint.py:39` | Duplicado exacto del de la línea 20: misma fixture, misma URL, mismo assert. Además compartían nombre, lo que impedía que el original se ejecutara. Se conserva como evidencia del hallazgo. |

---

## 4 · Tests nuevos por capa

| Capa | Propuestos | Aceptados | Descartados / corregidos | Fichero |
|---|---:|---:|---:|---|
| **Unit** | 18 | **18** | 0 | `test_rag_qa.py` |
| **Integración** | 4 | **4** | 2 corregidos en auditoría | `test_integracion_rag_flujo.py` |
| **Contrato** | 14 | **14** | 0 | `test_contrato_karyotype.py` |
| *(detección de duplicados)* | 9 grupos | 1 | **8 descartados** | — |
| **Subtotal Actividad 2** | **36** | **36** | — | |
| Unit — frontera MFA | 10 | **10** | 0 | `test_admin_client.py` |
| Unit — frontera backend-ml | 17 | **17** | 0 | `test_pipeline_client.py` (ampliado) |
| Unit — despachador del agente | 17 | **17** | 0 | `test_agente_acciones.py` |
| Unit — índice y embeddings | 17 | **17** | 0 | `test_rag_index.py` |
| **Subtotal cierre de huecos** | **61** | **61** | — | |
| Contrato — errores de los endpoints | 60 | **60** | 12 corregidos en auditoría | `test_contrato_errores_endpoints.py` |
| Contrato — resto del mapeo excepción → HTTP | 23 | **23** | 2 corregidos en auditoría | `test_contrato_errores_endpoints.py` (ampliado) |
| Unit — frontera del enrutador | 16 | **16** | 1 corregido en auditoría | `test_tool_router_frontera.py` |
| Unit — apertura de la sesión MCP | 8 | **8** | 0 | `test_mcp_apertura.py` |
| Unit — fuentes del corpus | 11 | **11** | 6 corregidos en auditoría | `test_rag_corpus_fuentes.py` |
| Unit — integridad y degradación | 16 | **16** | 4 corregidos en auditoría | `test_servicios_degradacion.py` |
| Unit — valor heredado sin cifrar | 3 | **3** | 0 | `test_fields.py` (ampliado) |
| Unit — imágenes malformadas | 4 | **4** | 0 | `test_imagen_metafase.py` (ampliado) |
| **Subtotal últimos huecos** | **81** | **81** | — | |
| **Total** | **238** | **238** | — | |

### Unit — `rag_qa.py`, de 0 % a 100 %

Los dobles están **en la frontera**, no dentro: se sustituyen las dos únicas
salidas del proceso —`indice()` (disco) y `OpenAI` (red)—, y todo lo demás corre
de verdad. Así las pruebas son deterministas, no gastan tokens y funcionan en un
pipeline sin Ollama.

Lo que más se afirma son los **caminos de degradación** (RN-07): sin índice, sin
modelo, con el modelo caído o devolviendo basura, el sistema **no revienta y no
inventa**.

El test que más protege: **una cita inventada se ignora**. Si el juez devuelve un
número de fragmento que no existe, el código descarta esa cita en vez de
fabricar una fuente. Un informe clínico que cita un documento inexistente es peor
que uno que no cita nada.

### Integración — el flujo real, con piezas reales

`entrada del usuario → recuperación → respuesta`, sobre un espacio temporal.

**Real:** la base vectorial (numpy, coseno de verdad), los ficheros
`vectores.npy` + `fragmentos.json` escritos y releídos del disco, el orden por
similitud, el corte por umbral, el reparto candidatos/vecinos y la resolución de
citas.
**Doblado:** solo las dos salidas de red — `embeber` y el juez.

Se afirma **el camino, no el resultado**. La prueba principal deja constancia de
cuatro tramos: que el índice se escribió y se releyó del disco, qué fragmento se
recuperó y en qué posición, qué texto llegó exactamente al juez, y que la cita
final apunta a un documento que estaba en el disco temporal. *Un test que solo
mirase `responde is True` pasaría aunque la recuperación devolviera el fragmento
equivocado.*

**Los dos corregidos en auditoría**, que es la parte que la consigna llama
intervención humana:

1. El primer diseño usaba vectores **ortogonales**. Solo un fragmento superaba
   el umbral, así que `candidatos[0]` y `candidatos[-1]` eran el mismo y la
   aserción de orden **fallaba**. Peor: no reproducía la realidad medida —en el
   corpus real todos los fragmentos se parecen porque hablan del mismo dominio,
   que es justo por lo que el umbral no discrimina. Se rehízo con vectores
   correlacionados.
2. El test del reparto **pasaba en vacío**: recorría una lista de vecinos que
   siempre estaba vacía. Se le añadió `assert r.vecinos` para que no pueda
   volver a pasar sin probar nada.

### Contrato — el endpoint principal

Valida **forma, tipos, catálogos y códigos HTTP**. No valida el contenido: que
un cromosoma salga de la clase 7 o de la 12 lo decide el modelo, y afirmarlo
produciría una prueba que falla cada vez que el clasificador mejora.

Incluye un test que **valida el propio esquema** (`check_schema`): un JSON Schema
mal escrito acepta cualquier cosa y no protege de nada.

### Cierre — los cuatro huecos que quedaban

Los cuatro estaban en la misma frontera y admitían el mismo tratamiento que
`rag_qa.py`: doblar la red y el disco, dejar real todo lo demás.

**`test_admin_client.py` (10)** — la verificación MFA de la firma del
supervisor, que es un acto de cumplimiento 21 CFR Part 11. La prueba que más
pesa es `test_ninguna_caida_se_traduce_en_veredicto`: pase lo que pase en la red
sale `MfaServiceError`, nunca un veredicto inventado. Degradar a `valid: True`
sería firmar sin segundo factor; degradar a `valid: False` en silencio haría
creer al supervisor que su código está mal cuando el problema es que
backend-admin está caído. El contador del circuito cuenta fallos **seguidos**:
`test_un_mfa_invalido_no_cuenta_como_fallo_del_servicio` fija que un supervisor
tecleando mal tres veces no deja sin firmar a todo el laboratorio.

**`test_pipeline_client.py` (+17)** — `segment_image`, `xai_heatmap` y
`classify_crop` comparten estructura, así que se prueban con **una batería
parametrizada** en lugar de tres bloques copiados: mañana se añade una fila, no
un bloque. Se afirma el suelo de timeout (30 s y 60 s): con los 2 s de
configuración, una Grad-CAM en CPU expiraría siempre y el circuito acabaría
abierto — el sistema entero parecería caído cuando lo único que pasa es que el
modelo tarda.

**`test_agente_acciones.py` (17)** — el despachador del agente. Es
**determinista** y se prueba con asserts: si el modelo *elige bien* la
herramienta es otra cosa, y se mide aparte con el banco de `eval_enrutado`.
`test_una_herramienta_nueva_aparece_sin_tocar_este_modulo` fija la propiedad que
impide que el agente y el servidor MCP se desincronicen.

**`test_rag_index.py` (17)** — `embeber` por lotes con progreso acumulado,
normalización a norma 1 (sin ella el umbral de 0,55 no significaría nada), un
vector nulo que no revienta la división, y que la ausencia de índice explique
**cómo** construirlo en vez de soltar un «fichero no encontrado».

#### Un defecto real que la cobertura destapó

El docstring de `agente_acciones.ejecutar` promete *«devuelve siempre un dict —
nunca lanza»*, y `agente_grafo.py:165` llama sin envolver apoyándose en esa
promesa. Pero `tool.run()` es una consulta al ORM: **una caída de la base salía
disparada hacia arriba y tumbaba el turno entero del agente**, en vez de llegar
al modelo como una observación de la que pudiera rectificar.

Se añadió el guard, y solo alrededor de las cuatro consultas de **lectura**. La
asimetría es deliberada y está probada en las dos direcciones
(`test_una_consulta_que_revienta_es_una_observacion_no_una_caida` y
`test_un_fallo_de_escritura_si_sale_disparado`): tragarse una excepción a mitad
de una escritura dejaría al modelo diciendo «hecho» sobre algo que no se guardó,
y RN-05 no admite eso.

Es el argumento de la consigna en un caso concreto: la cobertura no valía por el
número, sino porque al ir a cubrir esas 16 sentencias apareció una diferencia
entre lo que el código decía hacer y lo que hacía.

### Contrato — los errores de los endpoints

`views.py` era el hueco grande que quedaba: **80 %, 87 sentencias sin cubrir**,
casi todas ramas de error de endpoints cuyo camino feliz sí estaba probado.

El diagnóstico fue más concreto que «falta cobertura». Los servicios están bien
probados —`test_supervisor_s2.py` comprueba que `sign_report` levanta
`MfaLockedError` cuando toca—, pero **nadie comprobaba el tramo siguiente**: que
la vista traduzca esa excepción al código HTTP que el frontend espera. Si
`MfaLockedError` acabara devolviendo 500 en vez de 423, los tests de servicio
seguirían en verde y la pantalla del supervisor diría «error del sistema» donde
debe decir «cuenta bloqueada». Catorce códigos del contrato no aparecían en
ninguna prueba del clínico.

Se probó **en tabla, no un test por endpoint**: doce endpoints de cromosoma
repiten literalmente las mismas dos guardas, y probarlas una a una serían 24
tests casi idénticos — la clase de duplicado que la §2 buscaba. Un endpoint
nuevo que olvide una guarda aparece como una fila roja el día que se añada a la
lista.

`views.py` pasa de **80 % a 90,4 %**.

#### Doce de las sesenta fallaron en la primera pasada, y las tres causas eran reales

| Lo que yo suponía | Lo que el sistema hace | Qué se hizo |
|---|---|---|
| Desactivar una muestra es `is_active = False` | Hay una CHECK en la base, `samples_deactivated_implies_deleted_at`: desactivar sin registrar **cuándo** es un dato perdido | Un helper `borrar()` que pone las dos columnas y explica por qué van juntas |
| Un analista ajeno recibe `NOT_OWNER` en `narrative` e `iscn` | Esos dos exigen `case.sign`, que solo tienen Supervisor y Admin — y la guarda deja pasar a todo `is_staff` sin mirar de quién es el caso | Se separó la tabla: para esos dos la rama `NOT_OWNER` es **inalcanzable**, y así queda escrito en vez de forzarse |
| El supervisor no puede sobrescribir el ISCN | La matriz sembrada le da `case.override_iscn` a **todo** Supervisor | Se alcanza la rama con el mecanismo real del RBAC portado de MetaClass: una **excepción individual** que quita la opción (ADR-0019, deny-overrides) |

Las tres son el mismo patrón que la §2 ya había mostrado con los duplicados: la
primera medición dice más sobre las suposiciones del que mide que sobre el
sistema. Ninguna se «arregló» quitando el assert.

---

### Los últimos huecos — lo que solo pasa cuando algo va mal

Cerrados los cinco de frontera y el contrato de errores, lo que quedaba en el
clínico eran ramas defensivas: las que solo se ejecutan cuando la entrada está
mal, el disco falla o alguien manipula la base. Son las más fáciles de dejar sin
probar y las que peor fallan, porque nadie las ve fallar hasta que hace falta.

| Módulo | Antes | Después | Qué se cubrió |
|---|---:|---:|---|
| `tool_router.py` | 75,6 % | **100 %** | el prompt del enrutador, la llamada real al modelo y el camino RAG |
| `mcp_conexion.py` | 83,8 % | **100 %** | la apertura y el cierre reales de la sesión MCP |
| `rag_corpus.py` | 85,2 % | **100 %** | qué documentos entran al corpus y cuáles se ignoran |
| `services.py` | 95,0 % | **99 %** | integridad de la cadena, bloqueo y degradación |
| `imagen.py` | 89,4 % | **95,7 %** | ficheros truncados y formatos desconocidos |
| `fields.py` | 88,9 % | **100 %** | valores heredados que no son un token Fernet |
| `views.py` | 90,4 % | **94,4 %** | el resto del mapeo excepción → código HTTP |

#### El enrutador: probado a fondo, y con tres piezas sin ejecutar nunca

`test_tool_router.py` prueba muy bien los tres caminos —KEYWORD, LLM,
SIN_MATCH—, pero para hacerlo sustituye `_elegir_con_modelo` en **todos** sus
tests. Es la decisión correcta allí. El efecto lateral es que tres piezas no se
ejecutaban nunca: el prompt del sistema, la llamada real y el camino documental.

No es cobertura por la cobertura. `_prompt_sistema` **es** el contrato con el
modelo: si se añade una herramienta al catálogo y el prompt no la lista, el
modelo no puede elegirla — y ningún test de enrutado lo detectaría, precisamente
porque todos doblan la elección.

#### Tres hallazgos que la cobertura destapó

**1. `QuerySet.update()` esquiva el guard append-only de RN-05.** El guard vive
en `Model.save()`, así que protege del error honesto —un `save()` de más en un
servicio— pero no de la manipulación: un `.update()` reescribe el payload de un
evento de auditoría sin que el modelo se entere. Lo que sí lo detecta es la
cadena de hashes… y `verify_audit_chain` **nunca se había probado con datos
manipulados**: solo se había ejercitado con cadenas intactas. Una función de
verificación que solo se prueba en verde no está probada. Las dos capas quedan
ahora fijadas por separado, con su alcance real escrito.

**2. El troceador descarta en silencio los fragmentos de menos de 120
caracteres.** El documento se lee bien, no hay error, y simplemente no entra al
índice. Es la decisión correcta —un fragmento de dos líneas no lleva contexto
suficiente para que su embedding signifique algo— pero al ser invisible, una
regresión tampoco haría ruido: el RAG contestaría «no lo sé» a algo que sí
estaba documentado.

**3. `EncryptedTextField` devuelve el valor tal cual si no es un token Fernet
válido.** Pasa con filas escritas antes de que el campo se cifrara y con dumps
restaurados de otro entorno. Es deliberado y estaba sin probar: si lanzara, una
sola fila heredada tumbaría cualquier consulta que la incluyera —incluido el
listado de muestras— y el laboratorio se quedaría sin poder trabajar por un dato
viejo.

#### Cuatro suposiciones más que la primera pasada refutó

Mismo patrón que en §2 con los duplicados y en el contrato de errores:

| Lo que yo suponía | Lo que el sistema hace |
|---|---|
| «¿qué es un naranja?» va por el camino documental | «naranja» dispara el atajo por palabra clave; el que lo evita es «qué significa…», que `_es_atajo_inseguro` reconoce como petición de explicación |
| Un corpus de prueba con secciones cortas produce fragmentos | `MIN_CHARS = 120`: devolvía cero y parecía que la carga fallaba |
| El payload de un evento se puede reescribir con `save()` | RN-05 lo bloquea en el modelo; hay que usar `.update()`, que es justo el agujero |
| El registro llega al servicio con una imagen | El serializer exige **tres** metáfases: con menos no se toca la base ni se cifra la PII |

Ninguna se resolvió quitando el assert. Las cuatro están escritas como pruebas
con su motivo.

---

## 5 · Esquema del endpoint principal

**`GET /api/clinic/samples/{id}/karyotype/`** — devuelve el producto: el
cariotipo propuesto con su semaforización. De él dependen el visor, el panel del
supervisor y la decisión de si el caso puede emitir informe.

Vive en `backend-clinic/apps/samples/contratos.py`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "GET /api/clinic/samples/{id}/karyotype/",
  "type": "object",
  "required": ["id", "sample_id", "sample_status", "model_version",
               "generated_at", "summary", "chromosomes"],
  "properties": {
    "id":            {"type": "string", "format": "uuid"},
    "sample_id":     {"type": "string", "format": "uuid"},
    "sample_status": {"type": "string",
                      "enum": ["DRAFT","PENDING_AI","PROCESSING","READY",
                               "ANALYST_VALIDATED","VALIDATED","SIGNED",
                               "REPORTED","REJECTED"]},
    "sample_iscn":   {"type": "string"},
    "model_version": {"type": "string"},
    "generated_at":  {"type": ["string", "null"]},
    "summary": {
      "type": "object",
      "required": ["total","green","orange","red","unresolved_orange","is_blocked"],
      "additionalProperties": false,
      "properties": {
        "total":             {"type": "integer", "minimum": 0},
        "green":             {"type": "integer", "minimum": 0},
        "orange":            {"type": "integer", "minimum": 0},
        "red":               {"type": "integer", "minimum": 0},
        "unresolved_orange": {"type": "integer", "minimum": 0},
        "is_blocked":        {"type": "boolean"}
      }
    },
    "chromosomes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id","predicted_class","position_index","confidence_score",
                     "semaphore","resolution_status","xai_viewed","is_anomaly",
                     "is_active","order"],
        "properties": {
          "id":                {"type": "string", "format": "uuid"},
          "predicted_class":   {"type": "string",
                                "enum": ["1","2","3","4","5","6","7","8","9","10",
                                         "11","12","13","14","15","16","17","18",
                                         "19","20","21","22","X","Y"]},
          "position_index":    {"type": "integer", "minimum": 0},
          "confidence_score":  {"type": ["string","number","null"],
                                "pattern": "^\\d\\.\\d{1,3}$"},
          "semaphore":         {"type": "string", "enum": ["green","orange","red"]},
          "resolution_status": {"type": "string",
                                "enum": ["AUTO","PENDING","RESOLVED"]},
          "xai_viewed":        {"type": "boolean"},
          "is_anomaly":        {"type": "boolean"},
          "is_active":         {"type": "boolean"},
          "measures":          {"type": ["object","null"]},
          "bbox":              {"type": ["object","null"]},
          "order":             {"type": "integer", "minimum": 0}
        }
      }
    }
  }
}
```

### Códigos HTTP del contrato

| Código | Cuándo |
|---|---|
| `200` | el dueño del caso, o supervisor/admin |
| `401` | sin JWT |
| `403` | analista que no es dueño del caso (**RN-06**) |
| `404` | la muestra no existe, o no tiene cariotipo todavía |

Hay un test que barre los cuatro escenarios y falla si aparece **cualquier otro
código**.

### Dos decisiones del esquema que no son obvias

**`is_blocked` es booleano estricto.** RN-02 decide con este campo si el caso
puede emitir informe. En JavaScript la cadena `"false"` es verdadera: si el
backend lo mandara como texto, el visor dejaría emitir un caso bloqueado.

**Los catálogos son cerrados.** Un `semaphore` fuera de los tres valores no es un
dato raro: es un fallo. El visor pinta el color a partir de ese campo y no sabría
qué hacer con otra cosa.

---

## 6 · Corrida final en verde, sin modelo ni red

```bash
CLINIC_LLM_ENABLED=false CLINIC_LLM_URL=http://127.0.0.1:1/v1 \
  .venv/Scripts/python -m pytest -p no:randomly --cov=. --cov-fail-under=0
```

```
TOTAL                                    8783   1086    88%
863 passed, 2 warnings in 603.29s (0:10:03)
```

**El modelo apagado no basta como prueba.** Por eso la URL apunta a
`127.0.0.1:1`, un puerto muerto: si algún test intentara la red de verdad,
fallaría con «connection refused» en vez de pasar por casualidad porque Ollama
estaba encendido en la máquina.

Los 863 pasan en 10 min 3 s sin tocar la red. Los 236 tests añadidos no la tocan
tampoco: doblan `httpx` y `openai` en la frontera y usan `tmp_path` para el
disco. El único que lanza un proceso —la sesión MCP— tiene el doble puesto en el
SDK, no en el sistema operativo.

El detector de duplicados, corrido de nuevo sobre las **968 pruebas con assert**
del repositorio completo, devuelve **0 grupos con huella repetida**: los 236
tests nuevos no introdujeron ninguno.

La batería de contrato es donde más fácil habría sido introducirlos —doce
endpoints con las mismas dos guardas—, y es justo por eso que se escribió
parametrizada: la tabla es una fila por endpoint, no un bloque copiado.

---

## 7 · Lo que queda declarado

**El código de producción del clínico ya cumple RN-09**: 91,74 %, por encima del
90 % exigido. La cifra que reporta `pytest-cov` en bruto sigue por debajo
(86,00 %) porque mezcla los ficheros de test y los `management/commands`; se
explica en §1 y no se disimula.

**Lo que queda sin cubrir son 103 sentencias, y casi la mitad no son código
vivo:**

| Módulo | Cobertura | Sentencias sin cubrir |
|---|---:|---:|
| `migrations/` (4 ficheros de seed) | 68-73 % | 45 |
| `views.py` | 94,4 % | 24 |
| `agente_grafo.py` | 93,3 % | 7 |
| `agente.py` | 92,8 % | 6 |
| `services.py` | 99,0 % | 5 |
| `iscn.py` | 96,2 % | 4 |

Descontadas las migraciones de seed —código que se ejecutó una vez al aplicar la
migración y no se vuelve a ejecutar—, **el código vivo del clínico está al
97,76 %**.

Lo que queda en `views.py` es sobre todo la rama `mcp: true` del agente y el
turno con memoria conversacional: las dos levantan un proceso aparte (el
servidor MCP, el grafo de LangGraph). **Eso es integración de proceso, no
unit**, y forzarlo con dobles probaría el doble en vez del sistema. Es el
siguiente paso natural, en la capa E2E que este módulo todavía no tiene.

**Hay un test intermitente sin diagnosticar**: `sampleListPage · filtro por
status VALIDATED`, en `frontend-clinic`. Pasa aislado y ha pasado en las últimas
cuatro ejecuciones completas, así que no se contabiliza como fallo — pero está
sin explicar.

**Esta actividad midió `backend-clinic`.** El sistema tiene cinco módulos y 1.616
tests en total; los otros cuatro quedan para las siguientes iteraciones.
