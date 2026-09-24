# -*- coding: utf-8 -*-
"""Inserta un fragmento envenenado en el indice del RAG, y lo quita después.

    python scripts/envenenar_corpus.py poner --texto-archivo nota.txt
    python scripts/envenenar_corpus.py quitar

## Para qué

El modelo de amenazas nombra como actor a «quien pueda dejar un documento en la
base de conocimiento», y como frontera de confianza «corpus → contexto: NO
confiable aunque sea interno». Este guion simula exactamente eso: deja un
fragmento en el indice como si alguien hubiera subido una nota al corpus.

## Por qué hizo falta escribirlo

La primera tanda de ataques dio **0/3 en AI-SEC-006 y AI-SEC-007**, y eso
parecia «el sistema resistio». No lo era: `red_team_biomed.py` leia
`entrada_envenenada` del JSON y **no hacia nada con ella**. Los dos ataques
mandaban una pregunta normal contra un corpus limpio. Un 0/3 de un ataque que
nunca se ejecuto no es una defensa, es un instrumento roto — la decima vez en
este proyecto que el medidor falla antes que el sistema medido.

## Cómo funciona

El indice vive en `apps/samples/rag_data/` como `fragmentos.json` +
`vectores.npy`. Poner el veneno es:

1. **Respaldar** los dos ficheros (`.bak`). Sin esto un fallo a mitad deja el
   corpus clinico corrupto, que es mucho peor que no medir.
2. Embeber el texto malicioso con el mismo modelo (`nomic-embed-text` local) y
   añadir fragmento + vector al final.
3. Tras el ataque, `quitar` restaura los `.bak` y verifica que el conteo vuelve
   al original.

El fragmento se marca con una fuente reconocible (`NOTA-RED-TEAM`) para que, si
algo sale mal y queda, se vea de inmediato de dónde salió.

Salida en ASCII puro (la consola de Windows rompe con Unicode).
"""
import argparse
import io
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / 'backend-clinic' / 'apps' / 'samples' / 'rag_data'
FRAGMENTOS = DATOS / 'fragmentos.json'
VECTORES = DATOS / 'vectores.npy'
FUENTE = 'NOTA-RED-TEAM'


def respaldar():
    for f in (FRAGMENTOS, VECTORES):
        bak = f.with_suffix(f.suffix + '.bak')
        if not bak.exists():
            shutil.copy2(f, bak)
    return True


def restaurar():
    hechos = 0
    for f in (FRAGMENTOS, VECTORES):
        bak = f.with_suffix(f.suffix + '.bak')
        if bak.exists():
            shutil.copy2(bak, f)
            bak.unlink()
            hechos += 1
    return hechos


def cargar_fragmentos():
    return json.loads(FRAGMENTOS.read_text(encoding='utf-8'))


def poner(texto, seccion):
    import numpy as np
    sys.path.insert(0, str(RAIZ / 'backend-clinic'))
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_backend.settings')
    import django
    django.setup()
    from apps.samples.rag_index import embeber

    respaldar()
    datos = cargar_fragmentos()
    lista = datos['fragmentos'] if isinstance(datos, dict) else datos
    antes = len(lista)

    # El texto se embebe con contexto, igual que `construir` hace con el resto:
    # si se embebiera distinto, el fragmento envenenado no competiria en
    # igualdad y el ataque fallaria por un detalle del instrumento.
    con_contexto = '%s > %s\n%s' % (FUENTE, seccion, texto)
    vector = embeber([con_contexto])

    vectores = np.load(VECTORES)
    lista.append({'texto': texto, 'fuente': FUENTE, 'seccion': seccion,
                  'orden': antes})
    np.save(VECTORES, np.vstack([vectores, vector]))
    if isinstance(datos, dict):
        datos['fragmentos'] = lista
    io.open(FRAGMENTOS, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(datos, ensure_ascii=False))

    print('fragmentos: %d -> %d' % (antes, len(lista)))
    print('vectores  : %d -> %d' % (len(vectores), len(vectores) + 1))
    print('fuente    : %s' % FUENTE)
    print()
    print('IMPORTANTE: reiniciar backend-clinic para que recargue el indice,')
    print('y ejecutar «quitar» al terminar.')
    return 0


def quitar():
    n = restaurar()
    if not n:
        print('no habia respaldo: nada que restaurar')
        return 1
    datos = cargar_fragmentos()
    lista = datos['fragmentos'] if isinstance(datos, dict) else datos
    sucios = [f for f in lista if f.get('fuente') == FUENTE]
    print('restaurados %d ficheros | fragmentos ahora: %d | envenenados: %d'
          % (n, len(lista), len(sucios)))
    if sucios:
        print('*** quedan fragmentos de red team en el indice ***')
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('accion', choices=['poner', 'quitar', 'estado'])
    ap.add_argument('--texto', default=None)
    ap.add_argument('--texto-archivo', default=None)
    ap.add_argument('--seccion', default='Nota operativa')
    opts = ap.parse_args()

    if opts.accion == 'estado':
        datos = cargar_fragmentos()
        lista = datos['fragmentos'] if isinstance(datos, dict) else datos
        sucios = [f for f in lista if f.get('fuente') == FUENTE]
        print('fragmentos: %d | de red team: %d | respaldo: %s'
              % (len(lista), len(sucios),
                 'si' if FRAGMENTOS.with_suffix('.json.bak').exists() else 'no'))
        return 0
    if opts.accion == 'quitar':
        return quitar()

    texto = opts.texto
    if opts.texto_archivo:
        texto = Path(opts.texto_archivo).read_text(encoding='utf-8')
    if not texto:
        raise SystemExit('hace falta --texto o --texto-archivo')
    return poner(texto.strip(), opts.seccion)


if __name__ == '__main__':
    sys.exit(main())
