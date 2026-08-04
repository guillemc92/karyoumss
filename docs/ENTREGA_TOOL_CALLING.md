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

## 6. Endpoint

```
POST /api/clinic/tools/query/   {"pregunta": "..."}
GET  /api/clinic/tools/query/   → publica el catálogo
```

**Siempre responde 200.** Una pregunta fuera de alcance no es un error del
cliente: devuelve `camino: SIN_MATCH` con el catálogo de lo que sí se puede
consultar.

---

## 7. Qué no funcionó

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

## 8. Archivos

| Archivo | Rol |
|---|---|
| `backend-clinic/apps/samples/tools.py` | Catálogo + las consultas (Django ORM) |
| `backend-clinic/apps/samples/tool_router.py` | Enrutador: KEYWORD / LLM / SIN_MATCH |
| `backend-clinic/apps/samples/views.py` → `ToolQueryView` | Endpoint |
| `backend-clinic/apps/samples/management/commands/demo_tools.py` | Los cuatro escenarios |
| `backend-clinic/apps/samples/management/commands/seed_demo_tools.py` | Datos para la demo |
| `backend-clinic/apps/samples/tests/test_tool_router.py` | 31 tests |

**Tests:** 31, sin necesidad de Ollama corriendo (el modelo se sustituye por
dobles). El más importante verifica que **el escenario 1 y el 2 devuelvan
exactamente los mismos datos** — si difirieran, significaría que el modelo influyó
en la respuesta.

```bash
.venv/Scripts/python -m pytest apps/samples/tests/test_tool_router.py -v --no-cov
```
