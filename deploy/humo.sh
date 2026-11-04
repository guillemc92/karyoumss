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
#   4. que backend-ml responde desde dentro de la red.
# Nunca imprime una contraseña ni un token.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
PY="${PY:-python3}"   # en Git Bash de Windows: PY="py -3"

paso() { printf '%-58s' "$1"; }
ok() { echo "ok"; }

paso "1. / sirve la administración"
curl -fsS "$BASE/" | grep -q '<div id="root">' && ok
paso "1. /clinic/ sirve la clínica"
curl -fsS "$BASE/clinic/" | grep -q '/clinic/assets/' && ok

paso "2. el analista de la demo entra"
clave="$(docker compose run --rm --no-deps -T secretos cat /secretos/admin/DEMO_PASSWORD_ANALISTA)"
cuerpo="$(printf '{"email":"analista@biomed.local","password":"%s"}' "$clave")"
token="$(curl -fsS -H 'Content-Type: application/json' -d "$cuerpo" "$BASE/api/auth/login/" \
  | $PY -c 'import sys,json; print(json.load(sys.stdin)["access"])')"
[ -n "$token" ] && ok

paso "3. con ese token, backend-clinic lista las muestras"
curl -fsS -o /dev/null -H "Authorization: Bearer $token" "$BASE/api/clinic/samples/" && ok

paso "4. backend-ml responde dentro de la red"
docker compose exec -T clinic python -c \
  "import urllib.request; urllib.request.urlopen('http://ml:8000/health/', timeout=5)" && ok

paso "5. backend-ml, Postgres y los backends no están publicados"
publicados="$(docker compose ps --format '{{.Service}} {{.Publishers}}' | grep -c '0.0.0.0\|127.0.0.1' || true)"
[ "$publicados" = "1" ] && ok
