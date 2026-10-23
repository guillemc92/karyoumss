# DD-KARYO-007 — Corrección manual sobre la metafase

| Campo | Valor |
|---|---|
| **ID** | DD-KARYO-007 |
| **ADR origen** | [ADR-0021](../adr/0021-visor-correccion-cariotipo.md) (visor y corrección) · [ADR-0034](../adr/0034-segmentacion-interactiva-sam2.md) (segmentación asistida, *proposed*) · [ADR-0022](../adr/0022-audit-trail-clinico-django.md) (auditoría append-only) |
| **Continúa** | [DD-KARYO-006](DD-KARYO-006.md) (cromosomas reales en el cariograma) |
| **FSD** | FSD-UC-003 (corrección manual del cariotipo) |
| **Reglas** | RN-01 (validación manual), RN-05 (auditoría solo de inserción), RN-06 (alcance del analista), RN-07 (degradación), RN-09 (cobertura ≥ 90 %) |
| **Estado** | **Aprobado** por el autor el 2026-10-23 · respuestas a §9 en §10 |
| **Fecha** | 2026-10-23 |

## 1. Por qué existe

El autor, al usar el visor con un caso real el 23/10: *«no está bien la interfaz más
importante, que es la manipulación manual de los cromosomas»*.

Al revisarlo aparecen dos causas. Una es de diseño. La otra es más grave, porque
**las operaciones no hacen lo que su nombre dice**.

### 1.1 Las operaciones de edición no miran la imagen

Leído en `backend-clinic/apps/samples/services.py`:

| Operación | Qué promete | Qué hace hoy |
|---|---|---|
| `split_chromosome` | Separar dos cromosomas que se tocan | Parte la caja **por la mitad vertical**: el original se queda con la mitad izquierda y el nuevo con la derecha. No mira la imagen ni deja elegir dónde cortar. |
| `join_chromosomes` | Unir dos fragmentos | Une las dos cajas en su rectángulo envolvente. Sirve, pero arrastra todo lo que haya en medio. |
| `resolve_cross` | Resolver un cruce | Solo marca el cromosoma como `RESOLVED`. No separa nada. |

Un racimo en diagonal, o dos cromosomas uno encima de otro, no se separan partiendo
la caja por la mitad. El analista no tiene forma de decirle al sistema **dónde**
está la frontera.

### 1.2 Se corrige sobre la vista equivocada

Todas las herramientas de P3/P4 y DD-KARYO-006 trabajan sobre el **cariograma**,
una cuadrícula de huecos de 22 × 100 px. La metafase solo aparece en el panel de
recorte.

Los dos sistemas de referencia trabajan sobre la metafase:

- **MetaClass**, el sistema que el laboratorio usa y que este proyecto reemplaza
  (`ayuda.pdf`, cap. 3.2): separación manual **trazando una línea**, resolución de
  cruces, eliminación de objetos, giro de 180° de cada cromosoma.
- **Ikaros 7** (`ikaros.pdf`), solo como referencia del estado del arte:
  - la metafase grande en el centro, con el **contorno** de cada objeto;
  - **Flex Mode**, que corta con líneas y une con la misma herramienta;
  - *Add Objects* y *Reject Objects*;
  - el cariograma al lado, con los cromosomas de pie y por parejas;
  - deshacer el último paso con un clic.

Ninguno de los dos corrige sobre cajas abstractas. La segmentación se corrige en la
**metafase**, y el cariograma sirve para **ordenar**.

### 1.3 Lo que se midió antes de escribir esto

| Medido | Resultado | Fuente |
|---|---|---|
| Coste de corregir lo que propone la IA | 64 acciones por caso, frente a 46 haciéndolo a mano | `eval_correccion.py`, 17/08 |
| MobileSAM en la CPU del laboratorio (i5-3317U, sin GPU) | Codificador **5,5 s** por metafase; decodificador **~450 ms** por clic | Experimento del 23/10 |
| MobileSAM, un clic en cromosomas aislados | IoU mediana **0,80** (13 de 15 ≥ 0,7) | Ídem, metafase_54 |
| MobileSAM, clic positivo y negativo en dos cromosomas que se tocan | Los separa **sin solaparlos**, pero cubre solo el **61–85 %** del racimo | Ídem, metafase_207 |
| Siluetas por Otsu dentro de la caja | Precisión **99,4 %** (píxeles de máscara sobre tinta) | ADR-0035, `verificar_mascaras.py` |

