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

| Alcance | Antes | Después | Δ |
|---|---:|---:|---:|
| Lo que reporta `pytest-cov` | 82,25 % | 84,04 % | +1,79 pp |
| Sin ficheros de test | 65,41 % | — | — |
| **Código de producción** (sin tests ni CLI) | **85,63 %** | **88,60 %** | **+2,97 pp** |

```
antes    46 ficheros · 2.798 sentencias · 2.396 cubiertas
después  47 ficheros · 2.806 sentencias · 2.486 cubiertas
tests    627  →  663   (+36)
```

Reproducible con:

```bash
cd backend-clinic
.venv/Scripts/python -m pytest --cov=apps --cov-report=json:cov.json
python docs/../scripts/huecos_produccion.py cov.json
```

### Los huecos que la medición encontró

| Módulo | Cobertura antes | Sentencias sin cubrir |
|---|---:|---:|
| **`rag_qa.py`** | **0,0 %** | **62** |
| `rag_index.py` | 37,8 % | 51 |
| `agente_acciones.py` | 40,7 % | 16 |
| `admin_client.py` | 52,9 % | 16 |
| `pipeline_client.py` | 67,5 % | 25 |

`rag_qa.py` es el que decide **si el sistema responde una pregunta clínica o
dice que no sabe**, y no tenía ni una prueba. Es el hueco que se atacó primero.

Los cinco están en la **frontera** —modelo, disco y red—, que es exactamente
donde la consigna pide dobles.

---

## 2 · Duplicados

### Cómo se buscaron

La consigna define duplicado como *misma función bajo prueba, mismos datos de
entrada y mismo assert, **aunque el nombre cambie***. Comparar texto no vale, así
que se compara una huella del **AST** de cada test: llamadas, literales, asserts
normalizados, fixtures y decoradores.

Se analizaron **820 tests con assert** de los tres backends.

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
| **Total** | **36** | **36** | — | |

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
  .venv/Scripts/python -m pytest --cov=apps
```

```
TOTAL                                    7555   1206    84%
663 passed, 2 warnings in 471.71s (0:07:51)
```

**El modelo apagado no basta como prueba.** Por eso la URL apunta a
`127.0.0.1:1`, un puerto muerto: si algún test intentara la red de verdad,
fallaría con «connection refused» en vez de pasar por casualidad porque Ollama
estaba encendido en la máquina.

Los 663 pasan en 7 min 51 s sin tocar la red.

---

## 7 · Lo que queda declarado

**La cobertura sigue por debajo del 90 % que exige RN-09** (84,04 % en el
informe, 88,60 % en producción). Es deuda anterior a esta actividad y no se
disimula. Los siguientes huecos ya están identificados: `rag_index.py` 37,8 %,
`agente_acciones.py` 40,7 %, `admin_client.py` 52,9 %.

**Hay un test intermitente sin diagnosticar**: `sampleListPage · filtro por
status VALIDATED`, en `frontend-clinic`. Pasa aislado y ha pasado en las últimas
cuatro ejecuciones completas, así que no se contabiliza como fallo — pero está
sin explicar.

**Esta actividad midió `backend-clinic`.** El sistema tiene cinco módulos y 1.616
tests en total; los otros cuatro quedan para las siguientes iteraciones.
