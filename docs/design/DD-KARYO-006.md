# DD-KARYO-006 — Ver los cromosomas reales en el cariograma

| Campo | Valor |
|---|---|
| **ID** | DD-KARYO-006 |
| **ADR origen** | [ADR-0021](../adr/0021-visor-correccion-cariotipo.md) §D5 (visor y corrección) · [ADR-0016](../adr/0016-registro-muestras-captura-metafases.md) (`SampleImage`, metafases en `MEDIA_ROOT`) |
| **FSD** | FSD-UC-003 (corrección manual del cariotipo) |
| **Reglas** | RN-03 (sin PII), RN-06 (alcance del analista), RN-07 (degradación elegante), RN-09 (cobertura ≥ 90 %) |
| **Estado** | **Aprobado** por el autor el 2026-10-13, tal cual · en implementación |
| **Fecha** | 2026-10-01 (propuesta) · 2026-10-13 (aprobación) |
| **Corrige** | [DD-KARYO-005](DD-KARYO-005.md) §4.1 (coordenadas del recorte, ver §2) |

## 1. Por qué existe

Hoy el analista **corrige cromosomas que no ve**. El cariograma de Konva dibuja
cada cromosoma como un rectángulo de color de 22 × 100 con su número de clase
(`KaryotypeCanvas.tsx`, `<Rect fill={SEMAPHORE_FILL[...]}>`). Separar, unir,
resolver cruces y recortar funcionan, pero sobre cajas: el analista no ve la
forma, las bandas ni si el recorte se comió medio cromosoma vecino. Es el
equivalente a corregir un texto sin poder leerlo.

Las piezas para mostrarlos ya existen y se midieron el 01/10 sobre la base local:

| Medido | Resultado |
|---|---|
| Cariotipos con metafase real en disco | **14 de 17** (los 3 restantes son del seed de demo) |
| Formato real de esas metafases | **BMP** en los 39 ficheros reales (la extensión `.img` no lo dice) |
| Cajas de cromosoma que caen fuera de su imagen | **0 de 616** |
| Extremo de las cajas frente al tamaño de la imagen | coincide (p. ej. 914 × 712 en metafases de 1024 × 768) |

Las cajas (`Chromosome.bbox`) están en **píxeles de la metafase**: recortar es
directo, sin transformaciones.

## 2. El defecto que esta especificación destapa y corrige

DD-KARYO-005 §4.1 afirma que el recorte manual (RECROP) «emite el bbox en
píxeles de la metafase». **No es así.** `KaryotypeCanvas` calcula el rectángulo
con `getAbsoluteTransform().copy().invert()`, que deshace zoom y rotación pero
devuelve coordenadas **del lienzo del cariograma** —la cuadrícula de pares—, y
`KaryotypePage.handleCropDone` las envía sin transformar a
`POST /chromosomes/{cid}/recrop/`, que las interpreta como píxeles de la
metafase. El servidor reclasifica así una región de la metafase que no tiene
relación con lo que el analista dibujó.

Confirmado por lectura del código; **no reproducido todavía en la aplicación**
(el recorte nunca tuvo E2E real, pendiente declarado en su entrega). La
reproducción es la primera prueba de la tarea T4.

Este defecto no se puede dejar para después: en cuanto el analista vea
cromosomas reales usará el recorte sobre ellos, y el resultado sería erróneo
sin ninguna señal visible.

## 3. Decisiones

### D1 · Una imagen por caso; el recorte se hace en el cliente
Se sirve la metafase entera una vez y Konva recorta cada cromosoma con la
propiedad `crop` de `Image`. Frente a un endpoint por cromosoma:

- **1 petición** por caso en vez de 36–53;
- separar, unir y recortar cambian el `bbox` y la imagen se recorta de nuevo al
  instante, sin pedir nada;
- el servidor no procesa imágenes (el backend clínico no tiene Pillow).

### D2 · Los bytes se sirven tal cual; el tipo sale de la firma, no de la extensión
Los navegadores muestran BMP de forma nativa. El `Content-Type` se decide por
los primeros bytes (BMP, PNG o JPEG); cualquier otra cosa —como los ficheros
marcadores de 11 a 54 bytes que dejan tests y seeds— se trata como «sin imagen».

