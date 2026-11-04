# backend-clinic en contenedor (DD-E3-001 T3, experimento E3 de M8).
#
# Una sola imagen, dos puntos de entrada:
#   - la API (por omisión): clinic_backend.settings;
#   - la bitácora extraída: DJANGO_SETTINGS_MODULE=clinic_backend.settings_bitacora.
# Sin secretos dentro: todos llegan por variables de entorno al arrancar.

# --- Etapa 1: las dependencias se compilan aparte y solo pasan las ruedas ---
FROM python:3.12.7-slim AS dependencias
WORKDIR /w
COPY requirements.txt .
# gunicorn solo en la imagen: el desarrollo en Windows sigue con runserver (D5).
RUN pip wheel --no-cache-dir --wheel-dir /ruedas -r requirements.txt gunicorn==23.0.0

# --- Etapa 2: la imagen que corre ---
FROM python:3.12.7-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 clinica
COPY --from=dependencias /ruedas /ruedas
RUN pip install --no-cache-dir --no-index /ruedas/* && rm -rf /ruedas
# Las carpetas de los volúmenes, del usuario sin root: Docker copia el dueño al
# crear el volumen con nombre, y así el seed puede escribir sin ser root.
RUN mkdir -p /datos/api /datos/bitacora /k6data && chown -R clinica:clinica /datos /k6data
WORKDIR /app
COPY --chown=clinica:clinica . .
USER clinica
EXPOSE 8000
# La misma configuración de gunicorn en las dos formas del experimento.
CMD ["gunicorn", "clinic_backend.wsgi", "--bind", "0.0.0.0:8000", \
     "--workers", "2", "--worker-class", "gthread", "--threads", "4", "--timeout", "30"]
