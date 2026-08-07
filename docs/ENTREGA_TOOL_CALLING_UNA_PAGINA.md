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

| Banco de 30 | Inicial | Prompt endurecido | Descripciones equilibradas |
|---|---|---|---|
| Fuera de alcance | 2/6 — **33%** | 6/6 — 100% | 6/6 — 100% |
| Dentro de alcance | 22/24 — 92% | 21/24 — 88% | 23/24 — 96% |
| Global | 24/30 — 80% | 27/30 — 90% | 29/30 — **97%** |

**Ese 97% no era real.** Las 6 preguntas fuera de alcance del banco pequeño no
compartían ni una palabra con el catálogo, así que abstenerse era fácil. Con 56
preguntas —18 fuera de alcance, 6 de ellas escritas con el vocabulario del propio
dominio— el resultado cayó a **45/56 (80%), con la abstención en 11/18 (61%)**.
Las preguntas sobre los conceptos que las herramientas manipulan («¿quién tiene
permiso para firmar?», «¿qué umbral deberíamos usar?») acaban en la herramienta
dueña del concepto.

**Causa 1:** la regla de abstención era una línea suelta, sin ejemplos. El modelo
enrutaba por parecido temático — «¿quién es el jefe del servicio?» iba a
`CASOS_PENDIENTES_FIRMA`. Se corrigió enumerando lo que ninguna herramienta cubre
e invirtiendo la prioridad: elegir mal es peor que abstenerse. Costó una pregunta
válida (92% → 88%), un intercambio real que no se esconde.

**Causa 2:** tras eso, los 3 fallos restantes caían todos en la misma
herramienta. No porque las otras estuvieran mal definidas, sino porque esa
descripción estaba **mejor escrita** que las demás: cuatro líneas frente a dos.
El modelo se iba a la que mejor entendía. Se equilibraron las cuatro, cada una
declarando su etapa del flujo y su frontera, con el vocabulario real de los
usuarios («máquina», «corriendo», «trabajando») que no aparecía en ninguna.
Eso recuperó el terreno perdido y lo superó: **96% dentro de alcance sin perder
el 100% de abstención**.

El único fallo restante es de etiqueta discutible («¿qué está listo para la
última revisión?» admite dos lecturas) y se deja en el banco a propósito.

**El camino rápido tiene dos puntos ciegos estructurales.** La coincidencia
literal no sabe abstenerse —«¿qué significa que un cromosoma esté naranja?»
contiene «naranja» y devolvía la lista a una pregunta de documentación— ni ve la
negación: «¿validados pero NO cerrados?» disparaba con «cerrados» y devolvía lo
contrario. Ninguna llegaba al modelo. Corregido haciendo que el atajo ceda al
modelo ante preguntas explicativas o negadas.

**La respuesta truncaba en silencio:** mostraba 50 de 100 cromosomas naranjas
diciendo «50 resultado(s)». La respuesta significa «estos son los cromosomas que
hay que revisar»: un analista creería haber visto toda su cola faltándole la
mitad. Corregido con un aviso explícito y tres tests. Apareció por consultar
datos reales en vez de sembrados.

**Limitación metodológica declarada:** el número final sale de tres iteraciones
de ajuste contra el mismo banco. Los arreglos atacan clases de fallo, no ejemplos
concretos, pero la medida ya está contaminada. La prueba honesta sería un
conjunto nuevo escrito sin mirar los fallos; queda pendiente.

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
