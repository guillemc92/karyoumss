# E3 · Hipótesis

> Se escriben **antes de la primera corrida** y se suben a git en un commit
> propio, para que quede la fecha. Después de medir no se cambian: si el
> resultado refuta una, se dice en [`INFORME.md`](INFORME.md).

- **Grupo:** G04 (individual), Guillermo Mamani Chambi
- **Módulo que se compara:** la bitácora de auditoría de `backend-clinic`
  (`clinic_audit_events`, ADR-0022). El diseño está en
  [`docs/design/DD-E3-001.md`](../../docs/design/DD-E3-001.md).
- **Ruta que lo usa:** `GET /api/clinic/samples/{id}/audit/`
- **Ruta que no lo usa (control):** `GET /api/clinic/samples/{id}/`
- **Fecha y commit en que se escriben:** 2026-11-02. Es el commit que añade
  este archivo: aún no hay código del experimento ni ninguna medición.

**Cómo se lee cada fila:**
- **«Sin falla»** es la fase *antes* de la corrida.
- **«Falla»** son los 10 s en que Toxiproxy rompe la conexión.
- **Cada cifra es la mediana de 5 corridas o más.**

**Las dos formas:**
- **En proceso:** la API lee la bitácora de su propia base.
- **Extraída:** la API llama a la bitácora por HTTP, a través de Toxiproxy, con
  las siguientes protecciones:
  - plazo de 300 ms por intento;
  - 2 intentos;
  - *circuit breaker*;
  - plazo total de 800 ms.

| # | Qué se compara (forma, ruta, fase) | Qué esperamos y cuánto | Por qué (mecanismo) | Qué número la refuta |
|---|---|---|---|---|
| H1 | p95 de `…/audit/`, sin falla: extraída frente a en proceso | Extraer lo sube **20 ms o menos** | Se suman un salto por Toxiproxy y una petición HTTP con el JSON serializado dos veces. La consulta a SQLite es la misma en las dos formas, porque las dos bases salen del mismo seed | Una subida de la mediana **> 20 ms** |
| H2 | La ruta de control, en todas las fases, comparada entre formas | Su p95 cambia **10 % o menos** y da **0 % de errores** también durante la falla | No llama a la bitácora; si la falla la alcanza, es que algo la arrastró: hilos de gunicorn ocupados esperando a la bitácora | **Un solo error** en control durante la falla, o un p95 que cambia **> 10 %** |
| H3 | p95 de `…/audit/` durante la falla `colgado`, forma extraída | **900 ms o menos**: ninguna petición espera más que el plazo total | 800 ms de plazo total, más el margen del servidor; con el breaker abierto, se responde `503` sin esperar | Un p95 **> 900 ms** durante la falla |
| H4 | % de errores de `…/audit/` en la fase *después*, forma extraída, las tres fallas | **1 % o menos** | El breaker se vuelve a cerrar a los 2 s de quitar la falla, y la fase *después* dura 10 s | **> 1 %** de errores después |
| H5 | `up -d --wait` y `build`: extraída frente a en proceso | `up` tarda **5 s o más** de más; `build` difiere **10 % o menos** | La forma extraída arranca un Django más, con sus migraciones y su healthcheck. La imagen es la misma | Una diferencia de `up` **< 5 s**, o un `build` que difiere **> 10 %** |

**Lo que estas hipótesis NO cubren** (D2 del diseño): en las dos formas se
mide **solo la lectura**. Escribir eventos por la red, con la transacción
clínica y la cadena de hashes de por medio, no se mide. Se argumenta en el
ADR.
