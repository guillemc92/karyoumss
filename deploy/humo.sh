#!/usr/bin/env bash
# Prueba de humo del stack ya levantado (DD-OPS-001 §5). La corre el CI después de
# `docker compose up -d --wait`, y se puede correr a mano:
#
#   docker compose up -d --wait && deploy/humo.sh
#
# Comprueba, a través de `web` (el único puerto publicado):
#   1. que se sirven las dos aplicaciones;
#   2. que el analista de la demo entra (backend-admin emite el JWT);
#   3. que con ese JWT backend-clinic responde (el secreto compartido coincide);
#   4. que backend-ml responde desde dentro de la red;
#   5. que solo `web` publica un puerto.
# El primer paso que falla termina el script con 1. Nunca imprime una contraseña
# ni un token.
set -euo pipefail
export MSYS_NO_PATHCONV=1   # sin esto Git Bash reescribe /secretos/... como ruta de Windows
BASE="${BASE:-http://127.0.0.1:8080}"
PY="${PY:-python3}"   # en Git Bash de Windows: PY="py -3"

paso() {
  printf '%-60s' "$1"
  shift
  if "$@"; then echo ok; else echo FALLA; exit 1; fi
}

sirve() { curl -fsS "$BASE$1" | grep -q "$2"; }

# El código HTTP, sin archivo temporal: va en la última línea de la salida.
estado() { curl -sS -w '\n%{http_code}' "$@" | tail -n 1; }

entra_el_analista() {
  local clave cuerpo
  clave="$(docker compose run --rm --no-deps -T secretos cat /secretos/admin/DEMO_PASSWORD_ANALISTA)"
  cuerpo="$(printf '{"email":"analista@biomed.local","password":"%s"}' "$clave")"
  TOKEN="$(curl -fsS -H 'Content-Type: application/json' -d "$cuerpo" "$BASE/api/auth/login/" \
    | $PY -c 'import sys,json; print(json.load(sys.stdin)["access"])')"
  [ -n "$TOKEN" ]
}

clinic_responde() { [ "$(estado -H "Authorization: Bearer $TOKEN" "$BASE/api/clinic/samples/")" = 200 ]; }

sin_token_no() { [ "$(estado "$BASE/api/clinic/samples/")" = 401 ]; }

ml_responde() {
  docker compose exec -T clinic python -c \
    "import urllib.request; urllib.request.urlopen('http://ml:8000/health/', timeout=5)"
}

solo_web_publica() {
  [ "$(docker compose ps --format '{{.Service}} {{.Publishers}}' | grep -c '0\.0\.0\.0\|127\.0\.0\.1')" = 1 ]
}

paso "1. / sirve la administración" sirve / '<div id="root">'
paso "1. /clinic/ sirve la clínica" sirve /clinic/ '/clinic/assets/'
paso "2. el analista de la demo entra" entra_el_analista
paso "3. con ese token, backend-clinic lista las muestras (200)" clinic_responde
paso "3. sin token, backend-clinic responde 401" sin_token_no
paso "4. backend-ml responde dentro de la red" ml_responde
paso "5. solo web publica un puerto" solo_web_publica
