# backend-admin en contenedor (DD-OPS-001 D7). Postgres con el schema 'admin'
# (ADR-0012). Sin secretos dentro: llegan por variables o por archivos de
# BIOMED_SECRETS_DIR al arrancar (D3).

# --- Etapa 1: las dependencias se compilan aparte y solo pasan las ruedas ---
FROM python:3.12.15-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS dependencias
WORKDIR /w
COPY requirements.txt .
# requirements.txt mezcla las de prueba: no entran en la imagen.
RUN grep -vE '^(pytest|pytest-django|pytest-cov|factory-boy|ruff)==' requirements.txt > produccion.txt \
 && pip wheel --no-cache-dir --wheel-dir /ruedas -r produccion.txt

# --- Etapa 2: la imagen que corre ---
FROM python:3.12.15-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# apt-get upgrade: los parches de Debian que la imagen base todavía no trae
# (ADR-0039 D1). El 12/11 Trivy encontró 4 HIGH con parche en apt y zlib1g, y
# la etiqueta 3.12.15-slim seguía sin reconstruirse desde el 21/10.
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 admin
COPY --from=dependencias /ruedas /ruedas
RUN pip install --no-cache-dir --no-index /ruedas/* && rm -rf /ruedas
# La carpeta de los secretos, del usuario sin root: Docker copia el dueño al
# crear el volumen con nombre.
RUN mkdir -p /secretos && chown admin:admin /secretos
WORKDIR /app
COPY --chown=admin:admin . .
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/admin/login/', timeout=4).status != 200)"]
CMD ["gunicorn", "admin_backend.wsgi", "--bind", "0.0.0.0:8000", \
     "--workers", "2", "--worker-class", "gthread", "--threads", "4", "--timeout", "30"]