Conclusión: SAM sirve como **asistente**, pero no basta solo. Hace falta una
herramienta manual de corte fiable. Por eso aquí el corte por línea va primero y SAM
después.

## 2. Alcance por fases

Cada fase se entrega con sus pruebas y es útil por sí sola.

| Fase | Qué aporta | Depende de |
|---|---|---|
| **F1** · Metafase como lienzo de edición | La metafase grande con el contorno de cada objeto; seleccionar en ella o en el cariograma es lo mismo; **descartar** objetos (núcleos, suciedad) y **añadir** los que faltan | DD-KARYO-006 (ya hecho) |
| **F2** · Separar y unir de verdad | **Cortar trazando una línea** sobre la metafase; unir por máscara; deshacer la última edición | F1 |
| **F3** · Cariograma legible | Huecos a buen tamaño, parejas sobre una línea base, girar 180° y voltear cada cromosoma | F1 (en paralelo con F2) |
| **F4** · Asistente de clic (SAM) | Clic positivo o negativo para proponer una máscara; el analista la acepta o la descarta | F2, y **ADR-0034 en `accepted`** |

F4 queda bloqueada hasta que ADR-0034 se acepte. Además, ese ADR elige SAM 2 y aquí
se midió MobileSAM, que es otro modelo. Si se adopta MobileSAM, hace falta un ADR
nuevo que lo diga; ADR-0034 no se edita.

## 3. Decisiones

### D1 · Cada objeto lleva una máscara, no solo una caja
`Chromosome` gana un campo `contour`: un polígono en píxeles de la metafase,
`[[x, y], …]`. El `bbox` se conserva y se recalcula como el envolvente del contorno.

- **Por qué un polígono y no RLE ni un PNG por cromosoma:**
  - Konva lo dibuja tal cual con `Line closed`;
  - ocupa poco en JSON;
  - se puede auditar a simple vista;
  - y cortar un polígono con una línea es geometría simple.
- **De dónde sale al principio:** se calcula Otsu dentro del `bbox` y se toma el
  contorno exterior mayor. Es el método de ADR-0035, con 99,4 % de precisión.
- **Casos ya existentes:** el contorno se calcula al vuelo la primera vez y no se
  reescribe en casos validados (RN-04).
- **Sin contorno** (sin metafase, o si Otsu falla): se dibuja la caja, como hoy (RN-07).

### D2 · La metafase es el lienzo principal; el cariograma va al lado
La página de cariotipo pasa a tener dos paneles:

- **Metafase**, grande, con zoom y desplazamiento: el contorno de cada objeto,
  coloreado por su semáforo.
- **Cariograma** (DD-KARYO-006), más estrecho, para ordenar y reclasificar
  arrastrando.

Seleccionar un objeto en uno lo selecciona en el otro. El panel de recorte de
DD-KARYO-006 deja de ser una ventana aparte: el recorte se hace en el panel Metafase.

### D3 · Separar es trazar una línea
El analista traza una polilínea que atraviesa el objeto. El servidor:

1. corta el polígono del objeto con la línea y obtiene dos o más trozos;
2. descarta los trozos de menos de N px (ruido del trazo);
3. el original se queda con el trozo mayor y cada trozo restante crea un cromosoma
   nuevo;
4. reclasifica cada trozo con el clasificador, como ya hace RECROP. Si backend-ml no
   responde, los trozos quedan en la clase de origen y en naranja (RN-07).

El evento `SPLIT` guarda la línea, los ids resultantes y la clase de cada uno.
**Desaparece el corte automático por la mitad**: la API recibe la línea y sin línea
responde 400.

### D4 · Unir es unir máscaras
`JOIN` une los dos polígonos (unión geométrica) y el `bbox` pasa a ser su envolvente.
Si no se tocan, se guardan como multipolígono: un cromosoma partido en dos manchas
sigue siendo un cromosoma.

### D5 · Descartar y añadir son eventos propios
- **Descartar** (`REJECT_OBJECT`, nuevo): `is_active = False`, con el motivo
  (`nucleo`, `suciedad`, `duplicado`, `otro`). Es el mismo borrado suave que ya usa
  `join`.
