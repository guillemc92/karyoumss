"""Resume las corridas del E3 (DD-E3-001 D10): mediana y rango de cada cifra.

    py -3 bench/e3/resumir.py            tablas en Markdown, para INFORME.md

Lee `resultados/<forma>-<falla>-<n>.json` (resúmenes de k6) y
`resultados/tiempos.csv`. La carpeta `resultados/piloto/` no se cuenta.
"""
import csv
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

AQUI = Path(__file__).parent
RESULTADOS = AQUI / 'resultados'
RUTAS = ['bitacora', 'control']
FASES = ['antes', 'falla', 'despues']
NOMBRE = re.compile(r'^(proceso|http)-(sin-falla|colgado|caido|lento)-(\d+)\.json$')


def mediana_rango(valores: list[float], fmt='{:.1f}') -> str:
    if not valores:
        return '-'
    return f'{fmt.format(statistics.median(valores))} ({fmt.format(min(valores))}–{fmt.format(max(valores))})'


def leer_corridas():
    """{(forma, falla): [metrics de cada corrida]}"""
    corridas = defaultdict(list)
    for f in sorted(RESULTADOS.glob('*.json')):
        m = NOMBRE.match(f.name)
        if m:
            forma, falla, _ = m.groups()
            corridas[(forma, falla)].append(json.loads(f.read_text(encoding='utf-8'))['metrics'])
    return corridas


def cifra(metrics, que, ruta, fase):
    if que == 'p95':
        return metrics[f'http_req_duration{{ruta:{ruta},fase:{fase}}}']['values']['p(95)']
    return 100 * metrics[f'http_req_failed{{ruta:{ruta},fase:{fase}}}']['values']['rate']


def tabla_carga(corridas) -> str:
    filas = ['| Forma | Falla | Ruta | Fase | p95 (ms) | % errores | Corridas |', '|---|---|---|---|---:|---:|---:|']
    orden = [('proceso', 'sin-falla'), ('http', 'colgado'), ('http', 'caido'), ('http', 'lento')]
    for forma, falla in orden:
        lista = corridas.get((forma, falla), [])
        for ruta in RUTAS:
            for fase in FASES:
                p95 = [cifra(m, 'p95', ruta, fase) for m in lista]
                err = [cifra(m, 'err', ruta, fase) for m in lista]
                nombre_forma = 'En proceso' if forma == 'proceso' else 'Extraída'
                filas.append(f'| {nombre_forma} | {falla} | {ruta} | {fase} | {mediana_rango(p95)} | '
                             f'{mediana_rango(err)} | {len(lista)} |')
    return '\n'.join(filas)


def tabla_tiempos() -> str:
    datos = defaultdict(list)
    ruta = RESULTADOS / 'tiempos.csv'
    if not ruta.exists():
        return '(sin tiempos.csv)'
    with ruta.open(encoding='utf-8') as fh:
        for fila in csv.DictReader(fh):
            datos[(fila['que'], fila['forma'])].append(float(fila['segundos']))
    filas = ['| Qué | Forma | segundos: mediana (rango) | n |', '|---|---|---:|---:|']
    for que in ('build', 'seed', 'up'):
        for forma in ('proceso', 'http'):
            v = datos.get((que, forma), [])
            if v:
                filas.append(f'| {que} | {"En proceso" if forma == "proceso" else "Extraída"} | {mediana_rango(v)} | {len(v)} |')
    return '\n'.join(filas)


def main() -> int:
    corridas = leer_corridas()
    if not corridas:
        print('No hay resultados en', RESULTADOS)
        return 1
    print('## Carga\n')
    print(tabla_carga(corridas))
    print('\n## Tiempos de build, seed y arranque\n')
    print(tabla_tiempos())
    return 0


if __name__ == '__main__':
    sys.exit(main())
