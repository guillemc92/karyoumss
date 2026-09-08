# DD-KARYO-005 — Recorte manual del cromosoma con reclasificación (RECROP)

| Campo | Valor |
|---|---|
| **ID** | DD-KARYO-005 |
| **ADR origen** | [ADR-0021](../adr/0021-visor-correccion-cariotipo.md) §D5 (levanta parcialmente el diferimiento de DD-KARYO-004 §1) + [ADR-0022](../adr/0022-audit-trail-clinico-django.md) |
| **FSD** | FSD-UC-003 (corrección manual del cariotipo) |
| **Reglas** | RN-05 (audit append-only), RN-07 (degradación elegante), BR-004 (XAI antes de aceptar) |
| **Estado** | Implementado |
| **Fecha** | 2026-08-17 |
| **Commits** | `f541914` (backend + backend-ml), `9235dce` (frontend) |

## 1. Por qué existe

La segmentación de `backend-ml` es OpenCV + watershed (no U-Net; ver
`docs/DTI.md` §9). Su fallo dominante, **medido**, es la **sub-segmentación**:
dos o más cromosomas que se tocan salen como una sola detección. En
`metafase_1`, 18 de 36 objetos se clasificaron como «clase 1» — y no porque el
clasificador se equivoque, sino porque un cúmulo **es** más grande que
cualquier cromosoma, y la clase 1 es la más grande. El recorte malo produce la
clase mala.

Mientras no exista un segmentador mejor, la única vía para obtener un
cariotipo clínicamente utilizable es que el analista corrija el límite a mano.
Esta es esa vía.

### 1.1 Qué diferimiento levanta, y qué sigue diferido

DD-KARYO-004 §1 difirió el «editor de segmentación manual desde cero (dibujar
bounding boxes)» por depender de imágenes reales y del pipeline de ADR-0007.
Ambas cosas ya existen (dataset MetaClass real + `backend-ml` con clasificador
entrenado), pero **RECROP no es ese editor**: mueve el límite de una detección
que ya existe. **Sigue diferido** crear detecciones nuevas donde la
segmentación no vio nada — es un caso distinto, sin cromosoma al que
reclasificar.

## 2. La decisión que da sentido a la función

**El recorte arrastra una reclasificación.** Si el analista corrige el límite y
la clase se quedara como estaba, el sistema mostraría una clase calculada sobre
píxeles que ya nadie ve: peor que no tener la herramienta, porque parecería
correcta. Por eso `recrop_chromosome()` vuelve a llamar al clasificador con el
bbox **nuevo**, y el cromosoma **vuelve a `PENDING` con `xai_viewed = False`** —
la decisión anterior se tomó mirando otra imagen, así que BR-004 se reabre.

Verificado con datos reales: partir por la mitad el bbox del primer cromosoma
de `metafase_1` cambia la predicción de clase 1 a clase 3. El bucle se cierra.

### 2.1 Por qué no es SPLIT

`split()` parte un cromosoma en dos por la **mitad** del bbox — heurística
cruda: los cromosomas que se tocan casi nunca se separan por el centro
geométrico. RECROP no divide nada: mueve el borde de **uno**. Son operaciones
distintas, con eventos de auditoría distintos.

## 3. Backend

| Pieza | Detalle |
|---|---|
| `AuditEventType.RECROP` | Migración `0016_recrop_event`. Evento propio: `bbox_previo`, `bbox_nuevo`, `clase_previa`, `clase_nueva`, `reclasificado`, `motivo`. |
| `services.recrop_chromosome()` | Valida el bbox (`x,y,w,h` presentes, `w>0`, `h>0`), respeta el case-lock, reclasifica y emite el evento. |
| `POST /api/v1/classify/` (backend-ml) | Clasifica **un** recorte. Recibe la metafase **entera** + bbox, no el recorte suelto: el preprocesado usa `ref_h` —la mediana de alturas de todas las detecciones— como señal de escala. |

### 3.1 Degradación (RN-07)
Si el pipeline está caído, el recorte **se guarda igual** y el evento anota
`reclasificado: false` + `motivo`. Perder la corrección manual del analista por
una caída de infraestructura sería peor que quedarse sin reclasificar; y sin
esa anotación, un revisor creería que la clase corresponde al recorte nuevo.