**Coste declarado:** un BMP de 1024 × 1177 son ~3,6 MB sin comprimir por caso.
Aceptable en la red del laboratorio y con caché del navegador; si molesta,
convertir a PNG es una decisión aparte (añade Pillow).

### D3 · El mismo alcance que el visor, no una regla nueva
`HasOpcion('sample.view')` + `_get_owned_sample_or_none` → **403 `NOT_OWNER`**
para un analista que abre un caso ajeno; supervisor y administrador ven
cualquiera. Es exactamente lo que hace `KaryotypeView`. La lección de AI-SEC-001
(M9) fue que una segunda política para el mismo dato acaba divergiendo.

### D4 · La imagen que se sirve es la que se segmentó
Hoy esa elección está escrita tres veces en `services.py`
(`sample.images.order_by('order', 'captured_at').first()`, líneas 239, 369 y
987, la última del recorte). Se extrae a una única función
`metafase_segmentada(sample)` y la usan las tres llamadas y el endpoint nuevo.
Si un día cambia el criterio, cambia en un sitio y el visor sigue mostrando la
imagen con la que se calcularon las cajas.

### D5 · Sin imagen no es un error: se ve como hoy
`404 NO_METAPHASE_IMAGE` si no hay metafase, si el fichero falta o si su firma
no es de imagen. El cliente lo trata como degradación (RN-07): pinta los
rectángulos de color actuales y lo indica con una línea discreta, sin bloquear
ninguna herramienta.

### D6 · La ruta nunca sale del servidor y no puede escaparse de `MEDIA_ROOT`
El `image_path` se resuelve y se comprueba que queda dentro de `MEDIA_ROOT`
antes de abrirlo. La respuesta no incluye la ruta. Las metafases no llevan PII
(RN-03): las carpetas usan el código CHN anonimizado.

### D7 · El recorte se dibuja sobre la metafase real
RECROP pasa a dibujarse en un panel **«Metafase»** que muestra la región del
cromosoma seleccionado (su `bbox` más un margen) a escala ampliada. El
rectángulo se convierte a píxeles de la metafase con una transformación lineal
pura (`lib/recorteMetafase.ts`). Arregla el defecto del §2 y, de paso, permite
**agrandar** un recorte que se quedó corto, cosa imposible dibujando dentro del
rectángulo de 22 × 100.

### D8 · Los cromosomas tumbados se muestran de pie *(enmienda del 13/10, aprobada por el autor)*
La primera prueba en un navegador real enseñó que, con la imagen a la vista,
**no se ven lo bastante como para corregir**. Medido sobre los 565 cromosomas
con caja de la base local:

| | Valor |
|---|---|
| Tumbados (caja más ancha que alta) | **347 (61 %)** |
| Alto que ocupan en su hueco de 100 px | mediana **18 px** (tumbados 15, de pie 35) |

Encajados sin deformar en un hueco vertical de 22 × 100, los tumbados quedan
como una franja fina. Se **giran 90° solo para mostrarlos**, de modo que el eje
largo quede vertical; el `bbox` no cambia y el recorte sigue siendo el mismo.

**Lo que esto NO hace:** decidir qué extremo es el brazo p. Algunos quedarán
cabeza abajo; orientar según la convención ISCN sigue siendo la próxima
especificación (§6).

## 4. Backend

| Pieza | Detalle |
|---|---|
| `GET /api/clinic/samples/{id}/karyotype/metaphase/` | `MetaphaseImageView`. 200 con los bytes; 403 `NOT_OWNER`; 404 `NO_KARYOTYPE`; 404 `NO_METAPHASE_IMAGE`. Cabeceras: `Content-Type` por firma, `Cache-Control: private, max-age=300`, `X-Content-Type-Options: nosniff`. |
| `metafase_segmentada(sample)` | Única elección de la metafase (D4), usada por las tres llamadas existentes y por el endpoint. |
| `tipo_de_imagen(bytes)` | Firma → `image/bmp`, `image/png`, `image/jpeg` o `None`. |
| Auditoría | Ninguna: es una lectura, igual que `GET /karyotype/`. |

