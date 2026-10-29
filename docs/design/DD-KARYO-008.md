# DD-KARYO-008 — Enderezar cada cromosoma en el cariograma

| Campo | Valor |
|---|---|
| **ID** | DD-KARYO-008 |
| **ADR origen** | [ADR-0021](../adr/0021-visor-correccion-cariotipo.md) (visor y corrección) · [ADR-0022](../adr/0022-audit-trail-clinico-django.md) (auditoría append-only) |
| **Continúa** | [DD-KARYO-007](DD-KARYO-007.md). **Sustituye su D7** («girar 180° y voltear»), que no se edita: lo amplía esta. |
| **FSD** | FSD-UC-003 (corrección manual del cariotipo) |
| **Reglas** | RN-04 (lo validado no se reescribe), RN-05 (auditoría solo de inserción), RN-06 (alcance del analista), RN-07 (degradación), RN-09 (cobertura ≥ 90 %) |
| **Estado** | **Aprobado** el 2026-10-28, con las respuestas propuestas en §9 (§10) · T1 a T5 hechas |
| **Fecha** | 2026-10-28 |

## 1. Por qué existe

El autor, el 28/10: *«necesito mejorar la edición de cromosoma, está mal: gira todo
el lienzo, una vez que el modelo los reconoce»*.

### 1.1 Lo que pasa hoy

En la página del cariotipo hay dos giros y no se distinguen:

| Control | Dónde | Qué hace |
|---|---|---|
| ↺ / ↻ | Barra de imagen (`KaryoImageToolbar.tsx`) | Gira **el lienzo entero** de 15° en 15° (`viewport.rotation` en el `Stage`). Es de vista: no se guarda. |
| «↻ Girar 180°» / «⇋ Voltear» | Panel de propiedades, con un cromosoma seleccionado | Gira **solo ese cromosoma**, y únicamente 180° (D7). Emite `ORIENT`. |

El autor quería enderezar un cromosoma. El único botón que gira en pasos pequeños es
el de la barra, y ese gira todo.

El fondo del problema es que **un cromosoma en diagonal no se puede poner de pie**:

- el cariograma solo sabe girarlo 90° si su caja es más ancha que alta (D8 de
  DD-KARYO-006);
- el analista solo puede girarlo 180°;
- el backend rechaza cualquier otro ángulo (`orient_chromosome`, `giro not in (0, 180)`).

### 1.2 Lo que se midió antes de escribir esto

Siluetas de `metafase_1` segmentada por backend-ml (`POST /api/v1/segment/`), con el
eje mayor calculado por momentos de área del polígono. Lo reproduce
`scripts/medir_ejes_cromosomas.py`.

| Medido | Resultado |
|---|---|
| Siluetas | 38 |
| A más de **10°** del eje vertical u horizontal | **27** (71 %) |
| A más de **20°** | **21** (55 %) |
| A más de **30°** | **11** (29 %) |
| Largo sobre su eje frente al lado largo de la caja | mediana **1,01**, máximo **1,23** |

Así que dos de cada tres cromosomas se ven torcidos en el cariograma. Y el más
inclinado se muestra un 23 % más corto de lo que es, cuando el tamaño es lo primero
que se mira para emparejar.

**La primera medición salió mal, y por culpa del medidor.** Las siluetas de
backend-ml vienen en **sentido horario**. Con ese sentido, el área del polígono sale
negativa y todos los momentos cambian de signo, así que el ángulo calculado cae en el
eje **menor**. Lo destapó una cifra imposible: la relación de largos daba 0,47, y no
puede ser menor que 1. La autoprueba con rectángulos solo usaba el sentido
antihorario. Ahora prueba los dos, y la misma prueba es obligatoria en el código (§7).

### 1.3 Un riesgo que hay que resolver a la vez

Cada cromosoma se pinta con el recorte de **su caja** sobre la metafase, sin máscara
(`KonvaImage crop={bbox}` en `KaryotypeCanvas.tsx`).

