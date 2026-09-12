# Demo en vivo — de la metafase al informe

> Guion para tener en pantalla. Todo lo que aparece aquí está **verificado
> ejecutándolo**, no leído del código. Los números son los que van a salir.

---

## 0 · Antes de empezar (3 min)

### Los CINCO procesos — no cuatro

Las dos SPA tienen que servirse desde el **mismo origen** o no comparten el
`localStorage` donde vive el token (ADR-0020, DD-SSO-001 §4.1). Por eso hace
falta Caddy.

```bash
# 1 · motor de inferencia
cd backend-ml      && python -m uvicorn app.main:app --port 8000

# 2 · autoridad de JWT
cd backend-admin   && .venv/Scripts/python manage.py runserver 127.0.0.1:8001 --noreload

# 3 · backend clinico
cd backend-clinic  && CLINIC_LLM_ENABLED=true .venv/Scripts/python manage.py runserver 127.0.0.1:8002 --noreload

# 4 · SPA de administracion
cd frontend-admin  && npm run dev                       # :5173

# 5 · SPA clinica  (OJO: MSYS_NO_PATHCONV en Git Bash)
cd frontend-clinic && MSYS_NO_PATHCONV=1 VITE_BASE_PATH=/clinic/ npm run dev   # :5174

# 6 · el proxy que las une en un solo origen
caddy run --config Caddyfile.dev                        # :3000
```

> **`MSYS_NO_PATHCONV=1` no es opcional en Git Bash.** Sin él, `/clinic/` se
> convierte en una ruta de Windows y la app queda servida en
> `/Program%20Files/Git/clinic/`.

### La URL — y la que NO hay que usar

| | |
|---|---|
| ✅ **`http://localhost:3000`** | login, y de ahí todo |
| ❌ `http://localhost:5174` | **la lista sale VACIA**: otro origen, sin token |

Si durante la demo escribes `:5174` por costumbre, verás cero muestras y
parecerá que el sistema falla. **Deja una sola pestaña abierta, en `:3000`.**

### Credenciales — el campo es el EMAIL

```
analista    demo.analista@biomed.umss.bo   Demo2026!
supervisor  demo_supervisor@umss.bo        Demo2026!
```

Tras el login te lleva solo a `/clinic/samples` con **15 muestras** en todos
los estados. Para el ISCN de `CHN-DEMO-T21`, entra como **supervisor**: ese
panel solo se le muestra a él.

### Comprobacion rapida

```bash
curl http://127.0.0.1:8000/health/        # debe decir "trained_model":true
curl -o /dev/null -w "%{http_code}
" http://localhost:3000/clinic/samples   # 200
```

---

## 1 · Registrar y analizar con IA  *(en vivo, ~32 s)*

`/clinic/samples/register`

Rellenar CHN con formato **`CHN-AAAA-MM-DD-NNNN`** (lo valida), tipo de muestra
`Sangre`, y **subir 3 metafases** de `datasets/metaclass/metafases/`.

> ⏱ **Avisar antes de pulsar: tarda unos 32 segundos.** Si no lo dices, el
> silencio se hace muy largo.

**Qué decir mientras corre:**

> «No hay simulación aquí. Guarda la muestra, cifra los datos del paciente en
> una bóveda aparte, y llama a un servicio de inferencia propio que segmenta
> con OpenCV y clasifica con un EfficientNet-B3 que entrené con 48.000
> recortes del laboratorio.»

**Si el motor estuviera caído**, la muestra se guarda igual en `PENDING_AI` con
un aviso de modo degradado. Eso es RN-07: degradar, no romper.

*Alternativa sin riesgo:* ya existe `CHN-2026-08-19-2414` registrado así.

---

## 2 · El visor — aquí está el mensaje  *(3 min)*

Abrir el cariotipo de la muestra recién creada.

```
47 cromosomas detectados
42 naranjas · 5 verdes
confianza media 0.542 — solo 5 superan el umbral de 0.85
```

**Esto no es un fallo de la demo: es el mensaje.**

> «El umbral de 0.85 no es decorativo: bloquea la emisión del informe. La IA
> propone, el analista decide. Un cariotipo con 42 dudas no sale de aquí.»

Enseñar el banner de bloqueo y la leyenda del semáforo.

---

## 2.bis · El caso real del archivo — la comparación que más pesa  *(3 min)*

Tres casos del archivo del laboratorio están cargados, procesados por la IA. Lo
que los hace valiosos es que **existe el cariograma que un citogenetista produjo
a mano para esa misma metafase**.

