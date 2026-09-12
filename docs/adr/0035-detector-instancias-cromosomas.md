---
id: ADR-0035
title: Detector de instancias de cromosomas — decisión diferida, con protocolo de evaluación y derogación de AGENTS §11
date: 2026-08-31
status: proposed
related: [ADR-0007, ADR-0026, ADR-0033, ADR-0034]
depends-on: [ADR-0034]
---

# ADR-0035: Detector de instancias de cromosomas

> **Este ADR no elige un modelo todavía, y esa es la decisión.** Explica por qué
> no se puede elegir hoy, qué hace falta para poder hacerlo, y con qué
> protocolo se decidirá. Sigue el mismo patrón que ADR-0007, que difirió la
> extracción del servicio de inferencia con triggers explícitos en vez de
> adelantarla.

## Contexto

### Qué produce hoy la segmentación

OpenCV + watershed, declarado sin ambigüedad en la cadena de versión
(`opencv-watershed-v0+efficientnet-b3-metaclass-v3`). No hay U-Net: es diseño,
no implementación.

Medido sobre 443 cromosomas de 10 metafases de validación
(`eval_asignacion_metafase.py`), lo que entrega ese detector al clasificador:

- confianza media **0,509** frente a **0,746** sobre recortes limpios del experto
- **94 %** de los cromosomas en naranja
- **259 copias biológicamente imposibles** (más de dos por clase) antes de que
  ADR-0033 las redujera a 105

Y el coste que eso impone al analista: **64 acciones** de corrección por caso
frente a **46** de hacerlo a mano, en 20 de 20 casos peor
(`eval_correccion.py`).

El detector es el cuello de botella. Eso está medido, y no se discute aquí.

### Por qué la elección de modelo no se puede hacer hoy

**No hay verdad de terreno para segmentación.** `crops_manifest.csv` es
`file, class, source`, y `source` apunta al **cariograma**, no a la metafase.
Los 48.467 recortes están etiquetados por clase pero no tienen coordenadas en
la imagen original. `labels.csv` tiene `Width`, `Height` e `ISCN`, y ni una sola
caja.

De ahí salen dos imposibilidades, y la segunda pesa más que la primera:

1. **No se puede entrenar** Mask R-CNN, YOLO-seg ni U-Net supervisada sin
   máscaras.
2. **No se puede evaluar ninguno de los tres.** No hay IoU que calcular, no hay
   con qué comparar. Elegir un modelo sin poder medirlo es elegir por fe.

Este proyecto ya tiene una regla derivada de haberse equivocado cinco veces:
*el instrumento falla antes que el sistema medido; el número es lo último en lo
que hay que creer*. Adoptar un detector sin métrica sería contradecirla.

## Decisión

### D1 — La elección de arquitectura queda DIFERIDA

No se adopta Mask R-CNN, ni YOLO-seg, ni U-Net supervisada. Se difiere hasta
que se cumplan los triggers de D4.

Lo que sí se decide hoy es **cómo se decidirá**, que es lo que impide que la
elección acabe siendo una preferencia disfrazada de arquitectura.

### D2 — Candidatos y el criterio que los separa

| Candidato | A favor | En contra en ESTE proyecto |
|---|---|---|
| **Mask R-CNN** (+ cajas rotadas) | Dos etapas: propone regiones antes de trazar máscara, lo que ayuda cuando dos cromosomas comparten píxeles. Las variantes rotadas predicen el ángulo, útil para enderezar | El más caro de entrenar y de inferir. **Prohibido por AGENTS §11** — requiere la derogación de D3 |
| **YOLO-seg** (v8/v11) | Mucho más rápido; una sola etapa | Tiende a fusionar objetos que se tocan, que es exactamente el fallo a corregir |
| **U-Net + watershed** | Es el modelo que AGENTS §11 ya declara canónico; ADR-0007 lo asume | Segmentación semántica: separa instancias por post-proceso morfológico, que es lo que ya falla hoy |

El criterio que los separa **no es la literatura**: es el protocolo de D5 sobre
las metafases anotadas del laboratorio.

### D3 — Adoptar Mask R-CNN exigiría derogar AGENTS §11, explícitamente

AGENTS §11 dice: *«❌ Usar Mask R-CNN o ResNet50 — los modelos definitivos son
U-Net + EfficientNet-B3»*. Es una regla constitucional, y ADR-0016 llegó a
desviarse de un contrato HTML para respetarla (ADR-0016 D1).

