# E3 · Informe: ¿conviene extraer la bitácora de auditoría?

> Las hipótesis están en [`HIPOTESIS.md`](HIPOTESIS.md), commiteadas antes de
> medir (`3526e3e`). La decisión está en
> [`docs/adr/0038-no-extraer-bitacora-auditoria.md`](../../docs/adr/0038-no-extraer-bitacora-auditoria.md).
> El diseño está en [`DD-E3-001`](../../docs/design/DD-E3-001.md).

## Qué se comparó

- **Módulo:** la bitácora de auditoría de `backend-clinic` (`clinic_audit_events`,
  ADR-0022): append-only, con una cadena de hashes por caso.
- **Forma 1, en proceso (monolito modular):** `BitacoraEnProceso`. La API lee
  la tabla de su propia base. Es como funciona hoy en producción.
- **Forma 2, extraída:** `BitacoraHttp`. La API llama por HTTP a un servicio
  aparte (la misma imagen, con `settings_bitacora`) a través de Toxiproxy.
  - **Protecciones:** plazo de 300 ms por intento, 2 intentos con *jitter* de
    hasta 50 ms y plazo total de 800 ms.
  - **Breaker:** se abre tras 3 fallos seguidos y queda abierto 2 s.
  - **Alcance:** cada proceso de gunicorn tiene su propio breaker.
- **Ruta que usa el módulo:** `GET /api/clinic/samples/{id}/audit/`. En las
  tablas se llama `bitacora`.
- **Ruta de control, que no lo usa:** `GET /api/clinic/samples/{id}/`. En las
  tablas se llama `control`.
- **Fallas provocadas en la forma extraída:**
  - `colgado`: *toxic* `timeout` hacia la bitácora;
  - `caido`: proxy deshabilitado;
  - `lento`: +1.000 ms de latencia.

  Duran del segundo 10 al 20 de la parte medida. La forma en proceso no tiene
  red que romper: se mide sin falla y sirve de línea base.
- **Carga:** 10 pet/s **por ruta**, a ritmo fijo (modelo abierto). Hay 10 s de
  calentamiento que no se cuentan y después 30 s medidos: *antes*, *falla* y
  *después*, de 10 s cada una.

**Por qué 10 pet/s y no 50 como en la plantilla.** Es una decisión medida
([`resultados/piloto/`](resultados/piloto/)): a 20 pet/s por ruta, la forma en
proceso ya se satura y da un p95 de 350 a 920 ms sin ninguna falla. Medir un
servidor saturado mide la cola, no la extracción.

## Entorno

- **Máquina:** Intel Core i5-3317U a 1,70 GHz, con 2 núcleos y 4 hilos. 15,9 GB
  de RAM, de los que 7,7 GB son para Docker. Windows 10 Pro.
- **Docker:** Docker Desktop, motor 29.1.3, Compose 2.40.3. WSL 3.0.1.0, con
  kernel 6.18.40.1-1.
- **Imágenes:**
  - la de la aplicación es `python:3.12.7-slim`, multietapa y sin root, con
    Django 5.0.6, DRF 3.15.2 y gunicorn 23.0.0 (2 procesos `gthread` × 4
    hilos), igual en las dos formas;
  - Toxiproxy 2.13.0 y k6 2.3.0, fijadas por *digest*.
- **Base de datos:** SQLite en volúmenes con nombre.
- **Datos:** [`sembrar_bench --semilla 42`](../../backend-clinic/apps/samples/management/commands/sembrar_bench.py)
  carga 1.000 casos, 46.000 cromosomas y unos 14.000 eventos (de 3 a 70 por
  caso, con una media de unos 14).
  - **La forma imita la base de demo:** 434 eventos en 32 casos, media 13,6 y
    máximo 70.
  - **Es determinista:** los ids, el número de eventos, sus tipos y sus
    payloads salen iguales con la misma semilla. No hay PII.
  - **Las dos bases tienen los mismos datos:** un solo trabajo de seed carga la
    base de la API y la copia a la de la bitácora.
  - **k6 pide ids que existen:** los lee del `ids.json` que deja el seed.

## Método

- **Corridas:** 5 por combinación. Son 4 combinaciones: en proceso sin falla y
  extraída con cada una de las tres fallas. En total, 20 corridas.
- **Entre corridas:** `docker compose down -v`, secretos nuevos al azar y seed
  desde cero.
- **Orden:** las vueltas alternan las formas (proceso, colgado, caído, lento,
  proceso…), para que la deriva de la máquina caiga sobre todas.
- **Datos crudos:**
  - los resúmenes de k6 están en `resultados/<forma>-<falla>-<n>.json`;
  - los tiempos de seed, `up` y build, en `resultados/tiempos.csv`;
  - el registro, en `resultados/corridas.log`.
- **Tablas:** `py -3 bench/e3/resumir.py` las vuelve a generar.

## Resultados

Cada celda es la mediana de las 5 corridas y, entre paréntesis, el rango
(mínimo–máximo).

