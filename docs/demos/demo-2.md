# Demo 2 (release 8.2.0) — Grupo BIOMED UMSS

| Campo | Valor |
|---|---|
| **Demo** | 2 · lunes 26 de octubre de 2026 |
| **Release** | `release/8.2.0` |
| **Repositorio** | https://github.com/guillemc92/karyoumss |
| **Integrantes** | 1 (grupo individual) |
| **Canal oficial** | Classroom (este archivo es la copia del repositorio) |

## Integrantes y funcionalidades

| Integrante | Funcionalidad | Tamaño | Caso de uso (FSD) | Diseño | Repositorio |
|---|---|---|---|---|---|
| Guillermo Mamani Chambi ([`guillemc92`](https://github.com/guillemc92)) | 1 · Corrección manual de la segmentación sobre la metafase | Grande | FSD-UC-003 (XAI y corrección manual) | [DD-KARYO-007](../design/DD-KARYO-007.md) | https://github.com/guillemc92/karyoumss |
| Guillermo Mamani Chambi | 2 · Contrato OpenAPI generado desde el código y validado en CI | Mediana | Transversal (la API de FSD-UC-003 queda en el contrato) | [DD-API-001](../design/DD-API-001.md) | https://github.com/guillemc92/karyoumss |

## Funcionalidad 1 — Corrección manual de la segmentación sobre la metafase

**Caso de uso:** FSD-UC-003. **Antes:** «separar» partía la caja por la mitad, «unir»
unía cajas y la metafase solo se veía al recortar.

**Criterios de aceptación** (cada uno con su prueba E2E en Chromium contra el stack real):

1. **La metafase es el lienzo principal.**
   - Se ve con la silueta de cada cromosoma, coloreada por su semáforo.
   - Seleccionar un cromosoma aquí o en el cariograma es lo mismo.
   - Prueba: `tests/auditado/metafase-editor.spec.ts`.
2. **Añadir un cromosoma que la IA no vio.**
   - Se dibuja su caja y lo clasifica el modelo.
   - Si la IA no responde, el analista elige la clase y no se inventa ninguna.
   - Prueba: `metafase-objetos.spec.ts`.
3. **Descartar lo que no es un cromosoma.**
   - Se elige un motivo: núcleo, suciedad, duplicado u otro.
   - Es un borrado suave que queda en la auditoría (RN-05).
   - Prueba: `metafase-objetos.spec.ts`.
4. **Separar trazando una línea.**
   - backend-ml corta en ráster y cada trozo se reclasifica.
   - Una línea que no atraviesa el objeto no se envía y se dice por qué.
   - Prueba: `metafase-corte.spec.ts`.
5. **Deshacer la última edición propia.**
   - Es un evento que compensa al anterior; no borra nada.
   - El cromosoma queda idéntico al de antes.
   - Prueba: `metafase-corte.spec.ts`.
6. **El cariograma se lee.**
   - Todos los cromosomas a la misma escala, apoyados en la línea base.
   - Se pueden girar 180° y voltear.
   - Prueba: `metafase-flujo-completo.spec.ts`, con la auditoría en orden.

**Endpoints en el contrato** (`backend-clinic/openapi.json`, etiquetas «Cariotipo» y «Corrección manual»):

| Método y ruta | Qué hace |
|---|---|
| `GET /api/clinic/samples/{id}/karyotype/` | El cariotipo, con la silueta de cada cromosoma |
| `GET /api/clinic/samples/{id}/karyotype/metaphase/` | La imagen de la metafase |
| `POST /api/clinic/samples/{id}/karyotype/contours/` | Completa las siluetas que faltan |
| `POST /api/clinic/samples/{id}/karyotype/objects/` | Añadir (ADD_OBJECT) |
| `POST /api/clinic/samples/{id}/chromosomes/{cid}/reject/` | Descartar (REJECT_OBJECT) |
| `POST /api/clinic/samples/{id}/chromosomes/{cid}/split/` | Separar por una línea (SPLIT) |
| `POST /api/clinic/samples/{id}/chromosomes/{cid}/join/` | Unir (JOIN) |
| `POST /api/clinic/samples/{id}/chromosomes/{cid}/recrop/` | Recortar (RECROP) |
| `POST /api/clinic/samples/{id}/chromosomes/{cid}/orient/` | Girar / voltear (ORIENT) |
| `GET`, `POST /api/clinic/samples/{id}/karyotype/undo/` | Qué se desharía / deshacer (UNDO_EDIT) |

El corte y la unión los calcula backend-ml: `POST /api/v1/split/`, `/api/v1/join/` y
`/api/v1/contours/` en `backend-ml/openapi.json`.

**Evidencia:** commits `52361da`, `3eab8f1`, `548b1aa`, `0588f56`, `0bcd982`, `cc7a0b4` y `518337b`.

## Funcionalidad 2 — Contrato OpenAPI generado desde el código y validado en CI

**Criterios de aceptación:**

1. **El contrato sale del código**, con un comando por servicio:
   - backend-clinic: `python manage.py spectacular --format openapi-json --file openapi.json --validate`, con drf-spectacular;
   - backend-ml: `python -m app.exportar_openapi`, con FastAPI y sus modelos Pydantic.

   Los dos archivos están en el repositorio, y exportar dos veces da el mismo archivo.
2. **Incluye todos los endpoints de la funcionalidad 1** (tabla de arriba), con su cuerpo
   de entrada y cada código de error. Los demás endpoints aparecen con la etiqueta
   «Sin describir»: es deuda declarada en DD-API-001 D2.
3. **`.github/workflows/contrato-openapi.yml` se ejecuta en cada pull request y en cada
   push a `release/**`.** Para cada servicio comprueba:
   - **drift:** el archivo es el que genera el código;
   - **Spectral:** 0 errores;
   - **oasdiff:** que no haya cambios incompatibles con la rama base;
   - **Schemathesis**, solo en backend-ml: la API viva responde lo que dice su contrato.

**Pregunta fija de la demo, «Rompe tu contrato y muestra qué detecta el CI»:** el guion
está abajo.

## Guion — romper el contrato en vivo

1. **Abrir el PR de demostración**, que quita `contour` del `ChromosomeSerializer` sin
   regenerar el contrato. **El CI falla en el drift**: el código ya no produce el archivo
   del repositorio.
2. **Regenerar el contrato en ese PR.** El drift pasa, pero **oasdiff marca un cambio
   incompatible**: la respuesta pierde la propiedad `contour`, que el frontend usa para
   pintar la metafase.
3. **Volver atrás**: el CI queda en verde.

Los dos estados del CI quedan enlazados en `8.2.0-aportes.md`, por si la red falla en vivo.