Para un cromosoma en diagonal, la caja contiene trozos de los vecinos. Hoy se ven en
las esquinas. Si se gira la caja, esos trozos giran con él y se ven peor todavía.
**Enderezar exige recortar por la silueta, no por la caja.**

## 2. Alcance

| Pieza | Qué aporta |
|---|---|
| **A** · Recorte por silueta | Cada cromosoma del cariograma se pinta recortado por su `contour`; desaparecen los trozos de los vecinos |
| **B** · Enderezado automático | Cada cromosoma con silueta se gira hasta dejar su eje mayor vertical. Se calcula al pintar y **no se guarda** |
| **C** · Ajuste fino manual | «−5°», «+5°» y «Restablecer» en el panel. Se guarda en `measures.orientacion` y emite `ORIENT` |
| **D** · Barra sin ambigüedad | ↺ / ↻ pasan a llamarse «Rotar vista». Con un cromosoma seleccionado, la barra avisa de que la vista gira entera |

A va primero: sin A, B empeora lo que se ve.

## 3. Decisiones

### D1 · Se recorta por la silueta
La imagen del cromosoma va dentro de un `Group` de Konva cuyo `clipFunc` dibuja el
`contour`, pasado de píxeles de la metafase a coordenadas del recorte. El fondo claro
y el marco del semáforo no cambian.

- **Sin silueta** (casos antiguos sin contornos, o backend-ml caído): el recorte por
  caja de hoy, sin enderezar (RN-07).
- No se toca el servidor: el `contour` ya viene en la respuesta del cariotipo.

### D2 · El ángulo automático sale de los momentos de área, en el cliente
`lib/ejeCromosoma.ts` (puro, sin Konva) calcula, a partir del `contour`:

1. el centroide y los momentos de segundo orden (fórmula de Green);
2. **corrige el signo según el sentido de recorrido**, que es la trampa de §1.2;
3. el ángulo del eje mayor y el giro, en (−90°, 90°], que lo deja vertical;
4. el largo y el ancho del cromosoma **a lo largo de sus ejes** (proyección de los
   vértices), que sustituyen a los de la caja para la escala común y la línea base.

Si la silueta tiene menos de 3 puntos o área casi nula, devuelve `null` y se usa la
regla de hoy (90° si la caja está tumbada).

Un cromosoma casi redondo (los ejes miden casi lo mismo) tiene un eje mal definido.
Si el largo es menos de **1,2 veces el ancho**, no se endereza: un 21 o un 22
pequeños girarían al azar con un píxel de diferencia en la silueta.

**Por qué en el cliente y no guardado:**

- es presentación, como el giro de 90° que ya existe;
- no reescribe casos validados (RN-04);
- y si mañana se mejora el cálculo, mejora también en los casos viejos.

### D3 · El ajuste manual se suma al automático y queda auditado
`measures.orientacion` gana `ajuste`, en grados enteros dentro de [−90, 90]. El giro
que se pinta es:

`giro final = giro automático (D2) + ajuste + giro (0 | 180)`, con el `volteo` de D7.

- **«−5°» y «+5°»** cambian `ajuste` en 5 y emiten `ORIENT` con la orientación de
  antes y la de después.
- **«Restablecer»** vuelve `ajuste` a 0: se queda solo lo automático.
- Igual que en D7 (§11.10 de DD-KARYO-007), **orientar no es deshacible**: el botón
  contrario lo revierte, y «Deshacer» sigue apuntando al último corte.

### D4 · La API cambia sin romper a nadie
`POST …/chromosomes/{cid}/orient/` acepta un campo nuevo **opcional**, `ajuste`
(entero, −90..90):

- si no llega, **se conserva el `ajuste` guardado**, de modo que un cliente que solo
  envía `giro` y `volteo` no borra el ajuste;
- fuera de rango, no entero o booleano: 400, sin evento;
- `giro` sigue siendo `0 | 180`. No se amplía, para no mezclar el giro de 180° (poner
  p arriba, decisión clínica) con el de enderezar (presentación).

