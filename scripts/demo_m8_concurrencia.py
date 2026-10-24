"""Demo 1 de M8 — issue #2: ¿backend-ml sigue respondiendo mientras segmenta?

    py -3.12 scripts/demo_m8_concurrencia.py --url http://localhost:8000
    py -3.12 scripts/demo_m8_concurrencia.py --url http://localhost:8010   # release/8.0.0

Lanza DOS segmentaciones reales a la vez (dos metafases del dataset) y, mientras
duran, consulta `/health/` cada 0,5 s. Imprime una línea de tiempo:

- Antes (release/8.0.0): la inferencia corría en un `async def` y congelaba el
  único event loop; `/health/` no contesta hasta que acaba la segmentación.
- Ahora (release/8.1.0): `/health/` contesta al momento; la segunda segmentación
  espera su turno o, si la espera supera ML_ESPERA_MAX_S, recibe 503 con
  Retry-After.

Antes de medir hace una llamada a `/health/` para que el modelo ya esté cargado
(~16 s la primera vez); si no, esa carga se confundiría con el bloqueo.
"""
from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
METAFASES = RAIZ / 'datasets' / 'metaclass' / 'metafases'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://localhost:8000')
    ap.add_argument('--metafases', nargs=2, default=['metafase_1.bmp', 'metafase_10.bmp'])
    opts = ap.parse_args()

    print(f'Servicio: {opts.url}')
    t = time.perf_counter()
    httpx.get(f'{opts.url}/health/', timeout=120)
    print(f'Calentamiento: modelo cargado ({time.perf_counter() - t:.1f} s)\n')

    origen = time.perf_counter()
    reloj = lambda: time.perf_counter() - origen   # noqa: E731
    lineas: list[tuple[float, str]] = []
    terminadas = threading.Event()
    candado = threading.Lock()

    def anotar(texto: str) -> None:
        with candado:
            lineas.append((reloj(), texto))
            print(f'  t={reloj():5.1f} s  {texto}', flush=True)

    def segmentar(nombre: str, n: int) -> None:
        datos = (METAFASES / nombre).read_bytes()
        anotar(f'segmentación {n}: enviada ({nombre})')
        t0 = reloj()
        try:
            r = httpx.post(f'{opts.url}/api/v1/segment/',
                           files={'file': (nombre, datos, 'image/bmp')}, timeout=120)
            extra = ''
            if r.status_code == 200:
                extra = f"{r.json()['chromosome_count']} cromosomas"
            elif 'retry-after' in r.headers:
                extra = f"Retry-After: {r.headers['retry-after']} s"
            anotar(f'segmentación {n}: {r.status_code} en {reloj() - t0:.1f} s  {extra}')
        except httpx.HTTPError as exc:
            anotar(f'segmentación {n}: ERROR {type(exc).__name__}')

    def vigilar_salud() -> None:
        while not terminadas.is_set():
            t0 = reloj()
            try:
                r = httpx.get(f'{opts.url}/health/', timeout=60)
                anotar(f'   /health/ {r.status_code} en {reloj() - t0:.2f} s')
            except httpx.HTTPError as exc:
                anotar(f'   /health/ ERROR {type(exc).__name__}')
            terminadas.wait(0.5)

    hilos = [threading.Thread(target=segmentar, args=(m, i + 1)) for i, m in enumerate(opts.metafases)]
    salud = threading.Thread(target=vigilar_salud)
    for h in hilos:
        h.start()
    time.sleep(0.3)                 # que las segmentaciones ya estén en marcha
    salud.start()
    for h in hilos:
        h.join()
    terminadas.set()
    salud.join()

    # Un ERROR no es "0 s de espera": se informa aparte. La primera versión los
    # omitía y daba 0,00 s justo cuando /health/ no había respondido nunca.
    salud_ok = [float(l.split(' en ')[1].split(' s')[0]) for _, l in lineas if '/health/ 200' in l]
    salud_mal = sum(1 for _, l in lineas if '/health/ ERROR' in l)
    if salud_ok:
        print(f'\n/health/ respondió {len(salud_ok)} veces; peor espera {max(salud_ok):.2f} s')
    if salud_mal or not salud_ok:
        print(f'/health/ NO respondió {salud_mal} veces (timeout de 60 s)')


if __name__ == '__main__':
    main()
