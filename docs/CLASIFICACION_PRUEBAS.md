# Mapa de pruebas del producto

## ¿Es determinista o probabilística? · ¿Con qué capa se prueba? · ¿Qué herramienta?

| | |
|---|---|
| **Equipo** | **BIOMED UMSS** |
| **Integrantes** | Ing. Guillermo Mamani Chambi (individual, G04) |
| Producto | Plataforma de Cariotipado Asistido por IA |
| Repositorio | `karyoumss` — rama `feature/clinic-django-stack` |
| Fecha | 4 de septiembre de 2026 |
| Unit tests hoy | **1.616**, todos en verde |

---

## 1 · La respuesta a la trampa, antes de la tabla

Este producto tiene **dos** capas de IA —un clasificador de imágenes y un modelo
de lenguaje— y aun así **el 100 % de sus 1.616 pruebas unitarias son
deterministas**. Ninguna llama a un modelo.

No es un descuido: la frontera se dibujó en la arquitectura antes que en el
test, y está escrita en la cabecera de las pruebas del enrutador:

> *«El LLM se sustituye por dobles: los cuatro escenarios se verifican sin
> Ollama.»*

La frontera **no** separa «lo que tiene IA» de «lo que no». Separa **lo que se
puede afirmar con un `assert`** de **lo que solo se puede medir con un número
sobre un conjunto**. Login, CRUD, permisos, validaciones, nomenclatura ISCN,
cadena de auditoría, semáforo y reparto de cromosomas caen todos del lado del
`assert`.

---

## 2 · Mapa parte por parte

### 2.1 · Partes DETERMINISTAS

| Parte del producto | Clasificación | Capa de la pirámide | Herramienta |
|---|---|---|---|
| Login y emisión de JWT | Determinista | Integración (API + BD) | `pytest` + `pytest-django` |
| Renovación automática de sesión SSO | Determinista | Unitaria | `vitest` |
| Permisos por rol y RBAC jerárquico | Determinista | Integración (BD) | `pytest` |
| CRUD de muestras | Determinista | Integración (API + BD) | `pytest` + cliente HTTP |
| Registro de muestra: formato CHN, mínimo de imágenes | Determinista | Integración (API + BD) | `pytest` |
| Guardrail de tamaño de imagen (rechaza recortes) | Determinista | Unitaria | `pytest` |
| **Motor ISCN** — función pura | Determinista | Unitaria | `pytest` |
| **Cadena de auditoría SHA-256** | Determinista | Unitaria + Integración | `pytest` |
| **Semáforo RN-02** (confianza < 0,85 → naranja) | Determinista | Unitaria | `pytest` |
| **Reparto del cariotipo** (asignación húngara) | Determinista | Unitaria | `pytest` |
| Geometría del recorte y del viewport | Determinista | Unitaria | `vitest` |
| Componentes de interfaz | Determinista | Unitaria | `vitest` + Testing Library |
| Páginas y flujos de interfaz | Determinista | Integración | `vitest` + **MSW** |
| Enrutador de consultas — camino KEYWORD | Determinista | Unitaria | `pytest` |
| Enrutador de consultas — camino LLM | Determinista | Unitaria | `pytest` + **doble del modelo** |
| Guardrails del agente (tope de pasos, escritura que no ejecuta) | Determinista | Unitaria | `pytest` + doble |
| Clasificador: **reproducibilidad** (misma imagen → misma clase) | Determinista | Unitaria | `pytest` |

### 2.2 · Partes PROBABILÍSTICAS

| Parte del producto | Clasificación | Capa de la pirámide | Herramienta |
|---|---|---|---|
| Acierto del clasificador de cromosomas | Probabilística | Evals | `eval_dos_caminos` · macro-F1 sobre partición de validación |
| ¿El umbral de 0,85 separa aciertos de errores? | Probabilística | Evals | `eval_umbral_semaforo` |
| Ganancia del reparto global | Probabilística | Evals | `eval_asignacion` (banco de ajuste + banco nuevo) |
| Elección de herramienta del enrutador | Probabilística | Evals | `eval_enrutado` · banco de 56 preguntas etiquetadas |
| RAG: que cite la fuente y que sepa abstenerse | Probabilística | Evals | `eval_rag --con-juez` · **candidata: RAGAS** |
| Memoria conversacional del agente | Probabilística | Evals | `eval_memoria` |
| Narrativa clínica redactada por el LLM | Probabilística | Evals | **pendiente — candidata: DeepEval** |
| Coste de corrección frente a hacerlo a mano | Probabilística | Evals de producto | `eval_correccion` · 20 casos vs. cariograma del experto |

### 2.3 · Lo que NO existe todavía

| Parte del producto | Clasificación | Capa | Herramienta |
|---|---|---|---|
| Flujo completo en navegador (registrar → procesar → validar → firmar) | Determinista | **E2E** | **Playwright — no implementado** |