Añadir un campo opcional a una petición no es un cambio incompatible. **oasdiff no
debe marcar ninguna ruptura**, y ese es un criterio de aceptación de esta spec (§7).
El contrato se regenera y el drift pasa.

### D5 · «Rotar vista» se llama así
Los botones ↺ / ↻ de la barra cambian su `title` y su `aria-label` a «Rotar vista a
la izquierda» y «Rotar vista a la derecha», igual que «Voltear horizontal (solo la
vista)». Con un cromosoma seleccionado, la barra muestra «Gira toda la vista; para
este cromosoma, usa el panel». Su comportamiento no cambia.

### D6 · Todo edita solo si el caso es editable
`ajuste` pasa por `_assert_editable` (409) y por el mismo alcance que el visor (403
`NOT_OWNER`), como D8 de DD-KARYO-007. Los botones de C solo aparecen si el caso es
editable y hay metafase. A, B y D se ven siempre, también en casos validados.

## 4. Backend (backend-clinic)

| Pieza | Detalle |
|---|---|
| `orient_chromosome(…, ajuste=None)` | Valida (`int`, no `bool`, −90..90); `None` conserva el guardado. Guarda `{giro, volteo, ajuste}` y el evento lleva `previa` y `nueva` completas. |
| `ChromosomeOrientView` | Pasa `request.data.get('ajuste')` al servicio, igual que hoy `giro` y `volteo`: no hay serializador de entrada y la validación vive en el servicio. |
| `contrato.py` | El esquema de la petición de `orient` gana `ajuste` (entero, −90..90, opcional) y la descripción de `ORIENT` lo menciona. Se regenera `openapi.json`. |
| Migración | **Ninguna**: `measures` ya es JSON. Las orientaciones guardadas sin `ajuste` se leen como 0. |

## 5. Frontend (frontend-clinic)

| Pieza | Detalle |
|---|---|
| `lib/ejeCromosoma.ts` (nuevo) | `ejeDe(contour)` → `{angulo, largo, ancho, centro}` o `null`; `giroParaEnderezar(eje)`, con el umbral de 1,2 de D2. Cobertura total. |
| `lib/presentacionCariograma.ts` | `Orientacion` gana `ajuste`; `orientacionDe` lo lee (0 por defecto); `colocarEnLineaBase` y `escalaComun` usan las dimensiones enderezadas cuando hay eje; `transformacionImagen` suma el giro automático y el ajuste; `marcoVisible` usa las dimensiones giradas. |
| `KaryotypeCanvas.tsx` | `Group` con `clipFunc` por silueta (D1); `data-orientacion` incluye el giro final, para el E2E. |
| `ChromosomePropertiesPanel.tsx` | «−5°», «+5°» y «Restablecer» junto a «Girar 180°» y «Voltear»; se ve el ángulo final. |
| `karyotypeClient.ts` / `handlers.ts` (MSW) | `ajuste` en la petición de `orient`. |
| `KaryoImageToolbar.tsx` | Textos de D5 y el aviso con selección. |

## 6. Fuera de alcance, declarado

- **Enderezar cromosomas curvados** (llevar la línea media a una recta, como hacen
  algunos sistemas comerciales). Aquí el cromosoma se gira entero; uno curvado
  queda vertical, pero curvado.
- **Orientación automática ISCN** (qué extremo es p): sigue siendo manual, con
  «Girar 180°».
- **Girar sobre la metafase**: allí la orientación es la de la foto y no se toca.
- **Arrastrar para girar** (asa de rotación con el ratón): los botones bastan para
  ajustar y se prueban de forma determinista. Se puede añadir después.

## 7. Pruebas (RN-09 ≥ 90 %)