| Forma | Falla | Ruta | Fase | p95 (ms) | % errores |
|---|---|---|---|---:|---:|
| En proceso | ninguna | bitacora | antes | 179,5 (100,1–255,1) | 0,0 (0,0–0,0) |
| En proceso | ninguna | bitacora | falla | 95,6 (91,2–114,5) | 0,0 (0,0–0,0) |
| En proceso | ninguna | bitacora | despues | 89,8 (74,1–152,5) | 0,0 (0,0–0,0) |
| En proceso | ninguna | control | antes | 72,6 (44,2–144,8) | 0,0 (0,0–0,0) |
| En proceso | ninguna | control | falla | 53,7 (43,6–60,0) | 0,0 (0,0–0,0) |
| En proceso | ninguna | control | despues | 47,8 (45,0–74,9) | 0,0 (0,0–0,0) |
| Extraída | colgado | bitacora | antes | 272,1 (187,2–1385,4) | 1,0 (0,0–9,0) |
| Extraída | colgado | bitacora | falla | 757,0 (722,3–1032,3) | 99,0 (99,0–100,0) |
| Extraída | colgado | bitacora | despues | 166,7 (91,6–836,4) | 10,9 (7,0–24,8) |
| Extraída | colgado | control | antes | 78,8 (74,4–775,3) | 0,0 (0,0–0,0) |
| Extraída | colgado | control | falla | 176,8 (59,4–539,8) | 0,0 (0,0–0,0) |
| Extraída | colgado | control | despues | 72,4 (52,7–427,9) | 0,0 (0,0–0,0) |
| Extraída | caido | bitacora | antes | 194,1 (144,7–1120,3) | 1,0 (0,0–6,0) |
| Extraída | caido | bitacora | falla | 217,1 (135,7–1262,7) | 100,0 (100,0–100,0) |
| Extraída | caido | bitacora | despues | 220,3 (114,8–820,0) | 12,0 (9,1–14,9) |
| Extraída | caido | control | antes | 83,7 (55,3–279,1) | 0,0 (0,0–0,0) |
| Extraída | caido | control | falla | 144,9 (72,8–945,2) | 0,0 (0,0–0,0) |
| Extraída | caido | control | despues | 71,7 (55,9–580,0) | 0,0 (0,0–0,0) |
| Extraída | lento | bitacora | antes | 169,9 (139,1–351,3) | 1,0 (0,0–1,0) |
| Extraída | lento | bitacora | falla | 754,2 (701,4–913,0) | 99,0 (98,0–100,0) |
| Extraída | lento | bitacora | despues | 171,5 (105,2–452,7) | 13,0 (1,0–17,2) |
| Extraída | lento | control | antes | 70,7 (52,4–154,0) | 0,0 (0,0–0,0) |
| Extraída | lento | control | falla | 152,4 (78,0–561,1) | 0,0 (0,0–0,0) |
| Extraída | lento | control | despues | 77,7 (53,8–164,0) | 0,0 (0,0–0,0) |

**Cómo leer la fase *falla* de la bitácora extraída:**
- **Los errores son `503 AUDIT_UNAVAILABLE`**, la respuesta prevista, no
  caídas de la API.
- **La mediana (p50) es de unos 55 ms** con colgado y lento: casi todas las
  peticiones las rechaza enseguida el breaker abierto.
- **El p95 de unos 750 ms** son las que esperan el plazo entero: las de antes
  de que el breaker se abra y las de prueba en estado semiabierto.

### Recuperación

En la fase *después*, la bitácora extraída da entre **11 y 13 % de errores**
(mediana por falla). Con 10 pet/s durante 10 s, eso equivale a unos **1,1–1,3 s
de 503** después de quitar la falla.
- **Encaja con el breaker:** queda abierto 2 s y, al reabrir, solo deja pasar
  una llamada de prueba.
- **Hay dos breakers:** uno por proceso de gunicorn, y cada uno tiene que
  cerrarse por su cuenta.

No se midió el instante exacto en que vuelve a 0 %, solo el total de la fase.

### Tiempos de seed, arranque y build

| Qué | En proceso | Extraída |
|---|---:|---:|
| seed (s) | 92,5 (86,4–96,6), n=5 | 89,9 (81,5–97,2), n=15 |
| `up -d --wait` (s) | 5,6 (5,3–6,7), n=5 | 11,8 (10,9–17,8), n=15 |
| `build --no-cache` (s) | 110,6 (107,6–127,4), n=5 | 110,2 (109,6–123,1), n=5 |

El seed es el mismo trabajo en las dos formas: se cuenta aparte del `up`.

### El salto del proxy (sin falla, fase *antes*)

| | En proceso | Extraída (15 corridas) |
|---|---:|---:|
| p95 de `bitacora` | 179,5 ms | 194,1 ms (+14,6) |
| p50 de `bitacora` | 44 ms (41,7–47,8) | 57 ms (50,1–249,2) |
| % errores de `bitacora` | 0 % en las 5 corridas | 0–9 %, con 1 % de mediana; 10 de 15 corridas con algún error |