## 5. Frontend

| Pieza | Detalle |
|---|---|
| `clinicRequestBlob` | Variante del cliente que devuelve un `Blob` con las mismas cabeceras (`Authorization`, `X-Biomed-Mode`). Un `<img src>` no puede enviar el token. |
| `useMetaphaseImage(sampleId)` | Descarga una vez, crea el `objectURL`, carga un `HTMLImageElement` y **revoca la URL al desmontar**. Un 404 devuelve `null` (degradación), no un error. |
| `KaryotypeCanvas` | Por cromosoma, si hay imagen: `KonvaImage` con `crop = bbox`, escalada para caber en el cuerpo **sin deformarla** (relación de aspecto conservada). El semáforo pasa a ser el **borde** para que la imagen se vea. Sin imagen: el rectángulo actual. Brillo y contraste de P4 actúan por fin sobre píxeles reales. |
| `MetafasePanel` + `lib/recorteMetafase.ts` | El recorte del §D7. La conversión de coordenadas es una función pura con cobertura total. |

## 6. Fuera de alcance, declarado

- **Orientar** según ISCN (brazo p arriba, girar 180°) y **enderezar**:
  próxima especificación. Con esta, los tumbados se ponen de pie (D8), pero sin
  saber cuál de sus extremos es p.
- **Máscaras**: el recorte es la caja, así que puede colarse parte de un vecino.
  Las máscaras de ADR-0035 existen solo fuera del producto, en el dataset.
- **Separar trazando una línea** y **crear detecciones**: especificaciones aparte.
- Las otras dos metafases del caso: siguen sin segmentarse (ADR-0036).
- Compresión a PNG (D2).

## 7. Pruebas (RN-09 ≥ 90 %)

| Capa | Qué se prueba |
|---|---|
| Backend | 200 para el dueño (bytes y tipo correctos) · 200 para el supervisor · **403 para otro analista** · 401 sin sesión · 404 sin cariotipo · 404 con fichero marcador · 404 con fichero ausente · **ruta que intenta salir de `MEDIA_ROOT` rechazada** · `metafase_segmentada` elige la misma imagen que antes en las tres llamadas. |
| Frontend | `clinicRequestBlob` envía las cabeceras · el hook revoca la URL y convierte el 404 en `null` · el lienzo pinta `KonvaImage` con el `crop` del `bbox` y conserva el aspecto · sin imagen pinta el rectángulo · `recorteMetafase` ida y vuelta exacta. El mock global de `react-konva` gana la primitiva `Image`. |
| E2E real | Abrir un caso con metafase real: el endpoint responde 200 y un cromosoma del lienzo tiene píxeles no uniformes (no es un rectángulo liso) · **reproducir el defecto del §2 antes de corregirlo** y comprobar después que el `bbox` guardado cae dentro de la región dibujada · caso del seed sin imagen: rectángulos y aviso, sin error. |

## 8. Plan

Cada tarea cabe en una sesión de ≤ 3 h y se entrega con sus pruebas.

| # | Tarea | Estimación |
|---|---|---|
| T1 | Backend: `metafase_segmentada`, `tipo_de_imagen`, endpoint y sus pruebas | 2 h |
| T2 | Frontend: `clinicRequestBlob` + `useMetaphaseImage` y pruebas | 1,5 h |
| T3 | Lienzo: recortes reales, borde de semáforo, degradación; mock de `Image` | 2,5 h |
| T3b | D8: poner de pie los tumbados (`colocarRecorte`, giro de 90° solo de presentación) | 1,5 h |
| T4 | RECROP: reproducir el defecto en E2E, `MetafasePanel` + `recorteMetafase`, prueba de que queda corregido | 3 h |
| T5 | E2E real completo y capturas | 2 h |
| T6 | Cierre: estado de este documento, nota de corrección en DD-KARYO-005 §4.1, `TASKS.md` | 0,5 h |
