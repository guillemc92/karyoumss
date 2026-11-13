#!/usr/bin/env bash
# Prueba de humo de las trazas (DD-OBS-001, criterios 1 a 3). El stack tiene que
# estar levantado con el perfil obs:
#
#   BIOMED_TRAZAS=http://tempo:4318 docker compose --profile obs up -d --wait
#   deploy/humo-trazas.sh
#
# Hace UN «procesar» con una metafase sintética y comprueba, preguntando a Tempo a
# través de Grafana, que quedó UNA traza:
#   1. con tramos de backend-clinic y de backend-ml (la traza cruza los servicios);
#   2. con los tramos esperar_turno, segmentar y clasificar;
#   3. sin el texto de búsqueda de la URL en ningún atributo (RN-03).
# Nunca imprime el token.
set -euo pipefail
export MSYS_NO_PATHCONV=1   # sin esto Git Bash reescribe /k6data/... como ruta de Windows
BASE="${BASE:-http://127.0.0.1:8080}"
GRAFANA="${GRAFANA:-http://127.0.0.1:3000}"
PY="${PY:-python3}"   # en Git Bash de Windows: PY="py -3"
MARCA="ZZHUMOTRAZAS$$"   # viaja como búsqueda en la URL: no debe aparecer en Tempo

echo "Sembrando una muestra sintética…"
docker compose --profile carga run --rm -T -e CARGA_MUESTRAS=2 carga-semilla >/dev/null
TOKEN="$(docker compose --profile carga run --rm -T --entrypoint cat carga-semilla /k6data/token.txt)"
ID="$(docker compose --profile carga run --rm -T --entrypoint cat carga-semilla /k6data/ids.json \
  | $PY -c 'import sys,json; print(json.load(sys.stdin)[0])')"

echo "Procesando (una inferencia: puede tardar un minuto)…"
# El código HTTP va en la última línea de la salida, sin archivo temporal ni
# /dev/null: el curl de Windows no sabe escribir ahí (igual que en humo.sh).
estado="$(curl -sS -w '\n%{http_code}' -m 170 -X POST -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{}' "$BASE/api/clinic/samples/$ID/process/" | tail -n 1)"
if [ "$estado" = 503 ]; then
  echo "FALLA: procesar devolvió 503. Si el motor estaba ocupado con otra inferencia,"
  echo "       esperar a que termine (GET /api/clinic/pipeline/inferencias/) y repetir."
  exit 1
fi
[ "$estado" = 200 ] || { echo "FALLA: procesar devolvió $estado"; exit 1; }
# La redirección la hace el shell, no curl: así funciona también en Git Bash.
curl -sS -H "Authorization: Bearer $TOKEN" "$BASE/api/clinic/samples/?search=$MARCA" > /dev/null

echo "Preguntando a Tempo…"
GRAFANA="$GRAFANA" MARCA="$MARCA" $PY - <<'EOF'
import json, os, sys, time, urllib.parse, urllib.request

base = os.environ['GRAFANA'] + '/api/datasources/proxy/uid/tempo'
marca = os.environ['MARCA']


def pedir(ruta):
    with urllib.request.urlopen(base + ruta, timeout=30) as r:
        return json.load(r)


def buscar(traceql):
    return pedir('/api/search?limit=20&q=' + urllib.parse.quote(traceql)).get('traces', [])


def tramos(traza):
    for lote in pedir('/api/traces/' + traza)['batches']:
        servicio = next(a['value']['stringValue'] for a in lote['resource']['attributes']
                        if a['key'] == 'service.name')
        for grupo in lote['scopeSpans']:
            for span in grupo['spans']:
                yield servicio, span


# Tempo tarda unos segundos en dejar buscar una traza recién terminada.
consulta = '{ resource.service.name = "backend-clinic" && name =~ "POST.*process.*" }'
for _ in range(30):
    encontradas = buscar(consulta)
    if encontradas:
        break
    time.sleep(2)
else:
    sys.exit('FALLA: Tempo no tiene ninguna traza de «procesar»')

ultima = max(encontradas, key=lambda t: int(t['startTimeUnixNano']))
vistos = list(tramos(ultima['traceID']))
servicios = {s for s, _ in vistos}
nombres = {span['name'] for _, span in vistos}

fallos = []
if not {'backend-clinic', 'backend-ml'} <= servicios:
    fallos.append(f'la traza no cruza los dos servicios: {sorted(servicios)}')
faltan = {'esperar_turno', 'segmentar', 'clasificar'} - nombres
if faltan:
    fallos.append(f'faltan los tramos {sorted(faltan)}')

# La búsqueda con la marca: su traza existe, y la marca no está en ella.
for _ in range(30):
    listas = buscar('{ resource.service.name = "backend-clinic" && name =~ "GET.*samples.*" }')
    if listas:
        break
    time.sleep(2)
else:
    fallos.append('Tempo no tiene la traza de la búsqueda')
for traza in listas:
    if marca in json.dumps(pedir('/api/traces/' + traza['traceID'])):
        fallos.append('el texto de búsqueda de la URL quedó guardado en una traza (RN-03)')
        break

if fallos:
    sys.exit('FALLA: ' + '; '.join(fallos))
print(f"ok: una traza de {ultima['durationMs']} ms con {len(vistos)} tramos, "
      f"servicios {sorted(servicios)}, y sin el texto de búsqueda")
EOF