- **Añadir** (`ADD_OBJECT`, nuevo): el analista dibuja la caja (o, en F4, hace clic)
  sobre una zona sin objeto. Se calcula el contorno (D1) y se clasifica.

Ninguno de los dos borra filas ni eventos (RN-05).

### D6 · Deshacer es un evento que compensa, no un borrado
La auditoría es solo de inserción (RN-05, ADR-0022), así que deshacer no puede
borrar el evento anterior. `UNDO_EDIT` (nuevo) restaura el estado previo del objeto
o los objetos afectados: el evento original guarda lo necesario en su `payload`. Se
puede deshacer **la última edición del propio analista sobre el caso**; no se
deshace la de otro ni nada que sea anterior a la validación.

### D7 · Girar y voltear son de presentación, y quedan auditados
En el cariograma, girar 180° y voltear horizontalmente un cromosoma es lo que hace
MetaClass para poner el brazo p arriba. Se guarda en `Chromosome.measures` como
`orientacion` y emite `ORIENT` (nuevo). No cambia el `contour` ni el `bbox`, que
siguen en coordenadas de la metafase. La orientación automática según ISCN queda
fuera (§6).

### D8 · Todo edita solo si el caso es editable
Cada operación nueva pasa por `_assert_editable` (bloqueo del caso, 409) y por el
mismo alcance que el visor (`HasOpcion('sample.view')` más ser el dueño; 403
`NOT_OWNER`). Ninguna operación cambia el gate RN-01: un trozo nuevo con confianza
< 0,85 entra en naranja y hay que resolverlo como cualquier otro.

## 4. Backend

| Pieza | Detalle |
|---|---|
| Migración | `Chromosome.contour` (JSON, nullable). Tipos de evento nuevos: `REJECT_OBJECT`, `ADD_OBJECT`, `UNDO_EDIT`, `ORIENT`. |
| `contorno_inicial(sample, chromosome)` | Otsu dentro del `bbox` y contorno exterior mayor (D1). Necesita OpenCV en backend-clinic, o pedírselo a backend-ml. **Se decide en la pregunta abierta 1.** |
| `POST …/chromosomes/{cid}/split/` | Recibe `{linea: [[x, y], …]}` en píxeles de la metafase. 400 sin línea o si la línea no corta el objeto. |
| `POST …/chromosomes/{cid}/join/` | Igual que hoy, pero une contornos (D4). |
| `POST …/chromosomes/{cid}/reject/` | `{motivo}` (D5). |
| `POST …/karyotype/objects/` | `{bbox}`: añade un objeto (D5). |
| `POST …/karyotype/undo/` | Deshace la última edición del actor (D6). |
| `POST …/chromosomes/{cid}/orient/` | `{giro: 0 \| 180, volteo: bool}` (D7). |
| `resolve_cross` | Se mantiene, pero el cruce se resuelve con D3: la línea va **a lo largo** de uno de los dos cromosomas. |

## 5. Frontend

| Pieza | Detalle |
|---|---|
| `MetafaseEditor` (nuevo, Konva) | La metafase a tamaño completo con zoom y desplazamiento; contornos con el semáforo como color; selección; herramientas: seleccionar, cortar (polilínea), añadir (caja), descartar. |
| `lib/geometriaContorno.ts` | Funciones puras: cortar un polígono con una polilínea, unir polígonos, envolvente, punto dentro. Cobertura total. |
| `KaryotypeCanvas` | Queda como panel de ordenación: huecos escalados al ancho disponible, parejas alineadas en la línea base, giro y volteo (F3). |
| Barra de edición | Deshacer (D6), con el texto de la última edición a la vista, como Ikaros. |
| Atajos | Los de MetaClass donde existan (Alt+S separar, Alt+C cruce, Supr descartar) para no romper la memoria muscular del laboratorio. |

## 6. Fuera de alcance, declarado

- **Orientación automática ISCN** (decidir qué extremo es p). D7 es manual.
- **Pincel píxel a píxel**: descartado por ADR-0034.
- **Multimetafase** (ADR-0036): se sigue editando solo la primera metafase.
- **Ideogramas** (*Insert Ideograms* de Ikaros) y la galería de células del caso.
- **SAM 2 frente a MobileSAM**: lo decide el ADR que desbloquee F4, no esta spec.

