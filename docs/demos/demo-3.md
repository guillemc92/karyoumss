# Demo 3 (release 8.3.0) — Grupo BIOMED UMSS

| Campo | Valor |
|---|---|
| **Demo** | 3 · miércoles 4 de noviembre de 2026 |
| **Release** | `release/8.3.0` |
| **Repositorio** | https://github.com/guillemc92/karyoumss |
| **Integrantes** | 1 (grupo individual) |
| **Canal oficial** | Classroom (este archivo es la copia del repositorio) |

## Integrantes y funcionalidades

Son las dos funcionalidades que la consigna define como «lo técnico de esta demo»;
cada una cuenta como una mediana.

| Integrante | Funcionalidad | Tamaño | Caso de uso (FSD) | Diseño | Repositorio |
|---|---|---|---|---|---|
| Guillermo Mamani Chambi ([`guillemc92`](https://github.com/guillemc92)) | 1 · Imagen y stack de producción | Mediana | Transversal: el producto entero, con FSD-UC-001 a FSD-UC-003 de punta a punta sobre el stack | [DD-OPS-001](../design/DD-OPS-001.md) · [ADR-0039](../adr/0039-stack-produccion-riesgos-aceptados.md) | https://github.com/guillemc92/karyoumss |
| Guillermo Mamani Chambi | 2 · Análisis 🅱️: el módulo que extraeríamos como microservicio (E3) | Mediana | FSD-UC-005 (audit trail) y FSD-UC-007 (modo degradado) | [DD-E3-001](../design/DD-E3-001.md) · [ADR-0038](../adr/0038-no-extraer-bitacora-auditoria.md) | https://github.com/guillemc92/karyoumss |

La demo se presenta sobre el stack de la funcionalidad 1. En ella se ve también el
enderezado de cromosomas (DD-KARYO-008, PR #7), que entró en esta release.

## Funcionalidad 1 — Imagen y stack de producción

**Criterios de aceptación** (verificados el 04/11; detalle en DD-OPS-001 §10):

1. **Imágenes multi-stage.** Hay un Dockerfile por servicio: `backend-clinic`,
   `backend-admin`, `backend-ml` y `deploy/web`.
   - **Etapas:** la última solo recibe las ruedas, el venv o los `dist/`. Node y Go
     existen únicamente en las etapas de compilación.
   - **Usuario:** ninguna corre como root (uid 10001).
   - **Bases:** fijadas por digest.
2. **Todo se levanta desde un clon limpio** con `docker compose up -d --wait`:
   - Postgres con healthcheck;
   - jobs de secretos y migraciones (`service_completed_successfully`), y el de
     migraciones también siembra los usuarios;
   - los dos backends, backend-ml con el clasificador entrenado y `web`;
   - Ollama con `--profile ia`.
   Todo queda `healthy` en 55 s con las imágenes construidas.
3. **Ningún secreto en git ni en una imagen.** El job `secretos` los genera al azar
   la primera vez, con permisos 600 y una carpeta por servicio. Postgres lee el suyo
   con `POSTGRES_PASSWORD_FILE`.
4. **Un solo puerto.** Solo `web` (Caddy) publica, en `127.0.0.1:8080`. Sirve los dos
   frontends y las tres APIs desde un mismo origen (ADR-0020).
5. **hadolint y Trivy sin altos ni críticos sin justificar.**
   - **hadolint 2.15.1:** 0 hallazgos.
   - **`trivy config`:** 0 hallazgos.
   - **`trivy image`:** 0 HIGH o CRITICAL con parche en las 4 imágenes.
   - **Lo que no tiene parche publicado** está justificado en ADR-0039.
6. **En el CI.** `.github/workflows/imagenes-stack.yml` corre hadolint, Trivy y el
   `up --wait` con la prueba de humo (`deploy/humo.sh`) en cada PR.

**Lo que Trivy obligó a corregir:**
- **Django:** la 5.0.6 no tiene soporte y traía 2 CRITICAL; pasó a la 5.2.18 LTS.
- **Librerías de Python:** DRF, PyJWT, Pillow, cryptography y torch.
- **Bases:** las de Python y Alpine.
- **Caddy:** se recompiló con Go 1.26.10.

Las suites pasaron con las versiones nuevas y el contrato OpenAPI quedó idéntico.

**Lo que destapó el clon limpio** (estaba roto también en desarrollo):
- **numpy y mcp:** el código los importa, pero no estaban declarados como dependencias.
- **El tamaño de la petición:** tres metafases BMP reales no cabían en el límite de
  Django, de 2,5 MB.
- **El build de frontend-admin:** tres pruebas con errores de tipos impedían
  compilarlo.

**Evidencia:**
- **PR:** [#9](https://github.com/guillemc92/karyoumss/pull/9).
- **Commits:** `ccb1d99`, `7c3eae3`, `b4be965`, `474a62e` y `f936d65`.

## Funcionalidad 2 — Análisis 🅱️: el módulo que extraeríamos como microservicio (E3)

**Cuál es:** la bitácora de auditoría, la tabla `clinic_audit_events`. Es append-only
(RN-05) y cada evento se encadena al anterior con SHA-256 (ADR-0022).

**Por qué es el candidato:**
- **Frontera clara:** tiene su propia tabla.
- **Datos sensibles:** es un registro de cumplimiento (21 CFR Part 11).
- **Aislamiento:** fuera del monolito, nadie de la parte clínica podría tocarla.

**Su interfaz, con las dos formas:**
- **La interfaz:** `BitacoraPort`, elegida con `BITACORA_MODO`.
  - `proceso` (por omisión): dentro del monolito.
  - `http`: un servicio aparte, misma imagen con otro punto de entrada, protegido con
    el secreto interno.
- **Protecciones del cliente HTTP:** 300 ms por intento, 2 intentos, 800 ms en total y
  un breaker.
- **Si la bitácora cae:** `GET …/audit/` responde `503 AUDIT_UNAVAILABLE` con
  `Retry-After`. El 503 está en el contrato, y oasdiff lo clasifica como cambio aditivo.

**Qué se midió y qué se decidió:**
- **Medición:** 20 corridas con k6 y Toxiproxy (colgado, caído y lento), con las
  hipótesis commiteadas antes de medir.
- **Resultado:** la latencia apenas sube (+14,6 ms), pero la forma extraída falla
  más. Sin ninguna falla da 503 en 10 de 15 corridas, y después de cada falla, entre
  un 11 y un 13 %.
- **Decisión: no extraer**
  ([ADR-0038](../adr/0038-no-extraer-bitacora-auditoria.md), aceptado). Tiene
  condiciones de reversión medibles.
- **Detalle:** [`bench/e3/INFORME.md`](../../bench/e3/INFORME.md).

**Evidencia:**
- **PR:** [#8](https://github.com/guillemc92/karyoumss/pull/8).
- **Commits:** `3526e3e` (hipótesis), `44416bd`, `2e89e3c`, `27b9c6b`, `619211e`,
  `e1727ed` y `32dfea4`.

## Guion

### Antes de clase (≈ 40 min)

1. Clonar la release en una carpeta limpia y construir las imágenes. El primer
   build tarda unos 30 min en esta máquina, sobre todo por torch:

       git clone --branch release/8.3.0 https://github.com/guillemc92/karyoumss C:\demo\karyoumss
       cd C:\demo\karyoumss
       docker compose build

2. Cerrar Illustrator y los navegadores que no se usen, porque compiten por la CPU.
   Dejar abierto Docker Desktop.
3. Tener a mano tres metafases (por ejemplo, `metafase_1.bmp` de MetaClass).

### En vivo, funcionalidad 1 (≈ 4 min)

1. **Levantar desde cero.** Tarda unos 55 s:

       docker compose down -v
       docker compose up -d --wait
       docker compose ps -a

   Los jobs aparecen en `Exited (0)` y el resto en `healthy`.
2. **Prueba de humo:** `PY="py -3" bash deploy/humo.sh` da 7 de 7.
3. **Entrar.** Pedir la contraseña con
   `docker compose run --rm --no-deps secretos cat /secretos/admin/DEMO_PASSWORD_ANALISTA`
   y entrar por http://localhost:8080/ como `analista@biomed.local`.
4. **Registrar una muestra** con las tres metafases (unos 25 s) y abrir su
   cariotipo: los cromosomas aparecen enderezados.
5. **Enseñar la seguridad:** el workflow `imagenes-stack.yml` y el run verde del
   PR #9; ADR-0039 con lo que se corrigió y lo que se acepta.

### En vivo, funcionalidad 2 (≈ 3 min)

1. **La interfaz:** `BitacoraPort` y `BITACORA_MODO`, y el 503 en el contrato.
2. **Los resultados:** `py -3 bench/e3/resumir.py`, o la tabla de
   `bench/e3/INFORME.md`.
3. **La decisión:** ADR-0038, con sus condiciones de reversión.

### Preguntas probables

| Pregunta | Respuesta corta |
|---|---|
| ¿Por qué el job `secretos` corre como root? | Tiene que dar cada carpeta a su lector: uid 10001 para las apps y 70 para Postgres. Termina en segundos y no expone nada. Los servicios que quedan corriendo no son root. Está en ADR-0039 D3. |
| ¿Por qué `--ignore-unfixed`? | Lo que tiene parche se corrigió entero: Django, DRF, PyJWT, Pillow, cryptography, torch, las bases y Caddy. Lo que queda no tiene versión corregida publicada, así que no hay a qué actualizar. Va justificado en ADR-0039 D2, y en cuanto salga el parche, el CI vuelve a fallar. |
| ¿Por qué clinic sigue en SQLite? | Su código solo admite SQLite. Va en un volumen con nombre y está declarado como deuda. backend-admin sí usa Postgres, con un rol sin superusuario. |
| ¿Por qué la imagen de ml pesa 1,8 GB? | Por torch, aun en CPU. El clasificador entrenado es parte del producto. |
| ¿Qué pasa si alguien hace `down -v`? | Se borran los datos y los secretos, y el siguiente `up` genera unos nuevos. `down` sin `-v` los conserva. |
| ¿Por qué no extraer la bitácora, si la latencia casi no sube? | Sube poco, pero falla más: 503 sin falla en 10 de 15 corridas. El aislamiento que se buscaba sale más barato con permisos de la base de datos (R1 del ADR-0038). |