```bash
manage.py seed_casos_reales     # ya ejecutado; recarga si hiciera falta
```

| Caso | Lo que dijo el EXPERTO | Lo que propone la IA |
|---|---|---|
| `CHN-2026-08-20-R018` | **47,XX,+21** — trisomía 21, síndrome de Down | 44 cromosomas, 42 naranjas |
| `CHN-2026-08-20-R131` | 46,XY — varón normal | 53 cromosomas, 49 naranjas |
| `CHN-2026-08-20-R123` | 46,XX — mujer normal | 42 cromosomas, 39 naranjas |

**Enseña el R018.** Abre el visor con el caso, y al lado el cariograma del
experto:

```
datasets/metaclass/cariogramas/cario_18.bmp
```

En ese cariograma **se ve la trisomía a simple vista**: tres cromosomas en el
par 21 en vez de dos.

**Qué decir:**

> «A la izquierda, lo que propone mi sistema. A la derecha, lo que un
> citogenetista de este laboratorio produjo a mano para esta misma metafase, y
> que está en su archivo. No estoy midiéndome contra un dataset público:
> **me mido contra el trabajo real de la persona a la que quiero ayudar**.
>
> Y como ven, hoy no le ayudo: propone 44 cromosomas donde hay 47, y no
> encuentra la trisomía. Por eso el sistema la bloquea en vez de emitirla.»

Es el momento más honesto de la demo y el que mejor explica las 64 acciones.

---

## 3 · Corregir UNO, con trazabilidad  *(4 min)*

Seleccionar un cromosoma naranja:

1. **Ver explicabilidad (XAI)** — obligatorio antes de aceptar (BR-004). El
   botón de aceptar está deshabilitado hasta que se consulta.
2. **Recortar y reclasificar** — dibujar el rectángulo sobre el lienzo. Al
   soltar, el servidor vuelve a clasificar con el recorte nuevo y el cromosoma
   **vuelve a estar pendiente**: la decisión anterior se tomó sobre otros
   píxeles.
3. **Bitácora de auditoría** — abrirla. Cada acción encadenada con SHA-256.

> «Ninguna de estas acciones se puede borrar. La cadena de hash es lo que
> sostiene la firma electrónica.»

---

## 4 · El puente honesto  *(el momento delicado — 1 min)*

**Decirlo tal cual, sin rodeos:**

> «Corregir este caso entero son 64 acciones. Lo medí: contra el cariograma del
> experto, sobre 20 casos, la mediana es 64 y hacerlo a mano son 46. Hoy mi
> pipeline añade trabajo en vez de ahorrarlo, y sé por qué: la segmentación
> junta cromosomas que se tocan. Paso a un caso ya corregido para no hacerles
> ver las 64.»

Eso **suma**, no resta: es una métrica de producto medida, con causa
identificada y hoja de ruta.

---

## 5 · Del caso validado al informe  *(4 min)*

Abrir **`CHN-DEMO-T21`** (`REPORTED`).

| Paso | Qué enseñar |
|---|---|
| Validación del analista | RN-01: no avanza con naranjas sin resolver |
| Auditoría del 5% | RN-08, y el supervisor **no puede ser** el analista (RN-06) |
| Firma con MFA | 21 CFR Part 11 |
| **ISCN** | **`47,XY,+21`** — generado por una función determinista, no por el modelo |
| Narrativa | redactada por `llama3.2:3b` **local** |

> «El ISCN lo calcula código. El modelo solo lo pone en prosa. Si el LLM
> alucina, la nomenclatura no cambia.»

Y el remate, enseñando el informe real del laboratorio:

> «Este es el informe que emite hoy el laboratorio para un caso de trisomía 21:
> `47,XY,+21[20]`. Mi sistema produce `47,XY,+21`. Lo que falta es el `[20]` —
> el número de metafases que sostienen el diagnóstico— y sé exactamente qué
> hace falta para tenerlo.»

---

## 5.bis · Cierre — dónde va el nivel 5, y dónde no  *(60 s)*

> **Cuándo:** solo al final, después del informe. Si vas justo de tiempo,
> sáltalo: no lo ha pedido.
>
> **Cómo NO decirlo:** «también implementé el nivel 5». Eso invita a que lo
> evalúe contra el Día 7 entero —checkpoints, reanudar, HITL persistente,
> fallbacks, Langfuse— y cuente 1 de 5.
>
> **Cómo sí:** como una decisión ya tomada, no como una funcionalidad de más.

**Leerlo casi literal:**