**Un ADR que la contradiga en silencio es inválido en este proceso.** Si el
protocolo de D5 favorece a Mask R-CNN, este ADR se modifica para incluir:

- la derogación nominal de AGENTS §11 en lo tocante a Mask R-CNN
- la evidencia medida que la justifica
- la actualización de AGENTS.md, que es la fuente de verdad, en el mismo cambio

Y si el protocolo no lo favorece, la regla se queda como está. La derogación es
una consecuencia posible de la medición, **no una premisa**.

### D4 — Triggers para reabrir la decisión

Se reabre cuando se cumplan **los dos**:

1. **≥ 300 metafases con máscaras de instancia**, producidas por el flujo de
   ADR-0034. Es el orden de magnitud mínimo para entrenar y dejar fuera un
   conjunto de prueba honesto.
2. **Un conjunto de prueba separado por caso** —no por imagen— siguiendo el
   criterio del cuaderno v3: ningún paciente en entrenamiento y validación a la
   vez.

Hasta entonces, el sistema sigue con OpenCV + watershed y con la mitigación
estructural que ya está medida (ADR-0033: 259 → 105 copias imposibles).

### D5 — Protocolo de evaluación, fijado antes de tener los datos

Se fija ahora, y por escrito, para que no se ajuste después a lo que salga:

- **Métrica primaria:** F1 de instancia con IoU ≥ 0,5 sobre el conjunto de
  prueba. Es lo que hoy no se puede calcular y lo que decidirá.
- **Métrica de producto:** acciones de corrección por caso
  (`eval_correccion.py`), contra la línea base de 64. Un detector que suba el F1
  y no baje las acciones no resuelve el problema del laboratorio.
- **Coste de inferencia medido en la máquina real, sin GPU.** No se aceptan
  cifras de literatura: el pipeline actual tarda 26–32 s por metafase, y
  cualquier estimación optimista de «1–2 s por placa» debe verificarse antes de
  escribirse.
- **Los tres candidatos se miden sobre el mismo conjunto.** Un A/B con el banco
  intacto, como se hizo con el enrutador.

### D6 — La segmentación asistida no desaparece cuando llegue el detector

Aunque el detector automático mejore, la corrección interactiva de ADR-0034 se
mantiene: RN-01 exige validación manual, y el flujo sigue alimentando el corpus.
El detector reduce el trabajo; no elimina al analista.

## Consecuencias

**A favor**

- Impide adoptar un modelo que no se podría entrenar ni medir, que es la
  situación real de hoy.
- Deja el criterio escrito **antes** de ver los resultados, que es lo único que
  evita elegir el modelo preferido y buscarle la métrica después.
- Respeta el proceso constitucional en vez de saltárselo.

**En contra**

- **Retrasa la mejora del cuello de botella conocido.** Se asume a conciencia:
  el coste de elegir mal, en un sistema clínico, es mayor que el de esperar a
  tener con qué medir.
- **Depende por completo de ADR-0034.** Si la anotación asistida no produce
  corpus, este ADR se queda bloqueado indefinidamente. Es una dependencia real
  y conviene vigilarla, no esconderla.

## Alternativas descartadas

**Adoptar Mask R-CNN ahora, sobre la base de la literatura.** Es lo que proponía
el borrador inicial. Se descarta por tres motivos: no hay datos para entrenarlo,
no hay métrica para compararlo con nada, y contradice AGENTS §11 sin derogarla.
El primero de los tres ya lo hace inejecutable.

**Anotar un dataset a mano antes de tocar el producto.** Es el camino ortodoxo y
sigue siendo válido, pero cuesta meses de citogenetista — el recurso más escaso
del laboratorio, que es el problema que este proyecto existe para aliviar.
ADR-0034 obtiene lo mismo del trabajo que el analista ya hace.

**Datos sintéticos a partir de los 48.467 recortes.** Componer metafases
artificiales pegando recortes sobre un fondo es viable y barato, y queda como
**complemento**, no como sustituto: un cromosoma pegado no se toca con otro
igual que uno que creció tocándolo, y el dominio sintético es justo donde un
detector aprende atajos que no generalizan. Puede servir para preentrenar;
no para evaluar.