Los recorridos completos se han verificado **a mano** con un navegador real.
Sirve para comprobar una vez; no detecta la regresión de mañana. Es el hueco
declarado de este mapa.

---

## 3 · Por qué cada clasificación, en una línea

**El motor ISCN es determinista y es la parte más crítica.** Convierte un
conjunto de cromosomas en `47,XY,+21` con una función pura: mismo cariotipo,
misma nomenclatura, siempre. Es **el diagnóstico**, lo que un profesional firma,
y se hizo determinista **a propósito** para poder afirmarlo con un `assert`. El
LLM solo redacta la prosa que lo acompaña, en un campo aparte marcado como
borrador.

**El semáforo es un `if`.** Un umbral no es probabilístico: dada una confianza,
el color no varía.

**El reparto del cariotipo es un algoritmo exacto.** Mismas probabilidades de
entrada, mismo reparto de salida. Es el componente que más «suena a IA» de todo
el sistema y no tiene ni un gramo de azar.

**El camino LLM del enrutador se prueba como determinista** porque el modelo se
sustituye por un doble. Se afirma *qué hace el sistema cuando el modelo devuelve
X*, no *qué devuelve el modelo*. Lo segundo se mide aparte, en `eval_enrutado`.

**El clasificador aparece en las dos tablas, y no es contradicción.** Ver §4.1.

---

## 4 · Los tres matices que evitan la trampa

### 4.1 · El clasificador es determinista *como función*, probabilístico en su *corrección*

Corre con `model.eval()` y `torch.no_grad()`: **la misma imagen produce siempre
la misma clase y la misma confianza**, y eso se afirma con un `assert`.

Lo que **no** se puede afirmar es que esa clase sea la *correcta* para una
imagen arbitraria. Eso es una propiedad estadística del modelo, no del código,
y se mide con macro-F1 sobre una partición de validación **separada por
paciente**.

**Determinismo y corrección son dos preguntas distintas.** Confundirlas es la
otra mitad de la trampa.

### 4.2 · `temperature = 0` reduce la varianza; no la elimina

El enrutador y el agente usan `temperature=0.0` para que la decisión sea
reproducible. Es una mitigación, no una garantía.

Este proyecto tiene evidencia propia y actuó en consecuencia: **el nombre de
herramienta que devuelve el modelo se valida contra el catálogo**, porque
`strict: true` no garantiza que respete el enum. Esa línea de código existe
precisamente porque la salida no es fiable.

### 4.3 · Un fallo determinista es un bug; un número que baja, no siempre

El enrutador cayó de **86 % a 79 %** al integrar el RAG. No era una regresión:
las preguntas de documentación pasaron a resolverse por el corpus —que es lo
correcto— pero el banco las etiquetaba `NINGUNA` y las contaba como fallo.

Se midió con el banco **intacto** en vez de reescribir la vara. Una métrica que
baja porque el sistema cambió a propósito se explica mejor que una que sube
porque se cambió el examen.

---

## 5 · Los dos regímenes, y por qué no son la misma actividad

| | Régimen determinista | Régimen probabilístico |
|---|---|---|
| Qué comprueba | que el código hace lo que dice | qué tan a menudo el modelo acierta |
| Forma | `assert` exacto | métrica sobre conjunto etiquetado |
| Criterio | **verde o rojo** | un número contra una línea base |
| Cuándo corre | en cada cambio | al tocar el modelo o el prompt |
| Duración | segundos a minutos | minutos a horas (`eval_memoria` ≈ 2 h) |
| Volumen | **1.616 pruebas** | **8 evaluadores** |

---

## 6 · La pirámide real de este producto

```
        ( ausente )          E2E
      ─────────────────────────────
       78 ficheros           Integración
      ─────────────────────────────
       52 ficheros           Unitaria
```

| Capa | Ficheros | Herramienta |
|---|---:|---|
| Unitaria (pura, sin E/S) | 13 | `pytest` |
| Unitaria (componente / función) | 39 | `vitest` + Testing Library |
| Integración (BD) | 17 | `pytest-django` |
| Integración (API + BD) | 30 | `pytest` + cliente HTTP |
| Integración (componente + HTTP simulado) | 24 | `vitest` + MSW |
| Integración (página) | 7 | `vitest` + MSW |
| **E2E** | **0** | **Playwright — pendiente** |

**Dicho sin adornos:** hay más integración que unidad (78 contra 52), así que es
más un rombo que una pirámide, y **le falta la punta**.

---

## 7 · Resumen

1. **El sistema usa IA; sus pruebas unitarias no.** Las 1.616 son deterministas
   porque el modelo se sustituye por dobles.
2. **Lo probabilístico se mide aparte**, con 8 instrumentos que devuelven un
   número contra una línea base, no verde o rojo.
3. **El clasificador es determinista como función y probabilístico en su
   corrección.** Son dos preguntas distintas.
4. **El diagnóstico se hizo determinista a propósito**, para poder afirmarlo.
5. **Falta el E2E.** Declarado, no disimulado.