> «Sé que la orquestación es el siguiente paso. Ya tengo decidido dónde va
> LangGraph y dónde no, y está firmado en el ADR-0032.
>
> **Va** en la memoria conversacional del agente: hoy la lista de mensajes
> muere con la petición, así que una repregunta —"¿y de esos cuál mencionaste
> primero?"— llega sin referente.
>
> **No va** en el estado clínico. Un caso avanza en PostgreSQL con un audit
> trail encadenado por SHA-256, que es lo que sostiene la firma electrónica bajo
> 21 CFR Part 11. Meter eso en checkpoints crearía una segunda fuente de verdad
> para un proceso auditado: cuando alguien pregunte en qué estado estaba un
> caso, no puede haber dos respuestas. Es una objeción de cumplimiento, no de
> complejidad.
>
> Lo implementé y lo medí: **gana 4 de 8 repreguntas, contra 0 de 8 sin
> memoria**. El checkpoint persiste siempre —está probado—; lo que falla es que
> un modelo de 3B lo aproveche: vuelve a consultar las herramientas en vez de
> leer el historial. El límite es el modelo, no la arquitectura.»

**El remate, si hay ambiente para uno más:**

> «Y por eso tampoco uso el `interrupt` de LangGraph, aunque "aprobar desde otra
> sesión" sea literalmente mi RN-06: como la herramienta nunca escribe, aprobar
> algo que de todos modos no se ejecuta sería teatro con aspecto de guardrail.»

**Ten abierto en una pestaña:** `docs/adr/0032-memoria-conversacional-langgraph.md`

**No lo demuestres en vivo.** `eval_memoria` tarda casi dos horas y no hay nada
visual: es una tabla. Con la del informe basta.

---

## 6 · Si preguntan

**«¿Por qué solo analiza una metafase si pide tres?»**
Porque `Karyotype` es `OneToOne` con `Sample`: no hay dónde guardar 20
cariotipos ni el paso de consenso. Está identificado, es un cambio de modelo, y
es justo lo que separa esto de un informe clínico emitible.

**«¿Esto ya sirve en el laboratorio?»**
No todavía, y lo tengo medido: 64 acciones de corrección frente a 46 a mano. El
cuello de botella no es el clasificador —son 4 de esas 64 acciones—, es que el
detector junta cromosomas. Ese es el siguiente hito.

**«¿Por qué no hiciste el resto del Día 7 —fallbacks, caché semántica,
Langfuse?»**
Porque no se pidió y porque son infraestructura, no capacidad del agente. Lo que
sí faltaba —que la memoria muriese con el proceso— es lo que ADR-0030 dejó
anotado como carencia, y es lo único del Día 7 que resolví.

**«¿Con qué se compara esto? ¿Existe algo así ya?»**
Sí, y conviene distinguir dos cosas que suenan parecido:

> «Reemplazo **MetaClass**, que es lo que el laboratorio usa hoy. Tengo su
> esquema de base de datos —SQL Server, `SCAMC`, 48 tablas— y de ahí saqué las
> 1.113 imágenes con las que entrené el clasificador: **el sistema aprende del
> archivo real del sistema al que sustituye**.
>
> Y me comparo con **Ikaros 7 de MetaSystems**, que es el producto de referencia
> del sector. No para competir con él —es maduro y certificado, y lo mío es un
> prototipo cuyo coste de corrección salió desfavorable—, sino para comprobar si
> mis decisiones apuntan en la misma dirección. Tres que confirma: llama
> *proposal* a su salida, cuenta células analizadas, y expone un control manual
> del umbral de segmentación.»

Si sacas la captura de Ikaros, **di explícitamente que no es vuestro sistema**.
Dejarlo ambiguo invita a que te pregunten por qué construiste algo que ya
tenéis.

**«¿Es U-Net?»**
No. Es OpenCV con watershed. La cadena de versión lo declara sin ambigüedad:
`opencv-watershed-v0+efficientnet-b3-metaclass-v3`. U-Net es el diseño; está
distinguido de lo construido en el DTI §9.1.

**«¿Los datos del paciente salen a la nube?»**
No. El modelo corre en local con Ollama, no hay clave de API, y los datos
identificables viven cifrados en una bóveda separada del caso clínico.

---

## 7 · Lo que NO hay que abrir

- **`CHN-2026-08-06-2574`** — llegó a `REPORTED` con un ISCN de 50 anomalías y
  36 cromosomas. Ya está desactivado, pero no lo busques.
- La lista completa de reportados solo debe mostrar `CHN-DEMO-T21`.
