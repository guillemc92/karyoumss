#!/usr/bin/env bash
# Bucle de corridas del experimento E3 (DD-E3-001 D10). Se corre desde Git Bash o Linux:
#
#   bench/e3/correr.sh una <proceso|http> [falla]   una corrida, para probar
#   bench/e3/correr.sh corridas [N]                 N corridas (5 por omisión) de cada combinación
#   bench/e3/correr.sh build [N]                    N builds en frío de cada forma
#
# Cada corrida:
#   1. genera secretos nuevos al azar;
#   2. levanta la forma desde cero, después de un `down -v`;
#   3. corre k6;
#   4. vuelve a hacer `down -v`.
# Los tiempos de seed, `up` y build van a resultados/tiempos.csv; el resumen de k6, a
# resultados/<forma>-<falla>-<n>.json.
#
# Combinaciones medidas en `corridas` (las vueltas alternan las formas):
#   proceso, sin falla          la forma en proceso no tiene red que romper: es la línea base
#   http con colgado, caido y lento
set -euo pipefail
cd "$(dirname "$0")"
export MSYS_NO_PATHCONV=1   # sin esto Git Bash reescribe /k6/carga.js

RPS="${RPS:-10}"
MUESTRAS="${E3_MUESTRAS:-1000}"
export E3_MUESTRAS="$MUESTRAS"
TIEMPOS=resultados/tiempos.csv
mkdir -p resultados
[ -f "$TIEMPOS" ] || echo "fecha,que,forma,falla,corrida,segundos" > "$TIEMPOS"

dc() { docker compose --env-file "formas/$1.env" "${@:2}"; }

secretos() {
  # De usar y tirar: valen para una corrida y no se guardan en ningún sitio.
  export E3_DJANGO_SECRET_KEY E3_JWT_SECRET E3_INTERNAL_SECRET E3_VAULT_KEY
  E3_DJANGO_SECRET_KEY="$(openssl rand -hex 32)"
  E3_JWT_SECRET="$(openssl rand -hex 32)"
  E3_INTERNAL_SECRET="$(openssl rand -hex 32)"
  E3_VAULT_KEY="$(openssl rand -base64 32 | tr '+/' '-_')"   # clave Fernet válida
}

ahora() { date +%s.%N; }
anotar() { echo "$(date -Iseconds),$1,$2,$3,$4,$(awk "BEGIN{printf \"%.1f\", $6 - $5}")" >> "$TIEMPOS"; }

bajar() { dc "$1" --profile '*' down -v --remove-orphans >/dev/null 2>&1 || true; }

una() {
  local forma=$1 falla=${2:-} n=${3:-0}
  secretos
  bajar "$forma"
  local t0 t1 t2
  t0=$(ahora)
  dc "$forma" --profile seed run --rm seed
  t1=$(ahora)
  dc "$forma" up -d --wait
  t2=$(ahora)
  anotar seed "$forma" "${falla:-ninguna}" "$n" "$t0" "$t1"
  anotar up "$forma" "${falla:-ninguna}" "$n" "$t1" "$t2"
  dc "$forma" run --rm k6 run --quiet \
    -e MODO="$forma" -e FALLA="$falla" -e RPS="$RPS" \
    -e SALIDA="${forma}-${falla:-sin-falla}-${n}" /k6/carga.js
  bajar "$forma"
}

secretos   # compose los exige para cualquier comando, también build
case "${1:-}" in
  una)
    docker compose --env-file formas/proceso.env --profile seed build
    una "${2:?proceso o http}" "${3:-}" 0 ;;
  corridas)
    N="${2:-5}"
    docker compose --env-file formas/proceso.env --profile seed build
    for n in $(seq 1 "$N"); do
      una proceso "" "$n"
      for falla in colgado caido lento; do una http "$falla" "$n"; done
    done ;;
  build)
    N="${2:-5}"
    for n in $(seq 1 "$N"); do
      for forma in proceso http; do
        secretos
        t0=$(ahora)
        dc "$forma" --profile seed build --no-cache >/dev/null
        anotar build "$forma" - "$n" "$t0" "$(ahora)"
      done
    done ;;
  *) sed -n '2,8p' "$0"; exit 2 ;;
esac