| Capa | Qué se prueba |
|---|---|
| `ejeCromosoma.ts` (puras) | Rectángulo 10 × 100 a 0°, 30°, 90° y −45° **en los dos sentidos de recorrido** (la trampa de §1.2); casi redondo → no se endereza; menos de 3 puntos o área nula → `null`; largo y ancho proyectados frente a los esperados |
| `presentacionCariograma.ts` | Escala común y línea base con dimensiones enderezadas; ajuste guardado sin `ajuste` → 0; suma de automático + ajuste + 180 + volteo; marco girado dentro del hueco |
| Backend | `ajuste` válido → se guarda y el evento lleva `previa` y `nueva` · sin `ajuste` se conserva el anterior · −91, 91, 2.5, `true` y `"5"` → 400 sin evento · caso bloqueado 409 · analista ajeno 403 · objeto inactivo rechazado |
| Contrato (CI) | Drift verde con `openapi.json` regenerado; **oasdiff sin rupturas** frente a la base |
| Componentes | Los botones envían el ajuste correcto; «Restablecer» envía 0; no aparecen sin metafase o con el caso no editable; la barra muestra «Rotar vista» y el aviso con selección |
| E2E real (Chromium, muestra propia con `metafase_1.bmp`) | **Reproducir antes el defecto**: un cromosoma con silueta inclinada más de 20° se pinta hoy con giro 0 o 90 · tras el cambio, su giro final lo deja vertical (±2°) · «+5°» dos veces → +10° y dos eventos `ORIENT` en la auditoría · «Rotar vista» no cambia el `data-orientacion` de ningún cromosoma |

**Mutaciones obligatorias**, cada una rompiendo el código a propósito y con una prueba
que lo detecte:

- quitar la corrección de signo;
- enderezar los casi redondos;
- recortar por la caja en vez de por la silueta;
- resetear `ajuste` cuando no llega;
- aceptar `ajuste` booleano;
- dejar la escala común con las dimensiones de la caja.

## 8. Plan

| # | Tarea | Estimación |
|---|---|---|
| T1 | `lib/ejeCromosoma.ts` y sus pruebas, con los dos sentidos de recorrido | 2 h |
| T2 | Recorte por silueta (D1) y enderezado automático en el cariograma (D2): `presentacionCariograma.ts` y `KaryotypeCanvas.tsx` | 3 h |
| T3 | `ajuste` en backend-clinic: servicio, serializador, contrato, `openapi.json` regenerado y pruebas | 2 h |
| T4 | Botones −5° / +5° / Restablecer, cliente, MSW y pruebas de componente | 2 h |
| T5 | «Rotar vista» y el aviso en la barra (D5) | 0,5 h |
| T6 | E2E que reproduce el defecto, mutaciones, captura antes y después, CI (drift y oasdiff) y §11 Verificación | 2,5 h |

Total: unas 12 h. T1 → T2 son la mejora que ve el autor; T3 → T4 el ajuste fino; T5
se puede hacer en cualquier momento.

## 9. Preguntas abiertas para el autor

1. **Paso del ajuste fino: 5° o 15°.** Se propone 5°: lo grueso lo hace el
   enderezado automático, y a mano solo se corrige poco.
2. **¿El enderezado automático, siempre o con un interruptor?** Se propone siempre,
   sin interruptor: «Restablecer» deja solo lo automático, y el ajuste lo corrige
   cuando no acierta.
3. **El recorte por silueta cambia también lo que se ve de los cromosomas que no se
   giran:** desaparecen los trozos de vecinos dentro de su caja. Si la silueta está
   mal (sub-segmentación), se verá recortada. ¿Se acepta? La alternativa es recortar
   por silueta solo los que se enderezan.
4. **Umbral de «casi redondo»: 1,2.** Se puede afinar después con la medición de
   §1.2 sobre más metafases.

## 10. Respuestas (aprobación del 2026-10-28)

El autor aprobó la especificación al pedir que se empezara por T1 («empieza por la
tarea 1»), sin cambiar nada de §9. Quedan las respuestas propuestas:

1. Ajuste fino de **5°**.
2. Enderezado automático **siempre**, sin interruptor; «Restablecer» deja solo lo
   automático.
3. Recorte por silueta en **todos** los cromosomas con silueta.
4. Umbral de casi redondo **1,2**.

## 11. Avance