## 7. Pruebas (RN-09 ≥ 90 %)

| Capa | Qué se prueba |
|---|---|
| Geometría (front, puras) | Cortar en recta y en diagonal; una línea que no corta; una línea que corta dos veces (tres trozos); trozos menores del mínimo; unión de polígonos que se tocan y que no; ida y vuelta con el `bbox` |
| Backend | SPLIT con línea crea N cromosomas con el contorno correcto y un evento con la línea · sin línea 400 · caso bloqueado 409 · analista ajeno 403 · REJECT, ADD, ORIENT y UNDO emiten su evento y no borran nada · UNDO de otro actor rechazado · trozos sin backend-ml quedan en naranja |
| E2E real | Separar un racimo real (metafase_207, par 18 + 12) trazando una línea: salen dos objetos y los dos aparecen en el cariograma · descartar el núcleo de la metafase_331 · deshacer el corte · **reproducir antes el defecto**: hoy `split` parte por la mitad aunque la frontera sea diagonal |

## 8. Plan

| # | Tarea | Fase | Estimación |
|---|---|---|---|
| T1 | `contour` + migración + `contorno_inicial` + pruebas | F1 | 2,5 h |
| T2 | `MetafaseEditor`: metafase, contornos, selección sincronizada con el cariograma | F1 | 3 h |
| T3 | Descartar y añadir objetos (back + front + eventos) | F1 | 2,5 h |
| T4 | `geometriaContorno.ts` (cortar y unir) con cobertura total | F2 | 2,5 h |
| T5 | SPLIT por línea y JOIN por máscara en el backend; E2E que reproduce el defecto | F2 | 3 h |
| T6 | Herramienta de corte en el editor + deshacer (D6) | F2 | 3 h |
| T7 | Cariograma legible: escala, línea base, girar y voltear (D7) | F3 | 2,5 h |
| T8 | E2E completo, capturas y cierre | F1–F3 | 2 h |
| — | F4 (SAM): spec propia cuando ADR-0034 (o el ADR que lo sustituya) esté `accepted` | F4 | — |

Total F1–F3: unas 21 h.

## 9. Preguntas abiertas para el autor

1. **¿Dónde se calcula el contorno?** En backend-clinic con OpenCV (una dependencia
   nueva en el servicio clínico), o en backend-ml, que ya lo tiene (una llamada de red
   más, y si backend-ml no está, se ve la caja).
2. **¿Cuántos huecos de deshacer?** Esta spec propone solo la **última edición**.
   Varios niveles complican la regla de «no deshacer lo de otro».
3. **¿Atajos de MetaClass?** Confirmar con el laboratorio cuáles se usan de verdad.
4. **¿Orden de las fases?** La propuesta es F1 → F2 → F3. F3 puede ir antes si lo que
   más molesta es ver el cariograma.

## 10. Respuestas (aprobación del 2026-10-23)

El autor aprobó la especificación tal cual («está bien»). Las preguntas 2 a 4 quedan
con lo que se proponía. La 1 no tenía propuesta y se decidió con un criterio ya escrito.

1. **El contorno lo calcula backend-ml.** DD-KARYO-006 D1 ya fijó que el servidor
   clínico no procesa imágenes (no tiene Pillow, y menos OpenCV).
   - backend-ml ya devuelve las detecciones y ahora devuelve también el contorno de
     cada una, en la misma respuesta.
   - Para los casos existentes: `POST /api/v1/contours/` (metafase + cajas → contornos).
   - El **corte por línea (D3) también se hace en backend-ml, en ráster**: se pinta la
     máscara del objeto, se borra la línea con 3 px de grosor y se toman los
     componentes conexos. Es más robusto que cortar polígonos a mano.
   - Por eso **T4 cambia**: `geometriaContorno.ts` queda para la vista previa del
     corte y el punto dentro de un contorno. El corte de verdad lo prueba backend-ml.
   - Sin backend-ml se ve la caja y separar por línea no está disponible (RN-07), igual
     que hoy no hay reclasificación sin él.
2. **Deshacer:** solo la última edición del propio analista.
3. **Atajos:** los del manual de MetaClass (Alt+S, Alt+C, Supr), pendientes de
   confirmar con el laboratorio. Son configurables, no definitivos.
4. **Orden:** F1 → F2 → F3.