## Hipótesis: ¿se cumplieron?

| # | Hipótesis | Resultado | ¿Se cumple? |
|---|---|---|---|
| H1 | Sin falla, extraer sube el p95 de `…/audit/` en ≤ 20 ms | +14,6 ms (179,5 → 194,1); el p50 sube +13 ms | **Sí**, pero el rango de cada forma (100–255 ms en proceso) es mucho mayor que la diferencia: el efecto existe, aunque cabe dentro del ruido |
| H2 | Control: p95 ±10 % entre formas y 0 % de errores durante cualquier falla | 0 % de errores, sí. Pero su p95 durante la falla sube de 53,7 ms a 145–177 ms (×2,7–3,3). Su p50 no se mueve (≈ 30 ms) | **No**: la falla no tumba la ruta de control, pero sí le alarga la cola |
| H3 | Con `colgado`, p95 de `…/audit/` ≤ 900 ms durante la falla | 757 ms (722–1.032) | **Sí** por la mediana; 1 de 5 corridas pasa de 900 |
| H4 | Después de la falla, ≤ 1 % de errores en `…/audit/` | 10,9 / 12,0 / 13,0 % | **No**: el breaker tarda en cerrarse, como se explica en «Recuperación» |
| H5 | `up` ≥ 5 s más lento en la forma extraída; `build` ±10 % | `up` +6,2 s (5,6 → 11,8); build 110,6 → 110,2 s (−0,4 %) | **Sí**, en las dos partes |

**Un resultado que ninguna hipótesis preveía:** sin ninguna falla, la forma
extraída **ya da errores**. Hubo algún 503 en 10 de las 15 corridas, con hasta
un 9 % en la fase *antes*. Lo que ocurre es que, con la máquina cargada y la
caché fría, la bitácora tarda más de 300 ms en responder. Entonces se agota el
plazo por intento: es el coste de las protecciones mismas. En proceso no hay
plazo que vencer y dio 0 errores en las 5 corridas.

## Amenazas a la validez

1. **Todo en una máquina, y modesta.** La API, la bitácora, Toxiproxy y k6
   comparten 2 núcleos físicos.
   - **Qué afecta:** lo que se ve en la ruta de control durante la falla puede
     ser contención de CPU y no solo hilos ocupados esperando a la bitácora.
     Con estos datos no se separan las dos causas.
   - **Qué se hizo:** bajar la carga a 10 pet/s, que la forma en proceso
     atiende sin saturarse.
   - **Qué no se hizo:** cerrar VS Code y Docker Desktop, que también estaban
     abiertos.
2. **Toxiproxy añade un salto** también en la forma sana. El +14,6 ms de la H1
   incluye ese salto, no solo la red de Docker.
3. **Docker Desktop sobre WSL2.** El arranque y el build dependen de la máquina
   virtual y del disco virtual.
4. **El calentamiento no basta.** En la fase *antes*, la forma en proceso tiene
   un p95 de 179,5 ms; en *falla* y *después*, que en proceso no tienen
   ninguna falla, baja a unos 90 ms.
   - **Qué pasa:** con 1.000 casos, la caché de SQLite y la de Python siguen
     frías pasados los 10 s.
   - **Qué afecta:** esto afecta a las dos formas por igual. Pero ensancha el
     rango de la H1 y explica parte de los errores de la extraída en *antes*.
5. **La falla provocada no es la real.** Las de Toxiproxy son limpias y
   empiezan en un instante preciso. Una caída real suele ser una lentitud
   parcial que va y viene, y eso castigaría más al breaker.
6. **Solo se midió la lectura** (DD-E3-001 D2).
   - **Qué lee la forma extraída:** una copia sembrada de la base, sin
     sincronizar.
   - **Lo que no se midió:** el coste de escribir eventos por la red y de
     mantener la cadena de hashes entre dos bases. Es lo más caro de extraer
     y se argumenta en el ADR, sin cifra.
7. **SQLite y no Postgres.** Con Postgres, la consulta de la bitácora y su
   comportamiento con varios hilos cambiarían. La comparación entre formas
   sigue siendo justa, porque la base es la misma en las dos.
8. **Un breaker por proceso.** Con 2 procesos de gunicorn hay dos breakers
   independientes. Es parte del diseño medido, no un defecto del banco, pero
   alarga la recuperación (H4).

## Conclusión

**Extraer la bitácora no compensa con estos números.**
- **Sin fallas,** la lectura sana cuesta poco más, unos 14 ms. Pero ya trae
  errores que antes no había.
- **Con fallas,** las protecciones hacen su trabajo: la API no se cae y
  responde 503 a tiempo. Pero la bitácora queda sin servicio más de 1 s después
  de cada falla, y la cola de la ruta de control se alarga ×3.
- **Lo que se ganaría** es aislar la tabla, y eso no se mide en este banco.
- **Lo que costaría más** es extraer la escritura, que tampoco se midió y rompe
  la atomicidad con la acción clínica.

La decisión y la condición para revertirla están en el ADR-0038.
