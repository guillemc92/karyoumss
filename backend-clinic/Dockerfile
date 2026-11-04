# backend-clinic en contenedor: la imagen del stack (DD-OPS-001) y la del
# experimento E3 (DD-E3-001 T3).
#
# Una sola imagen, dos puntos de entrada:
#   - la API (por omisión): clinic_backend.settings;
#   - la bitácora extraída: DJANGO_SETTINGS_MODULE=clinic_backend.settings_bitacora.
# Sin secretos dentro: todos llegan por variables de entorno al arrancar.

# --- Etapa 1: las dependencias se compilan aparte y solo pasan las ruedas ---
FROM python:3.12.15-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS dependencias
WORKDIR /w
COPY requirements.txt .
# gunicorn solo en la imagen: el desarrollo en Windows sigue con runserver (D5).
RUN pip wheel --no-cache-dir --wheel-dir /ruedas -r requirements.txt gunicorn==23.0.0

# --- Etapa 2: la imagen que corre ---
FROM python:3.12.15-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 clinica
COPY --from=dependencias /ruedas /ruedas
RUN pip install --no-cache-dir --no-index /ruedas/* && rm -rf /ruedas
# Las carpetas de los volúmenes, del usuario sin root: Docker copia el dueño al
# crear el volumen con nombre, y así el seed puede escribir sin ser root.
# /secretos y /datos/clinic son del stack (DD-OPS-001); el resto, del banco del E3.
RUN mkdir -p /secretos /datos/clinic /datos/api /datos/bitacora /k6data \
 && chown -R clinica:clinica /secretos /datos /k6data
WORKDIR /app
COPY --chown=clinica:clinica . .
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/admin/login/', timeout=4).status != 200)"]
# La misma configuración de gunicorn en las dos formas del experimento. El
# stack alarga el timeout con GUNICORN_CMD_ARGS: segmentar tarda ~19 s.
CMD ["gunicorn", "clinic_backend.wsgi", "--bind", "0.0.0.0:8000", \
     "--workers", "2", "--worker-class", "gthread", "--threads", "4", "--timeout", "30"]