### 3.2 Un bbox inválido no deja evento
Un rechazo no es un acto clínico: `ValueError` antes de tocar el audit trail.

## 4. Frontend

| Pieza | Detalle |
|---|---|
| `lib/recorte.ts` | Geometría pura: `rectanguloDeRecorte()` normaliza las dos esquinas (el analista arrastra en las cuatro direcciones; el servidor exige `w`/`h` positivos) y redondea a píxeles enteros. `esRecorteUtil()` descarta el clic suelto (`RECORTE_MIN = 8` px de lado). |
| `KaryotypeCanvas` | `cropMode` + `onCropDone`. `mouseDown/Move/Up` dibujan el rectángulo; **`mouseLeave` cancela** —soltar fuera del lienzo dejaría el rectángulo pegado al cursor—. |
| `ChromosomePropertiesPanel` | Botón «Recortar y reclasificar» sobre el cromosoma seleccionado. |
| `KaryotypePage` | Guarda el **id** del cromosoma que se recorta, no un booleano: el rectángulo se dibuja sobre el lienzo entero y hay que saber a cuál de los 46 se aplica. |

### 4.1 Coordenadas: metafase, no pantalla
El bbox se emite en píxeles de la **metafase**, deshaciendo zoom, rotación y
desplazamiento con `getAbsoluteTransform().copy().invert()`. Sin eso, recortar
con la vista ampliada guardaría una región distinta de la que el analista ve.

### 4.2 Modos excluyentes
Medir y recortar son ambos un arrastre sobre el mismo lienzo, y el arrastre de
un cromosoma es la reclasificación por drag & drop. Activar el recorte apaga la
medición y desactiva `draggable` en los cromosomas; sin eso, recortar movería
el cromosoma de par sin que nadie lo pidiera. El modo se apaga **solo al
soltar**: recortar es un acto puntual, no un estado en el que uno se queda.

## 5. Tests (RN-09 ≥90%)

**Backend** (`test_recrop.py`, 11 tests): el recorte arrastra clase nueva; se
clasifica con el bbox **nuevo** (con el viejo daría justo la clase que se
intenta corregir); vuelve a `PENDING`/`xai_viewed=False`; sin IA se guarda el
recorte y la traza dice que no se reclasificó; bbox inválido rechazado y **sin
evento**.

**Frontend** (14 tests): `recorte.spec.ts` (geometría pura, 100% cobertura),
`karyotypeCanvas.spec.tsx` (máquina de estados del arrastre: normalización,
clic suelto, cancelación al salir, exclusión con el drag de reclasificación),
`karyotypeRecorte.spec.tsx` (página contra MSW: la clase cambia, BR-004 se
reabre, el modo se apaga, queda en la bitácora).

**Cobertura frontend tras el cambio:** 97.52% stmts / 91.83% branch.

### 5.1 Lo que este reparto de tests demostró
`karyotypeClient.recrop` serializaba el cuerpo dos veces —`clinicRequest` ya
hace `JSON.stringify`—, así que el servidor recibía una cadena y no veía el
bbox. **El test unitario del lienzo no lo habría cazado nunca**: emitía el bbox
correcto y ahí terminaba su alcance. Lo encontró el test de página contra MSW,
que atraviesa el cliente HTTP de verdad. Es el argumento concreto para no
sustituir integración por unitarios rápidos.

## 6. Mock de react-konva

Konva no funciona en jsdom. El mock global (`tests/setup.ts`) ahora reenvía los
eventos de ratón con un stage de identidad, lo que permite probar la **máquina
de estados** del arrastre sin canvas. La conversión real de coordenadas es de
Konva y se sigue validando en **E2E (Chromium)**, no aquí.

## 7. Deuda declarada

- **Segmentación manual desde cero** (crear detecciones nuevas): sigue
  diferida, ver §1.1.
- `sampleListPage > "filtro por status VALIDATED"` falla de forma intermitente
  bajo la carga de la suite completa. **Previo a este cambio** (verificado con
  `git stash`), ajeno a RECROP.
