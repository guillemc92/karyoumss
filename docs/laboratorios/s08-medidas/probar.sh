#!/usr/bin/env bash
# Arranca la imagen, mide hasta /health/ 200 y segmenta una metafase real.
# uso: probar.sh IMAGEN METAFASE SALIDA
set -u
I=$1; M=$2; S=$3
docker rm -f lab-prueba >/dev/null 2>&1
t0=$(date +%s.%N)
docker run -d --name lab-prueba -p 127.0.0.1:18800:8000 "$I" >/dev/null
until curl -fs http://127.0.0.1:18800/health/ >/dev/null 2>&1; do sleep 0.5; done
t1=$(date +%s.%N)
salud=$(curl -fs http://127.0.0.1:18800/health/)
t2=$(date +%s.%N)
seg=$(curl -fs -F "file=@$M" http://127.0.0.1:18800/api/v1/segment/)
t3=$(date +%s.%N)
{
  echo "imagen: $I"
  echo "arranque hasta /health/ 200: $(awk "BEGIN{printf \"%.1f\", $t1-$t0}") s"
  echo "health: $salud"
  echo "segment: HTTP ok, $(echo "$seg" | py -3 -c 'import sys,json; d=json.load(sys.stdin); print(len(d.get("chromosomes",[])), "cromosomas; modelo:", d.get("model_version"))') en $(awk "BEGIN{printf \"%.1f\", $t3-$t2}") s"
  echo "estado docker: $(docker inspect -f '{{.State.Health.Status}}' lab-prueba)"
} | tee "$S"
docker rm -f lab-prueba >/dev/null
