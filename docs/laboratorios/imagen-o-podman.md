# Laboratorio S08: imagen o Podman

- **Integrante(s):** Guillermo Mamani Chambi ([`guillemc92`](https://github.com/guillemc92)). El grupo es individual.
- **Opción:** A, auditar y adelgazar la imagen.
- **Servicio o stack:** `backend-ml`, el servicio de inferencia: FastAPI con la segmentación
  OpenCV y el clasificador EfficientNet-B3 entrenado sobre torch, en CPU. Es la imagen
  más grande del stack de producción (`compose.yaml` de `release/8.3.0`).
- **Fecha:** 9 de noviembre de 2026.
- **Máquina:**
  - **Sistema:** Windows 10 Pro 10.0.19045.
  - **Docker:** Docker Desktop 4.55.0, con Docker Engine 29.1.3 como cliente y servidor, sobre
    WSL2 con 4 CPU y 7,7 GB para Docker.
  - **Podman:** no se usó.
- **Uso de IA: sí.** Claude (Claude Code) propuso los cambios del Dockerfile, corrió
  los comandos de medición y redactó este informe.
  - **Cómo se comprobó:** cada propuesta se midió antes de aceptarla, y la que empeoraba
    el servicio se descartó (ver «Qué cambié»).
  - **Dónde están las salidas:** las salidas completas están en
    [`s08-medidas/`](s08-medidas/), y cada número de este informe sale de ellas.
  - **Por qué con IA:** el README del laboratorio pide hacerlo sin IA, pero la consigna de
    Classroom la permite si se comprueba con mediciones y se declara. Se siguió la de
    Classroom.

## Punto de partida

- **`main` no tiene `backend-ml`.** El desarrollo vive en las ramas `release/*`.
- **Primer commit de la rama (`58b6e86`):** trae `backend-ml` sin cambios desde
  `release/8.3.0` (`630420d`). Ese Dockerfile ya era multi-stage, sin root y con la base
  fijada por digest (DD-OPS-001). La imagen «antes» es exactamente la del stack de
  producción.
- **Segundo commit:** el único cambio es `backend-ml/Dockerfile`.

## Opción A: antes y después

**Imagen:** `lab-ml:antes` y `lab-ml:despues`. **Dockerfile:** `backend-ml/Dockerfile`.

| Medida | Antes | Después | Comando con el que se midió |
|---|---:|---:|---|
| Tamaño en disco (DISK USAGE) | 1,86 GB | **1,57 GB** (−290 MB, −16 %) | `docker image ls` |
| Tamaño comprimido (CONTENT SIZE) | 437 MB | **383 MB** (−54 MB, −12 %) | `docker image ls` |
| Número de capas | 9 capas de sistema de archivos (20 filas en `history`) | 9 (20) | `docker image history`; `docker image inspect --format "{{len .RootFS.Layers}}"` |
| Eficiencia y espacio desperdiciado (Dive) | 99,71 %, 5,7 MB | 99,66 %, 5,7 MB | `dive` con `CI=true` |
| Usuario con el que corre | `uid=10001(ml)` | `uid=10001(ml)` | `docker run --rm --entrypoint id ...` |
| CVE totales (Trivy 0.76.1) | 203: 191 del SO + 12 de Python | **197**: 191 del SO + 6 de Python | `trivy image --scanners vuln` |
| CVE HIGH + CRITICAL | 51 + 0, todas del SO; ninguna de Python | 51 + 0 | ídem |
| Avisos de hadolint | 0 | 0 (hubo 1 intermedio, ver abajo) | `hadolint` 2.15.1 |
| ¿Arranca y responde? | Sí. `/health/` 200 en 19,4 s (mediana de 3); segmenta `metafase_1.bmp` y devuelve 38 cromosomas | Sí. `/health/` 200 en 24,3 s (mediana de 3); los mismos 38 cromosomas con el modelo entrenado | `GET /health/` y `POST /api/v1/segment/` (`s08-medidas/probar.sh`) |

**Sobre las cifras de tiempo:**
- **Variación:** con la CPU compartida, el arranque varía entre corridas. El «después»
  fue de 20,6 a 30,3 s y el «antes», de 19,3 a 20,3 s
  ([`arranque-3x.txt`](s08-medidas/arranque-3x.txt)).
- **Lo que no se puede afirmar:** con tres corridas, no se puede decir que el «después»
  arranque igual de rápido. Arranca a lo sumo unos segundos más tarde.
- **La segmentación:** tardó 44,5 s antes y 53,0 s después, en una sola corrida cada una.
  La cuenta de cromosomas es idéntica, y con una corrida esa diferencia es ruido de CPU,
  no un efecto medido.

### Qué encontré en la imagen de antes

- **Ya estaba bien:** multi-stage, uid 10001, base fijada por digest y 0 avisos de
  hadolint. Dive da 99,7 %: casi no hay espacio desperdiciado *entre capas*. El problema
  está *dentro* de una capa.
- **Una sola capa pesa 1,25 GB:** `COPY /opt/venv`, el entorno de Python. Dentro de
  `site-packages`:

  | Qué | Tamaño |
  |---|---:|
  | `torch` | 769 MB, de los que `torch/lib` son 455 MB de bibliotecas nativas que sí se ejecutan |
  | `.pyc` en todo el venv | 151 MB |
  | Carpetas `tests` y `test` de los paquetes (numpy, sympy, networkx…) | 143 MB |
  | `opencv_python_headless.libs` + `cv2` | 153 MB |
  | `sympy` | 74 MB, dependencia de torch |
  | `torch/include` | 63 MB, headers C++ |
  | `pip` + `setuptools` | 21 MB |

- **torchvision se usa** (`app/efficientnet.py` importa `models` y `transforms`), así
  que no se puede quitar.
- **Las 51 HIGH vienen todas de los paquetes del sistema operativo** de la base Debian 13
  (`python:3.12.15-slim`), y ninguna tiene parche publicado. Las 12 CVE de Python eran
  MEDIUM o LOW, y la mitad venía de `pip` y `setuptools`.

### Qué cambié

```diff
 RUN python -m venv /opt/venv \
  && /opt/venv/bin/pip install --no-cache-dir -r requirements-imagen.txt
+WORKDIR /opt/venv/lib/python3.12/site-packages
+RUN rm -rf torch/include torch/share \
+ && find . -depth -type d \( -name tests -o -name test \) -prune -exec rm -rf {} + \
+ && /opt/venv/bin/python -m pip uninstall -y -q pip setuptools
```

1. **Headers C++ y CMake de torch** (`torch/include`, `torch/share`): solo sirven para
   compilar extensiones, no para ejecutar.
2. **Carpetas `tests` y `test` de cada paquete:** son las pruebas de las propias
   librerías. El servicio no las importa.
3. **`pip` y `setuptools` fuera del venv final:** nadie instala nada en la imagen que
   corre. Así desaparecen también 6 CVE MEDIUM o LOW de Python.
4. **Todo va en una capa propia de la etapa de dependencias,** *después* del
   `pip install`.
   - **Para qué:** así la capa de pip sigue en caché y no hay que volver a descargar
     torch. Con la red de la máquina, eso llevaba más de 8 minutos.
   - **Efecto:** la etapa final copia el venv ya limpio, y por eso el número de capas
     finales no cambia.
5. **`WORKDIR` en lugar de `cd`.** La primera versión usaba `cd` dentro del `RUN`, y
   hadolint dio **un aviso nuevo, DL3003** («Use WORKDIR to switch to a directory»). Con
   `WORKDIR` vuelve a 0. El `WORKDIR /app` de la etapa final no cambia: el servicio sigue
   corriendo en `/app`, comprobado con `os.getcwd()`.

**Lo que la IA propuso y se descartó al medirlo:** quitar también los `.pyc`.
- **Lo que ganaba:** la imagen bajaba a 1,42 GB, otros 150 MB.
- **Lo que costaba:** el arranque pasaba de unos 20 s a **unos 40 s**, con 38,5, 40,5 y
  44,3 s en tres corridas. El servicio corre sin root y con `PYTHONDONTWRITEBYTECODE`,
  así que Python recompila todo torch en *cada* arranque.
- **Decisión:** 150 MB no compensan duplicar el tiempo hasta que el servicio está listo.

**Un fallo del instrumento:** la primera variante «con `.pyc`» no los tenía.
- **Qué pasó:** el `sed` que debía quitar la línea no coincidió, y la imagen salió igual
  a la «sin `.pyc`». Sus tiempos (40–48 s) se descartaron.
- **Cómo se cazó:** contando los `.pyc` *dentro* de cada imagen
  (`find /opt/venv -name "*.pyc" | wc -l`): 6.554 antes, 0 sin `.pyc` y 4.661 en la
  final.
- **Después:** solo entonces se midió de nuevo.

### Qué no pude resolver o no me convenció

- **Las 51 HIGH del sistema operativo siguen,** porque vienen de la base Debian y no
  tienen parche publicado.
  - **Qué lo arreglaría:** cambiar de base, a distroless o a una Docker Hardened Image.
  - **Por qué no se hizo:** las imágenes distroless de Python traen otra versión de
    Python, distinta de la 3.12 del venv. Habría que reinstalar torch para esa versión,
    y no lo intenté con esta red.
  - **Dónde está aceptado:** en el ADR-0039 del proyecto.
- **El peso de verdad es torch:** 455 MB de bibliotecas nativas en `torch/lib`, que el
  servicio sí carga. Adelgazar más exigiría otro runtime para el modelo, por ejemplo
  exportarlo a ONNX y servirlo con onnxruntime. Eso cambia el servicio, no solo la
  imagen.
- **`sympy` (74 MB) y `networkx` (19 MB)** son dependencias de torch que esta inferencia
  probablemente no usa. No los quité: torch los declara como dependencias, y romper eso
  por 90 MB sin una prueba de cada camino de torch no me convenció.
- **El arranque del «después» varía más** (20,6–30,3 s). Con tres corridas no se puede
  descartar que sea unos segundos más lento.

## Comandos usados

En Git Bash, con `export MSYS_NO_PATHCONV=1` antes de los que montan
`/var/run/docker.sock`.

```bash
# Rama desde main y servicio de partida
git worktree add -b lab-s08/mamani-chambi <carpeta> origin/main
git checkout origin/release/8.3.0 -- backend-ml

# Antes
cd backend-ml
docker build -t lab-ml:antes .
docker version
docker image ls lab-ml:antes
docker image history lab-ml:antes
docker image inspect lab-ml:antes --format "{{len .RootFS.Layers}}"
docker run --rm -e CI=true -v /var/run/docker.sock:/var/run/docker.sock wagoodman/dive:v0.13.1@sha256:f1886e6c32c094fc41a623c1989f5cb3e48aa766da5f0be233f911fc1d85ce10 lab-ml:antes
docker image inspect lab-ml:antes --format "{{.Config.User}}"
docker run --rm --entrypoint id lab-ml:antes
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache aquasec/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c image --scanners vuln lab-ml:antes
docker run --rm -i hadolint/hadolint:v2.15.1@sha256:32dac94127fd60b7b7e3fbfc65e1383b9b5e25c9bfd7b8536de7a539fe68a12d < Dockerfile
bash ../docs/laboratorios/s08-medidas/probar.sh lab-ml:antes <ruta>/metafase_1.bmp prueba-antes.txt

# Dónde está el peso, dentro del venv
docker run --rm --entrypoint sh lab-ml:antes -c 'cd /opt/venv/lib/python3.12/site-packages && du -sm * | sort -rn | head'
docker run --rm --entrypoint sh lab-ml:antes -c 'find /opt/venv -name "*.pyc" | wc -l'

# Después: los mismos comandos con lab-ml:despues
docker build -t lab-ml:despues .
# ...

# Arranque, tres veces por variante (arranque-3x.txt)
docker run -d --name lab-t -p 127.0.0.1:18801:8000 lab-ml:<variante>
#   y se mide hasta que GET http://127.0.0.1:18801/health/ responde 200
```