| # | Estado |
|---|---|
| T1 | **Hecha 28/10.** `lib/ejeCromosoma.ts`, 27 pruebas, **100 %** de líneas y ramas. Cada caso se recorre en los dos sentidos. Mutaciones: sin corregir el signo fallan 7 pruebas; enderezando los casi redondos falla 1. Contrastada con `scripts/medir_ejes_cromosomas.py` sobre las 38 siluetas reales de `metafase_1`: mismas cifras (27 / 21 / 11 inclinadas; largo frente a la caja 1,01 de mediana, 1,23 de máximo). Con el umbral de 1,2, **2 de las 38** quedan como casi redondas y no se enderezan. |
| T2 | **Hecha 29/10.** Cada cromosoma con silueta se pinta dentro de un `Group` de Konva que recorta por ella (`clipFunc`) y lo gira hasta dejarlo de pie. La colocación sale de la caja de la silueta **ya girada**, así que vale para cualquier ángulo y T4 solo tiene que sumar el ajuste. La escala común usa lo que miden de pie. Sin silueta, el recorte de su caja, como antes (RN-07). Pruebas: 34 de geometría y 18 de componente; `ejeCromosoma.ts` y `presentacionCariograma.ts` al 100 %, y el código nuevo de `KaryotypeCanvas.tsx` cubierto entero (lo que queda sin cubrir es la medición y el arrastre del lienzo, como antes). Suite del frontend: 621 verdes. E2E `cariograma-enderezado.spec.ts` sobre una muestra propia con `metafase_1`: un 10 inclinado 59° en la metafase queda a **26,5°** con el código anterior (el test **falla**) y a **1,7°** con T2 (pasa). Capturas en `capturas/dd-karyo-008/` (`antes.png`, `despues.png`). |
| T3 | **Hecha 29/10.** `orient_chromosome(…, ajuste=None)`: entero −90..90; sin él se conserva el guardado; 400 y ningún evento con −91, 91, 2,5, 5,0, `true`, `false`, `"5"` o `[5]`. La vista lo pasa desde `request.data`. Contrato: `ajuste` es una propiedad **opcional** de la petición `Orientar` (no entra en `required`), con `openapi.json` regenerado (+6/−1). 22 pruebas nuevas, que fallaban antes de implementar. Suite de backend-clinic: **1134 verdes, cobertura del 90,85 %**. Mutaciones: borrar el ajuste cuando no llega hace fallar 2; aceptar un booleano hace fallar 3. **oasdiff no se pudo ejecutar en local** (Docker Desktop apagado): lo comprueba el CI en el PR. |
| T4 | **Hecha 29/10.** «↺ −5°», el valor («Ajuste +10°») y «↻ +5°» en una fila del panel, con «Restablecer» debajo. Se apagan en los topes (±90) y «Restablecer» se apaga cuando el ajuste ya es 0. «Girar 180°» y «Voltear» conservan el ajuste. El ajuste guardado se suma al enderezado al pintar. El doble MSW valida como el backend. Pruebas: 5 de geometría, 6 de panel y 1 de página (+5° dos veces → giro final de 330 a 340, girar 180° lo conserva, 3 entradas en la bitácora). Mutaciones, las cuatro detectadas: no sumar el ajuste al pintar (fallan 3), quitar el tope (falla 1), «+5°» con el signo cambiado (fallan 2) y que «Girar» pierda el ajuste (fallan 2). E2E en Chromium sobre la misma muestra propia: con +10° el cromosoma queda a **8,4°** en los píxeles, y la auditoría tiene dos `ORIENT` con el ajuste 0→5 y 5→10. Captura: `capturas/dd-karyo-008/panel-ajuste.png`. Suite E2E completa: **20 de 20**. |
| T5 | **Hecha 29/10.** ↺ ↻ se llaman «Rotar vista a la izquierda / a la derecha» (`aria-label`), y su `title` dice que giran todo el lienzo. Con un cromosoma seleccionado, la barra muestra «↺ ↻ giran toda la vista; el cromosoma se gira en su panel». El comportamiento no cambia. 2 pruebas de componente; el E2E `cariograma-enderezado` comprueba que el aviso se ve al seleccionar. Captura: `capturas/dd-karyo-008/barra-rotar-vista.png`. Al pasar las pruebas de página falló de forma intermitente `sampleListPage` (filtro VALIDATED); sola pasó dos veces seguidas, así que es la misma inestabilidad con la CPU cargada de §11.3. |
| T6 | Pendiente. |

