# -*- coding: utf-8 -*-
"""Evals offline del asistente documental de BIOMED — M7, Dia 10.

    python evals/evaluar.py correr v3          # puntua y decide: exit 0 = PASA, 1 = NO PASA
    python evals/evaluar.py comparar v1 v2
    python evals/evaluar.py generar v3         # pregunta al modelo (necesita Ollama)
    python evals/evaluar.py plantilla v2       # hoja para calificar a mano
    python evals/evaluar.py calibrar v2        # acuerdo y kappa juez vs humano

Se ejecuta desde la carpeta raiz de la entrega (la que contiene `dataset/`,
`respuestas/`, `evals/` y `evidencia/`).

## La funcion que se mide, en una linea

    Responder consultas sobre las reglas y procedimientos del laboratorio
    usando SOLO la documentacion entregada, con las cifras exactas, y
    abstenerse ante datos de pacientes, temas ajenos o datos que no estan.

Es el paso de GENERACION de `rag_qa.responder_documental` (backend-clinic):
mismo modelo (`llama3.2:3b`), mismo esquema JSON de salida, temperatura 0 y
el mismo formato de mensaje (`FRAGMENTOS: [n] fuente — seccion ... PREGUNTA:`).
La recuperacion queda fuera a proposito, igual que en el laboratorio: cada
caso trae su contexto fijo, de modo que un fallo es de la funcion y no de que
el buscador trajera el fragmento equivocado. La recuperacion ya se mide aparte
(`eval_rag`, M6).

## Dependencias

`correr`, `comparar`, `plantilla` y `calibrar` usan solo la biblioteca
estandar de Python: puntuan las respuestas GRABADAS, sin modelo y sin red. Solo
`generar` necesita `pip install openai` y un Ollama local con el modelo.

Salida en ASCII: la consola de Windows (cp1252) rompe con Unicode.
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATASET = RAIZ / 'dataset' / 'dataset_dorado.jsonl'
ETIQUETAS = RAIZ / 'dataset' / 'etiquetas_humanas.csv'
RESPUESTAS = RAIZ / 'respuestas'
EVIDENCIA = RAIZ / 'evidencia'
PROMPTS = RAIZ / 'evals' / 'prompts'
UMBRALES = RAIZ / 'evals' / 'umbrales.json'

# Esquema de salida: identico al de produccion (rag_qa.RESPUESTA_SCHEMA).
ESQUEMA = {
    'type': 'json_schema',
    'json_schema': {
        'name': 'respuesta_documental',
        'strict': True,
        'schema': {
            'type': 'object',
            'properties': {
                'responde': {'type': 'boolean'},
                'respuesta': {'type': 'string'},
                'fuentes': {'type': 'array', 'items': {'type': 'integer'}},
            },
            'required': ['responde', 'respuesta', 'fuentes'],
            'additionalProperties': False,
        },
    },
}


#: Para las versiones en las que la APLICACION decide las abstenciones: el
#: modelo no puede devolver `responde`, solo lo que extrae. Quitar el campo
#: del esquema es mas fuerte que pedirle en el prompt que no se abstenga —
#: medido: con el campo disponible, el borrador 3 de v3 se abstuvo en 7 de las
#: 9 preguntas que el contexto respondia.
ESQUEMA_SOLO_EXTRAE = {
    'type': 'json_schema',
    'json_schema': {
        'name': 'extraccion_documental',
        'strict': True,
        'schema': {
            'type': 'object',
            'properties': {
                'respuesta': {'type': 'string'},
                'fuentes': {'type': 'array', 'items': {'type': 'integer'}},
            },
            'required': ['respuesta', 'fuentes'],
            'additionalProperties': False,
        },
    },
}


#: Modo seleccion (v3): el modelo no redacta, elige oraciones numeradas.
ESQUEMA_SELECCION = {
    'type': 'json_schema',
    'json_schema': {
        'name': 'seleccion_de_oraciones',
        'strict': True,
        'schema': {
            'type': 'object',
            'properties': {'oraciones': {'type': 'array', 'items': {'type': 'integer'}}},
            'required': ['oraciones'],
            'additionalProperties': False,
        },
    },
}


def segmentar(caso):
    """Parte el contexto en oraciones con su texto LITERAL.

    Primero por bloque (linea en blanco, o una linea que abre elemento de
    lista, fila de tabla, encabezado o regla RN-), uniendo las lineas de un
    mismo bloque: el markdown de los ADR corta frases a mitad con saltos de
    linea, y sin esto la regla de segregacion de EV-09 quedaba partida en dos
    oraciones que por separado no decian nada. Despues por celda de tabla y
    por fin de oracion. Solo se normalizan espacios; el texto es el del
    documento.
    """
    unidades = []
    for x in caso['contexto']:
        bloques = re.split(r'\n\s*\n|\n(?=\s*(?:[-*|#]|RN-\d|\d+\.\s))', x['texto'])
        for bloque in bloques:
            linea = ' '.join(bloque.split())
            for celda in linea.split(' | '):
                for o in re.split(r'(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÑ¿(`*\-])', celda):
                    o = o.strip().strip('|').strip()
                    if len(o) >= 3:
                        unidades.append(o)
    return unidades


# ==========================================================================
# carga
# ==========================================================================
def casos():
    with io.open(DATASET, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


def respuestas(version):
    ruta = RESPUESTAS / ('%s.jsonl' % version)
    if not ruta.exists():
        raise SystemExit('no existe %s: genera primero con «generar %s»'
                         % (ruta.relative_to(RAIZ), version))
    with io.open(ruta, encoding='utf-8') as f:
        return {r['id']: r for r in (json.loads(l) for l in f if l.strip())}


def umbrales():
    return json.loads(UMBRALES.read_text(encoding='utf-8'))


def contexto_texto(caso):
    """Lo que el asistente tenia delante: el mismo texto que ve el juez."""
    return '\n\n'.join(x['texto'] for x in caso['contexto'])


# ==========================================================================
# normalizacion (misma idea que el laboratorio)
# ==========================================================================
VACIAS = set("""
a al algo ante como con cual cuando de del desde donde el ella en entre era es esa ese eso esta este esto
fue ha hay la las le les lo los mas me mi mis muy no nos o para pero por que se si sin sobre su sus te tu
tus un una uno unos unas y ya yo puede pueden puedes debe deben tiene tienen son ser esta estan caso
""".split())

#: Frases de gestion: no afirman hechos del laboratorio (rechazar, derivar).
#: La rubrica las cuenta como respaldadas si no llevan cifras.
FRASES_GESTION = ('no puedo', 'no tengo informacion', 'no encuentro', 'no dispongo',
                  'no se menciona', 'no aparece', 'consulte', 'consultar con')


def plano(texto):
    t = unicodedata.normalize('NFD', (texto or '').lower())
    return ''.join(c for c in t if unicodedata.category(c) != 'Mn')


def oraciones(texto):
    partes = re.split(r'(?<=[.;!?])\s+|\n+', (texto or '').strip())
    return [p.strip() for p in partes if p.strip()]


def palabras(texto):
    return [p for p in re.findall(r'[a-z0-9_]+', plano(texto))
            if p not in VACIAS and len(p) > 2]


def numeros(texto):
    return re.findall(r'\d+', texto or '')


def cumple(patron, texto):
    """Punto clave o prohibida. `a|b` = alternativas; `re:` = expresion regular.

    El `re:` existe por las negaciones: «puedes emitir» es prohibido y «no
    puedes emitir» es la respuesta correcta. Una lista de subcadenas no los
    distingue; `(?<!no )puedes? emitir` si.
    """
    t = plano(texto)
    if patron.startswith('re:'):
        return re.search(plano(patron[3:]), t) is not None
    return any(plano(a.strip()) in t for a in patron.split('|') if a.strip())


# ==========================================================================
# el juez de fidelidad — rubrica escrita en evals/rubrica_juez.md
# ==========================================================================
UMBRAL_PALABRAS = 0.5


def juzgar(respuesta, contexto):
    """Devuelve (puntaje 0..1 o None, [(oracion, respaldada, motivo)]).

    Rubrica (evals/rubrica_juez.md):
      R1. Se divide la respuesta en oraciones.
      R2. Una frase de gestion sin cifras («no puedo…», «consulte…») cuenta
          como respaldada: no afirma nada del laboratorio.
      R3. Cualquier otra oracion esta respaldada solo si TODOS sus numeros
          aparecen en el contexto — inventar una cifra es la alucinacion que
          mas dano hace en un informe clinico — y
      R4. al menos la mitad de sus palabras de contenido aparecen en el
          contexto.
      R5. Fidelidad = oraciones respaldadas / oraciones totales.
    """
    ctx = plano(contexto)
    vocab = set(palabras(contexto))
    detalle = []
    for o in oraciones(respuesta):
        if any(f in plano(o) for f in FRASES_GESTION) and not numeros(o):
            detalle.append((o, True, 'R2 gestion'))
            continue
        faltan = [n for n in numeros(o) if n not in ctx]
        ps = palabras(o)
        prop = (sum(p in vocab for p in ps) / len(ps)) if ps else 1.0
        if faltan:
            detalle.append((o, False, 'R3 cifra ausente: %s' % ', '.join(faltan)))
        elif prop < UMBRAL_PALABRAS:
            detalle.append((o, False, 'R4 apoyo %.2f' % prop))
        else:
            detalle.append((o, True, 'R4 apoyo %.2f' % prop))
    if not detalle:
        return None, []
    return sum(1 for _, ok, _ in detalle if ok) / len(detalle), detalle


# ==========================================================================
# metricas por caso
# ==========================================================================
def puntuar_caso(c, r):
    texto = r.get('respuesta') or ''
    responde = bool(r.get('responde'))
    prohibidas = [p for p in c.get('prohibidas', []) if cumple(p, texto)]
    fila = {'id': c['id'], 'tipo': c['tipo'], 'critico': c['critico'],
            'responde': responde, 'texto': texto,
            'sin_prohibidos': 0.0 if prohibidas else 1.0,
            'prohibidas_halladas': prohibidas, 'faltan': [], 'detalle': []}

    if c.get('abstenerse'):
        # Lo esperado es no responder. Se expresa en las tres metricas para
        # que el caso compita en los mismos promedios que los demas:
        #   completitud = se abstuvo;  fidelidad = 1 si no afirmo nada.
        fila['completitud'] = 0.0 if responde else 1.0
        if responde:
            fid, det = juzgar(texto, contexto_texto(c))
            fila['fidelidad'] = fid if fid is not None else 1.0
            fila['detalle'] = det
            fila['faltan'] = ['abstenerse (respondio)']
        else:
            fila['fidelidad'] = 1.0
    else:
        if not responde:
            # Se callo en una pregunta que el contexto SI responde: no dijo
            # nada falso (fidelidad 1) pero no cubrio nada (completitud 0).
            fila['completitud'] = 0.0
            fila['fidelidad'] = 1.0
            fila['faltan'] = ['se abstuvo'] + c['puntos_clave']
        else:
            faltan = [p for p in c['puntos_clave'] if not cumple(p, texto)]
            n = len(c['puntos_clave'])
            fila['completitud'] = (n - len(faltan)) / n if n else 1.0
            fila['faltan'] = faltan
            fid, det = juzgar(texto, contexto_texto(c))
            fila['fidelidad'] = fid if fid is not None else 0.0
            fila['detalle'] = det

    fila['ok'] = (fila['completitud'] == 1.0 and fila['sin_prohibidos'] == 1.0
                  and fila['fidelidad'] == 1.0)
    return fila


def puntuar(version):
    rs = respuestas(version)
    filas = []
    for c in casos():
        if c['id'] not in rs:
            raise SystemExit('falta %s en respuestas/%s.jsonl' % (c['id'], version))
        filas.append(puntuar_caso(c, rs[c['id']]))
    return filas, rs


def compuerta(filas, u):
    media = lambda k: sum(f[k] for f in filas) / len(filas)       # noqa: E731
    comp, fid, sp = media('completitud'), media('fidelidad'), media('sin_prohibidos')
    crit = [f for f in filas if f['critico']]
    crit_mal = [f['id'] for f in crit if not f['ok']]
    razones = []
    if comp < u['completitud_minima']:
        razones.append('completitud %.3f < %.2f' % (comp, u['completitud_minima']))
    if fid < u['fidelidad_minima']:
        razones.append('fidelidad %.3f < %.2f' % (fid, u['fidelidad_minima']))
    if sp < u['sin_prohibidos_minimo']:
        razones.append('sin_prohibidos %.3f < %.2f' % (sp, u['sin_prohibidos_minimo']))
    if len(crit_mal) > u['criticos_fallados_max']:
        razones.append('criticos fallados: %s' % ', '.join(crit_mal))
    return {'completitud': comp, 'fidelidad': fid, 'sin_prohibidos': sp,
            'criticos': len(crit), 'criticos_ok': len(crit) - len(crit_mal),
            'pasa': not razones, 'razones': razones}


# ==========================================================================
# comandos
# ==========================================================================
def cmd_correr(version):
    filas, rs = puntuar(version)
    u = umbrales()
    g = compuerta(filas, u)

    print('=' * 64)
    print(' EVALS BIOMED  version %s  (%d casos, %d criticos)'
          % (version, len(filas), g['criticos']))
    print('=' * 64)
    print(' caso   tipo              crit resp  compl  fidel  proh  ok')
    for f in filas:
        print(' %-6s %-17s %-4s %-5s %5.2f  %5.2f  %-4s  %s' % (
            f['id'], f['tipo'], 'si' if f['critico'] else '',
            'si' if f['responde'] else 'abst', f['completitud'], f['fidelidad'],
            'ok' if f['sin_prohibidos'] == 1.0 else 'MAL', 'OK' if f['ok'] else 'falla'))
    print('-' * 64)
    print(' completitud    %.3f   (minimo %.2f)' % (g['completitud'], u['completitud_minima']))
    print(' fidelidad      %.3f   (minimo %.2f)' % (g['fidelidad'], u['fidelidad_minima']))
    print(' sin_prohibidos %.3f   (minimo %.2f)' % (g['sin_prohibidos'], u['sin_prohibidos_minimo']))
    print(' criticos       %d/%d   (fallados permitidos: %d)'
          % (g['criticos_ok'], g['criticos'], u['criticos_fallados_max']))
    print('-' * 64)
    for r in g['razones']:
        print(' motivo: %s' % r)
    codigo = 0 if g['pasa'] else 1
    print(' COMPUERTA: %s   (codigo de salida %d)' % ('PASA' if g['pasa'] else 'NO PASA', codigo))
    print('=' * 64)

    EVIDENCIA.mkdir(exist_ok=True)
    (EVIDENCIA / ('informe_%s.md' % version)).write_text(
        informe(version, filas, g, rs, u), encoding='utf-8')
    return codigo


def informe(version, filas, g, rs, u):
    L = ['# Informe de la corrida %s' % version, '',
         '| Metrica | Valor | Umbral |', '|---|---|---|',
         '| completitud | %.3f | >= %.2f |' % (g['completitud'], u['completitud_minima']),
         '| fidelidad | %.3f | >= %.2f |' % (g['fidelidad'], u['fidelidad_minima']),
         '| sin prohibidos | %.3f | = %.2f |' % (g['sin_prohibidos'], u['sin_prohibidos_minimo']),
         '| criticos perfectos | %d/%d | todos |' % (g['criticos_ok'], g['criticos']),
         '', '**Compuerta: %s (codigo %d)**' % ('PASA' if g['pasa'] else 'NO PASA',
                                               0 if g['pasa'] else 1), '',
         '| Caso | Tipo | Critico | Responde | Completitud | Fidelidad | Prohibidas | OK |',
         '|---|---|---|---|---|---|---|---|']
    for f in filas:
        L.append('| %s | %s | %s | %s | %.2f | %.2f | %s | %s |' % (
            f['id'], f['tipo'], 'si' if f['critico'] else '', 'si' if f['responde'] else 'no',
            f['completitud'], f['fidelidad'], 'ninguna' if f['sin_prohibidos'] == 1 else
            ', '.join('`%s`' % p for p in f['prohibidas_halladas']), 'OK' if f['ok'] else 'falla'))
    fallos = [f for f in filas if not f['ok']]
    if fallos:
        L += ['', '## Casos que fallan', '']
        for f in fallos:
            L.append('**%s** (%s%s) — respuesta: «%s»' % (
                f['id'], f['tipo'], ', critico' if f['critico'] else '',
                (f['texto'] or '(se abstuvo)')[:220].replace('\n', ' ')))
            if f['faltan']:
                L.append('- falta: %s' % '; '.join('`%s`' % x for x in f['faltan']))
            for o, ok, motivo in f['detalle']:
                if not ok:
                    L.append('- sin respaldo (%s): «%s»' % (motivo, o[:140]))
            L.append('')
    tok = sum((r.get('tokens_entrada') or 0) + (r.get('tokens_salida') or 0) for r in rs.values())
    lat = sum(r.get('latencia_ms') or 0 for r in rs.values()) / 60000.0
    L += ['', '## Coste de la corrida completa', '',
          '| Llamadas al modelo | Tokens | Tiempo | Llamadas al juez | Dinero |',
          '|---|---|---|---|---|',
          '| %d | %d | %.1f min | 0 (juez sin modelo) | 0 (modelo local) |'
          % (len(rs), tok, lat)]
    return '\n'.join(L) + '\n'


def cmd_comparar(a, b):
    u = umbrales()
    res = {}
    for v in (a, b):
        filas, _ = puntuar(v)
        res[v] = (filas, compuerta(filas, u))
    print('%-16s %10s %10s' % ('', a, b))
    for k in ('completitud', 'fidelidad', 'sin_prohibidos'):
        print('%-16s %10.3f %10.3f' % (k, res[a][1][k], res[b][1][k]))
    print('%-16s %10s %10s' % ('criticos ok', '%d/%d' % (res[a][1]['criticos_ok'], res[a][1]['criticos']),
                               '%d/%d' % (res[b][1]['criticos_ok'], res[b][1]['criticos'])))
    print('%-16s %10s %10s' % ('compuerta', 'PASA' if res[a][1]['pasa'] else 'NO PASA',
                               'PASA' if res[b][1]['pasa'] else 'NO PASA'))
    oka = {f['id']: f['ok'] for f in res[a][0]}
    okb = {f['id']: f['ok'] for f in res[b][0]}
    print('\nmejoran de %s a %s : %s' % (a, b, ', '.join(i for i in oka if not oka[i] and okb[i]) or 'ninguno'))
    print('empeoran de %s a %s: %s' % (a, b, ', '.join(i for i in oka if oka[i] and not okb[i]) or 'ninguno'))
    return 0


def config_version(version):
    """Que lleva cada version: el prompt y si la aplicacion decide las
    abstenciones (evals/versiones.json)."""
    conf = json.loads((RAIZ / 'evals' / 'versiones.json').read_text(encoding='utf-8'))
    if version not in conf:
        raise SystemExit('%s no esta declarada en evals/versiones.json' % version)
    return conf[version]


def cmd_generar(version):
    from openai import OpenAI
    sys.path.insert(0, str(RAIZ / 'evals'))
    from guarda import motivo_abstencion
    conf = config_version(version)
    url = os.getenv('EVALS_LLM_URL', 'http://localhost:11434/v1')
    modelo = os.getenv('EVALS_LLM_MODEL', 'llama3.2:3b')
    sistema = (PROMPTS / conf['prompt']).read_text(encoding='utf-8').strip()
    cliente = OpenAI(base_url=url, api_key='ollama', timeout=300.0)
    salida, t0 = [], time.time()
    lista = casos()
    for n, c in enumerate(lista, 1):
        motivo = motivo_abstencion(c['pregunta']) if conf['guarda'] else None
        if motivo:
            # La aplicacion decide: la pregunta no llega al modelo.
            fila = {'id': c['id'], 'version': version, 'modelo': 'guarda (sin llamada)',
                    'responde': False, 'respuesta': '', 'fuentes': [],
                    'tokens_entrada': 0, 'tokens_salida': 0, 'latencia_ms': 0,
                    'error': '', 'guarda': motivo}
            salida.append(fila)
            print('  [%2d/%d] %s ABSTIENE   guarda: %s' % (n, len(lista), c['id'], motivo))
            continue
        seleccion = conf.get('modo') == 'seleccion'
        if seleccion:
            unidades = segmentar(c)
            usuario = 'ORACIONES:\n%s\n\nPREGUNTA: %s' % (
                '\n'.join('[%d] %s' % (i, o) for i, o in enumerate(unidades, 1)), c['pregunta'])
        else:
            bloques = []
            for i, x in enumerate(c['contexto'], 1):
                donde = x['fuente'] + (' — ' + x['seccion'] if x['seccion'] else '')
                bloques.append('[%d] %s\n%s' % (i, donde, x['texto']))
            usuario = 'FRAGMENTOS:\n\n%s\n\nPREGUNTA: %s' % ('\n\n'.join(bloques), c['pregunta'])
        ini = time.time()
        try:
            decide = conf.get('modelo_decide_abstencion', True)
            esquema = ESQUEMA_SELECCION if seleccion else (ESQUEMA if decide else ESQUEMA_SOLO_EXTRAE)
            r = cliente.chat.completions.create(
                model=modelo, temperature=0.0, max_tokens=500, response_format=esquema,
                messages=[{'role': 'system', 'content': sistema},
                          {'role': 'user', 'content': usuario}])
            d = json.loads(r.choices[0].message.content or '{}')
            if seleccion:
                # La aplicacion escribe: copia literal de lo elegido, en el
                # orden del documento. Numeros fuera de rango se ignoran en vez
                # de inventar una oracion.
                elegidas = sorted({n for n in d.get('oraciones', [])
                                   if isinstance(n, int) and 1 <= n <= len(unidades)})
                d = {'respuesta': ' '.join(unidades[n - 1] for n in elegidas),
                     'fuentes': elegidas}
            if seleccion or not decide:
                # Llego al modelo porque la guarda lo dejo pasar: se responde.
                d['responde'] = bool((d.get('respuesta') or '').strip())
            uso = getattr(r, 'usage', None)
            te, ts = (getattr(uso, 'prompt_tokens', 0) or 0), (getattr(uso, 'completion_tokens', 0) or 0)
            error = ''
        except Exception as exc:                          # noqa: BLE001
            # Un fallo del modelo se graba como tal: no se reintenta en
            # silencio ni se sustituye por una respuesta inventada.
            d, te, ts, error = {'responde': False, 'respuesta': ''}, 0, 0, str(exc)[:200]
        fila = {'id': c['id'], 'version': version, 'modelo': modelo,
                'responde': bool(d.get('responde')),
                'respuesta': (d.get('respuesta') or '').strip() if d.get('responde') else '',
                'fuentes': d.get('fuentes', []), 'tokens_entrada': te, 'tokens_salida': ts,
                'latencia_ms': int((time.time() - ini) * 1000), 'error': error}
        salida.append(fila)
        print('  [%2d/%d] %s %-9s %4.0fs  %s' % (n, len(lista), c['id'],
              'responde' if fila['responde'] else 'ABSTIENE', time.time() - ini,
              (fila['respuesta'] or error)[:60].encode('ascii', 'replace').decode()))
        sys.stdout.flush()
    RESPUESTAS.mkdir(exist_ok=True)
    ruta = RESPUESTAS / ('%s.jsonl' % version)
    with io.open(ruta, 'w', encoding='utf-8', newline='\n') as f:
        for fila in salida:
            f.write(json.dumps(fila, ensure_ascii=False) + '\n')
    print('escrito %s  (%.1f min)' % (ruta.relative_to(RAIZ), (time.time() - t0) / 60))
    return 0


CAMPOS = ['version', 'caso', 'pregunta', 'respuesta', 'fiel', 'anotador', 'nota']


def cmd_plantilla(version):
    """Hoja para calificar a mano, UNA fila por caso. No se rellena sola:
    calibrar es comparar al juez con una persona."""
    rs = respuestas(version)
    with io.open(ETIQUETAS, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        for c in casos():
            r = rs[c['id']]
            w.writerow({'version': version, 'caso': c['id'], 'pregunta': c['pregunta'],
                        'respuesta': r.get('respuesta') or '(se abstuvo)',
                        'fiel': '', 'anotador': '', 'nota': ''})
    print('escrito %s — marca fiel=1/0 en al menos 6 casos' % ETIQUETAS.relative_to(RAIZ))
    return 0


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(v) / n) * (b.count(v) / n) for v in (0, 1))
    return po, (None if pe == 1 else (po - pe) / (1 - pe))


def cmd_calibrar(version):
    if not ETIQUETAS.exists():
        raise SystemExit('no hay %s: corre «plantilla %s»' % (ETIQUETAS.relative_to(RAIZ), version))
    # Excel en configuracion regional espanola guarda con «;» y, si no se elige
    # «CSV UTF-8», en la codificacion de Windows. Se aceptan las dos cosas: la
    # hoja la rellena una persona con la herramienta que tenga a mano.
    crudo = ETIQUETAS.read_bytes()
    try:
        texto = crudo.decode('utf-8-sig')
    except UnicodeDecodeError:
        texto = crudo.decode('cp1252')
    muestra = texto[:2048]
    lector = csv.DictReader(io.StringIO(texto),
                            delimiter=';' if muestra.count(';') > muestra.count(',') else ',')
    etiquetas = [e for e in lector if (e.get('fiel') or '').strip() in ('0', '1')]
    if len(etiquetas) < 6:
        raise SystemExit('hay %d casos calificados; la consigna pide al menos 6' % len(etiquetas))
    humano, juez, desacuerdos = [], [], []
    por_version = {}
    for e in etiquetas:
        v = e.get('version') or version
        if v not in por_version:
            por_version[v] = {c['id']: puntuar_caso(c, respuestas(v)[c['id']]) for c in casos()}
        f = por_version[v][e['caso']]
        h, j = int(e['fiel']), 1 if f['fidelidad'] == 1.0 else 0
        humano.append(h)
        juez.append(j)
        if h != j:
            desacuerdos.append((v, e['caso'], h, j, (e.get('nota') or '').strip()))
    po, k = kappa(humano, juez)
    print('casos calificados a mano : %d' % len(humano))
    print('acuerdo                  : %.1f %%' % (po * 100))
    print('kappa de Cohen           : %s' % ('%.3f' % k if k is not None else 'indefinida (sin variacion)'))
    for v, c, h, j, nota in desacuerdos:
        print('  desacuerdo %s %s: humano=%s juez=%s  %s' % (
            v, c, 'fiel' if h else 'no fiel', 'fiel' if j else 'no fiel', nota))
    EVIDENCIA.mkdir(exist_ok=True)
    L = ['# Calibracion del juez', '',
         '| Casos calificados a mano | Acuerdo | Kappa de Cohen |', '|---|---|---|',
         '| %d | %.1f %% | %s |' % (len(humano), po * 100, '%.3f' % k if k is not None else 'indefinida'),
         '', '| Version | Caso | Humano | Juez | Nota |', '|---|---|---|---|---|']
    for v, c, h, j, nota in desacuerdos:
        L.append('| %s | %s | %s | %s | %s |' % (v, c, 'fiel' if h else 'no fiel',
                                                 'fiel' if j else 'no fiel', nota))
    if not desacuerdos:
        L.append('| — | — | — | — | sin desacuerdos |')
    (EVIDENCIA / 'calibracion.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    return 0


def main():
    ap = argparse.ArgumentParser(description='Evals offline BIOMED')
    ap.add_argument('comando', choices=['correr', 'comparar', 'generar', 'plantilla', 'calibrar'])
    ap.add_argument('version')
    ap.add_argument('otra', nargs='?')
    o = ap.parse_args()
    if o.comando == 'correr':
        return cmd_correr(o.version)
    if o.comando == 'comparar':
        if not o.otra:
            raise SystemExit('comparar necesita dos versiones')
        return cmd_comparar(o.version, o.otra)
    if o.comando == 'generar':
        return cmd_generar(o.version)
    if o.comando == 'plantilla':
        return cmd_plantilla(o.version)
    return cmd_calibrar(o.version)


if __name__ == '__main__':
    sys.exit(main())
