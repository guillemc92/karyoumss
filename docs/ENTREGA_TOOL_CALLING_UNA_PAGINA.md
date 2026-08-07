# Tool calling — resumen de una página

**BIOMED UMSS · Plataforma de Cariotipado Inteligente** — Ing. Guillermo Mamani Chambi (individual)
Repositorio: `https://github.com/guillemc92/karyoumss` · Rama: **`feature/clinic-django-stack`**

---

## Herramientas publicadas

| Herramienta | Responde | Fuente (tabla) |
|---|---|---|
| `CROMOSOMAS_PARA_REVISION` | Cromosomas naranjas: confianza < 85% sin resolver | `clinic_chromosomes` |
| `CASOS_PENDIENTES_FIRMA` | Casos validados esperando la firma del Supervisor | `clinic_samples` |
| `CASOS_REPORTADOS` | Casos cerrados con nomenclatura ISCN emitida | `clinic_samples` |
| `CASOS_EN_PROCESO` | Muestras que el pipeline de IA todavía procesa | `clinic_samples` |

Cada respuesta declara en pantalla `camino`, `tool` y `source`. Sin procedencia, un
usuario no puede distinguir un dato consultado de uno inventado.

## Modelo y versión

| | |
|---|---|
| Modelo | **`llama3.2:3b`** — versión fija en el `.env`, **nunca `latest`** |
| Proveedor | Ollama local, `http://localhost:11434/v1` (SDK de OpenAI) |
| Parámetros | `temperature=0.0` (enrutar es determinista), `max_tokens=200`, `response_format` con enum de nombres válidos |
| Interruptor | `CLINIC_LLM_ENABLED` en `backend-clinic/.env` |

La versión se fija porque `latest` cambia el modelo bajo los pies: el enrutamiento
dejaría de ser reproducible y los cuatro escenarios no serían verificables dos veces.

## Qué no funcionó

**El modelo elegía una herramienta en 4 de cada 6 preguntas fuera de alcance.**
Es el fallo más grave que apareció, y los cuatro escenarios no lo detectaban: la
pregunta del escenario 3 resultó ser una de las dos que sí acertaba. Se encontró
midiendo con un banco de 30 preguntas etiquetadas (`manage.py eval_enrutado`),
no ejecutando la demo.

| | Antes | Después |
|---|---|---|
| Fuera de alcance | 2/6 — **33%** | 6/6 — **100%** |
| Dentro de alcance | 22/24 — 92% | 21/24 — 88% |
| Global | 24/30 — 80% | 27/30 — **90%** |

La causa: la regla de abstención era una línea suelta, sin ejemplos, y las
descripciones solo decían para qué sirve cada herramienta, nunca para qué **no**.
El modelo enrutaba por parecido temático — «¿quién es el jefe del servicio?» iba
a `CASOS_PENDIENTES_FIRMA`. Se corrigió enumerando lo que ninguna herramienta
cubre e invirtiendo la prioridad: elegir mal es peor que abstenerse. **El peaje
costó una pregunta válida** (92% → 88%): el intercambio compensa porque los dos
errores no cuestan lo mismo, pero es real y no se esconde.

**La latencia del camino LLM es inaceptable para uso interactivo: ~94 segundos**,
contra 7–34 ms del camino KEYWORD — tres órdenes de magnitud. Es el costo de un
modelo de 3B en CPU sin GPU. La arquitectura de dos caminos existe justamente por
esto: las preguntas frecuentes se resuelven con vocabulario y el modelo queda como
red de seguridad para las que no.

**El modelo devuelve nombres que no están en el enum**, pese a declarar
`strict: true` en el esquema. El enrutador verifica el nombre contra el catálogo
antes de ejecutar, en vez de confiar en que el contrato se respetó. Está cubierto
por un test.

**La degradación es tan limpia que esconde errores de configuración.** Al correr la
demo con un intérprete sin el SDK de `openai` instalado, el escenario 2 devolvió
`SIN_MATCH` con aspecto de comportamiento correcto; el único indicio era una línea
de log. Un fallo de disponibilidad y una pregunta fuera de alcance se ven casi
igual desde la pantalla. Convendría distinguirlos en la respuesta.

**La consola de Windows (cp1252) rompe con Unicode** — flechas, comillas angulares,
guiones largos. La primera corrida falló con `UnicodeEncodeError`; se resolvió
usando solo ASCII en la salida del comando.

**Los cromosomas naranjas del seed original ya estaban resueltos**, así que la
herramienta principal devolvía cero filas y la demo no probaba nada. Hubo que
sembrar un caso específico (`seed_demo_tools`).

## Lo que aporta el modelo, medido

Con `CLINIC_LLM_ENABLED=false`, el escenario 1 responde idéntico (7 ms) y el
escenario 2 —el sinónimo— cae en «no sé». Esa diferencia, y solo esa, es la
contribución del modelo: **tolerancia a la paráfrasis, sin tocar los datos**.
