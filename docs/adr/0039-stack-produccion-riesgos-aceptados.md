---
id: ADR-0039
title: Stack de producción en un compose — lo que Trivy no deja en cero y por qué se acepta
date: 2026-11-04
status: accepted
related: [ADR-0012, ADR-0013, ADR-0020, ADR-0024]
---

# ADR-0039: Stack de producción en un compose y sus riesgos aceptados

- **Autores:** Ing. Guillermo Mamani Chambi (G04), con Claude
- **Origen:** Demo 3 de M8, «Imagen y stack de producción»
- **Diseño:** [DD-OPS-001](../design/DD-OPS-001.md), aprobado el 2026-11-04
- **Aceptado:** 2026-11-04, por el autor al aprobar DD-OPS-001

## Contexto

La consigna pide un Dockerfile multi-stage por servicio y un `compose.yaml` que
levante todo con `docker compose up -d --wait` desde un clon limpio. Las imágenes
deben revisarse con hadolint y Trivy, **sin hallazgos altos ni críticos sin
justificar**.

**La primera pasada de Trivy** (2026-11-04, Trivy 0.75.0) encontró HIGH y CRITICAL en
las cuatro imágenes:

| Origen | Qué | Cómo se resolvió |
|---|---|---|
| Librerías | Django 5.0.6, una rama sin soporte, con 2 CRITICAL | **Actualizado** a 5.2.18 LTS |
| Librerías | DRF 3.15.2, simplejwt 5.3.1, PyJWT 2.9.0, Pillow 12.3.0, cryptography 43/49 | **Actualizados** a DRF 3.18.2, simplejwt 5.5.1, PyJWT 2.15.1, Pillow 13.0.0 y cryptography 50.0.2 |
| Librerías | torch 2.9.1 | **Actualizado** a 2.14.1 (CPU) |
| Binario de Caddy | Caddy 2.10.2, y la imagen oficial 2.11.7 sigue con Go 1.26.8, x/net 0.59 y go-jose 4.1.5 | **Recompilado** Caddy 2.11.7 con `xcaddy`, Go 1.26.10, x/net 0.60.0 y go-jose 4.1.6 |
| Sistema operativo | Debian de `python:3.12.12-slim` y Alpine de Caddy (brotli, curl) | **Actualizado** a `python:3.12.15-slim`; en `web`, `apk upgrade` y se quita curl, que no se usa |

**Resultado tras corregir:** las cuatro imágenes quedan con **0 HIGH y 0 CRITICAL con
parche**. Quedan 45 HIGH del sistema operativo sin parche publicado en cada imagen
de Python, y ninguno en `web`.

Las suites de backend-clinic y backend-admin se corrieron completas con las versiones
nuevas, y el contrato OpenAPI no cambió (DD-OPS-001 §10).

## Decisión

### D1 · Se corrige todo lo que tiene parche

El CI falla con cualquier HIGH o CRITICAL que tenga versión corregida publicada
(`--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1`).

Corregir es siempre actualizar la imagen base o la librería. No se usa
`.trivyignore` para tapar un hallazgo que tenga parche.

### D2 · Se aceptan los que no tienen parche publicado

Con `--ignore-unfixed` quedan fuera los CVE del sistema operativo para los que Debian
todavía no publicó corrección. No hay versión a la que actualizar, y cambiar de
distribución (a Alpine o distroless) está fuera del alcance de esta demo.

**Por qué el riesgo es bajo en este stack:**

- **No se exponen:** ningún contenedor publica puertos salvo `web`, que es Caddy y no
  ejecuta esos paquetes al servir.
- **Sin root:** las cuatro imágenes propias corren como el uid 10001.
- **No se usan:** son utilidades del sistema base (`util-linux`, `libacl`, …) que la
  aplicación no invoca.

**Revisión:** el CI vuelve a escanear en cada PR. En cuanto un CVE recibe parche,
deja de estar ignorado y el CI falla hasta que se actualice la base.

### D3 · Las otras excepciones del stack

| Excepción | Por qué se acepta |
|---|---|
| **El job `secretos` corre como root** | Tiene que darle cada carpeta al usuario que la lee: el uid 10001 para las apps y el uid 70 para Postgres. Termina en segundos y no expone ningún puerto. Los servicios que quedan corriendo no son root. |
| **`ollama/ollama` corre como root** | Es la imagen oficial, solo se levanta con `--profile ia` y no publica puertos. |
| **backend-clinic sigue con SQLite** | Su código solo admite SQLite. Va en un volumen con nombre. Pasar a Postgres es deuda declarada en DD-OPS-001 §4. |
| **Los servicios montan el volumen `secretos` entero, en solo lectura** | Cada uno lee solo su carpeta, que tiene permisos 700 y es de su usuario. Postgres (uid 70) no puede leer la de las apps. Las apps comparten el uid 10001, así que entre ellas sí podrían leerse: es aceptable dentro de un mismo host, porque ya comparten el JWT y el secreto interno. |

## Consecuencias

- **El CI bloquea** cualquier HIGH o CRITICAL con parche en `imagenes-stack.yml`.
- **Los desarrolladores** tienen que reinstalar dependencias en su venv
  (`pip install -r requirements.txt`): Django pasa de 5.0 a 5.2 y se añaden numpy y
  mcp, que faltaban.
- **La imagen de backend-ml pesa unos 1,8 GB** por torch, aunque sea CPU. Se acepta,
  porque el clasificador entrenado es parte del producto.

## Condición de reversión

Esta decisión se revisa si se cumple **cualquiera** de estas condiciones:

- **R1:** un CVE sin parche afecta a un paquete que la aplicación sí usa en tiempo de
  ejecución. En ese caso hay que cambiar de base (distroless o Alpine) en lugar de
  esperar el parche.
- **R2:** el stack sale de `127.0.0.1`, a una red compartida o a internet. Entonces
  hacen falta TLS, secretos de un gestor (no un volumen) y Postgres también para
  backend-clinic.