### 11.3 Decisiones tomadas al implementar T4

1. **El ajuste fino solo aparece si el cromosoma tiene silueta.** Sin ella se pinta el recorte de su caja, que solo sabe girar 0°, 90° o 180°: un ajuste de 5° no se vería o se saldría del hueco. «Girar 180°» y «Voltear» siguen apareciendo siempre.
2. **El cliente envía siempre `ajuste`.** El backend admite omitirlo (D4, para clientes antiguos), pero el panel conoce la orientación entera. Enviarla completa evita depender de que el servidor la conserve, y la rama «sin ajuste» del cliente habría sido código muerto.
3. **La suite del frontend falló una vez con 632 de 633 y en la siguiente pasaron las 633.** No se sabe qué prueba fue, porque la salida estaba filtrada. Coincide con los fallos intermitentes que ya dieron `sampleRegisterPage` y `toolQueryPage` con la CPU cargada. Queda como inestabilidad conocida, no como resuelta.
4. **Apagar el stack con `TaskStop` deja vivos los procesos `node` de Vite** y los puertos 5173 y 5174 ocupados. Al relanzarlos con `--strictPort` fallan. Para apagarlo del todo hay que cerrar esos procesos por su PID.

### 11.1 Decisiones tomadas al implementar T2

1. **`data-orientacion` no cambia.** La spec (§5) decía que incluiría el giro final, pero las pruebas de D7 lo leen tal cual. El giro final va en un atributo aparte, `data-giro-final`, en el grupo de la silueta.
2. **Voltear invierte el signo del giro.** Voltear en pantalla una imagen girada r es reflejarla y girarla −r (M·R(r) = R(−r)·M), porque Konva escala antes de girar. La prueba que lo protege aplica a los puntos la transformación de Konva escrita aparte, no la del código.
3. **Una mutación sobrevivió a la primera tanda de pruebas.** «Escala común con las cajas» pasaba, porque la prueba tenía nueve cromosomas verticales y uno solo en diagonal, y el percentil 90 lo marcaban los verticales. Se añadió una prueba con todos en diagonal: con las cajas la escala sería 0,28, y de pie es 1.
4. **El primer E2E daba «de pie» antes y después del cambio: falló el medidor, no el sistema.** Lo que Konva no pinta es transparente y se lee (0, 0, 0, 0), gris y negro. El medidor contaba el hueco vacío, un rectángulo vertical: 2.496 «píxeles oscuros» para una mancha de unos 10 px. Ahora exige opacidad, y solo entonces el test falla con el código anterior.
5. **`metafase-corte.spec.ts` fallaba, y no por T2** (fallaba igual con el código anterior). Pulsaba el centro del objeto mayor sin desplazar la página. Con `metafase_1`, que es la que ahora devuelve `metafaseReal` porque las muestras de la demo la usan, ese centro caía en y = 802 con una ventana de 720. Ahora desplaza la página antes de medir dónde está el lienzo (sin la rueda, que hace zoom). Suite E2E completa: 19 de 20; corregido, `metafase-corte` pasa solo.

### 11.2 Decisiones tomadas al implementar T3

1. **`ajuste` se guarda siempre, también cuando vale 0.** Así `measures.orientacion` tiene un solo formato, `{giro, volteo, ajuste}`. Una orientación antigua sin él se lee como 0, también en el `previa` del evento. Las pruebas de D7 que esperaban `{giro, volteo}` ahora esperan también `ajuste: 0`. El cliente no se ve afectado: `orientacionDe` ignora las claves que no conoce.
2. **No se exige que sea múltiplo de 5.** Los botones de T4 van de 5 en 5, pero la API acepta cualquier entero del rango. El paso es cosa de la interfaz.
