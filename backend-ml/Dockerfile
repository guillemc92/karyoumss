# backend-ml en contenedor (DD-OPS-001 D7): segmentación OpenCV y el clasificador
# EfficientNet-B3 entrenado (models/classifier.pth), en CPU.
# Sin secretos: este servicio no recibe ninguno.

# --- Etapa 1: las dependencias se instalan en un entorno aparte ---
FROM python:3.12.15-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS dependencias
WORKDIR /w
COPY requirements-imagen.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir -r requirements-imagen.txt

# --- Etapa 2: la imagen que corre ---
FROM python:3.12.15-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH
# apt-get upgrade: los parches de Debian que la imagen base todavía no trae
# (ADR-0039 D1). El 12/11 Trivy encontró 4 HIGH con parche en apt y zlib1g, y
# la etiqueta 3.12.15-slim seguía sin reconstruirse desde el 21/10.
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 ml
COPY --from=dependencias /opt/venv /opt/venv
WORKDIR /app
COPY --chown=ml:ml app/ app/
COPY --chown=ml:ml models/ models/
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=6 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=4).status != 200)"]
# Un solo proceso: el modelo se carga una vez y el límite de inferencias
# (app/concurrencia.py) es por proceso.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
