# -*- coding: utf-8 -*-
"""Evaluacion offline del asistente documental de BIOMED — M7, Dia 10.

    python scripts/eval_calidad.py generar v2      # pregunta al sistema real
    python scripts/eval_calidad.py correr v2       # puntua lo generado
    python scripts/eval_calidad.py comparar v1 v2
    python scripts/eval_calidad.py plantilla v2    # CSV para etiquetar a mano
    python scripts/eval_calidad.py calibrar v2     # acuerdo y kappa

## Que se mide, y por que no basta con «funciona»

`eval_rag` ya media si el RAG **recupera** el documento correcto. Eso no dice
nada de la respuesta que ve el analista: un sistema puede recuperar el ADR
adecuado y aun asi contestar media verdad, o colar una cifra que no esta en
ninguna parte. Aqui se mide la RESPUESTA, contra un dataset dorado con lo que
debe y lo que no debe decir.

## Las tres metricas, y la cuarta que este sistema permite

- **Completitud** (determinista) — fraccion de lo que *debe* decir que dice.
  `'0.85|0,85|85 %'` son alternativas de la misma exigencia.
- **Sin prohibidos** (determinista) — 0 si aparece algo que *no debe* decir.
- **Fidelidad** (juez) — oraciones respaldadas por los fragmentos recuperados
  entre oraciones totales. Una cifra que no esta en las fuentes no se respalda.
- **Abstencion** (determinista) — para los casos que NO deben responderse.

La cuarta es propia. El laboratorio mide la abstencion buscando «no se» en el
texto, porque su asistente siempre emite texto. El de BIOMED devuelve un
booleano `responde` y un texto vacio, asi que se comprueba el booleano: es mas
estricto que buscar una frase y no se rompe si cambia la redaccion. Es la misma
regla que el red teaming de M9 — criterio observable, nunca igualdad de texto.

## Por que la generacion y la puntuacion estan separadas

`generar` habla con el modelo y graba; `correr` puntua lo grabado. Asi la
puntuacion es reproducible sin Ollama y sin esperar 40 minutos, y dos personas
que puntuan la misma corrida obtienen el mismo numero. Es lo mismo que hace el
laboratorio al repartir `respuestas/*.jsonl` ya grabadas.

Salida en ASCII puro: la consola de Windows (cp1252) rompe con Unicode.
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
BASE = RAIZ / 'docs' / 'M7_EVALS'
DATASET = BASE / 'datos' / 'dataset_dorado.jsonl'
ETIQUETAS = BASE / 'datos' / 'etiquetas_humanas.csv'
UMBRALES = BASE / 'umbrales.json'

#: Cuanta parte de las palabras con contenido de una oracion debe aparecer en
#: los fragmentos para darla por respaldada. No sale de una intuicion: se
#: calibra contra las etiquetas humanas (`calibrar`) y se ajusta si el acuerdo
#: es bajo. Mientras no se calibre, es una suposicion declarada.
APOYO_MINIMO = 0.55
#: Palabras por debajo de esta longitud no cuentan como contenido: «de», «que»,
#: «los» aparecen en cualquier fragmento y darian por respaldada cualquier
#: oracion.
LARGO_PALABRA = 5


# --------------------------------------------------------------------------
# carga
# --------------------------------------------------------------------------
def casos():
    with io.open(DATASET, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


def umbrales():
    return json.loads(io.open(UMBRALES, encoding='utf-8').read())


def ruta_respuestas(version):
    return BASE / 'respuestas' / ('%s.jsonl' % version)


def respuestas(version):
    ruta = ruta_respuestas(version)
    if not ruta.exists():
        raise SystemExit('no hay respuestas de %s: corre primero '
                         '«generar %s»' % (version, version))
    with io.open(ruta, encoding='utf-8') as f:
        return {r['id']: r for r in (json.loads(l) for l in f if l.strip())}


def prompt_de(version):
    ruta = BASE / 'prompts' / ('%s.txt' % version)
    if not ruta.exists():
        raise SystemExit('no existe %s' % ruta)
    return io.open(ruta, encoding='utf-8').read().strip()


# --------------------------------------------------------------------------
# normalizacion
# --------------------------------------------------------------------------
def plano(texto):
    """Minusculas sin acentos. El modelo acentua de forma inconsistente y una
    comparacion sensible a la tilde mediria ortografia, no contenido."""
    t = unicodedata.normalize('NFD', (texto or '').lower())
    return ''.join(c for c in t if unicodedata.category(c) != 'Mn')


def aparece(patron, texto):
    """¿Se cumple `patron` sobre `texto`?

    Por defecto es coincidencia de subcadena con alternativas separadas por `|`:
    basta con una. Un patron que empieza por `re:` se trata como expresion
    regular sobre el texto ya normalizado.

    **Por que hizo falta el regex.** La lista de prohibidos de EV-007 decia
    `puede firmarlo`, y v3 escribio «El mismo usuario puede analizar un caso y
    firmarlo» — afirmando lo contrario de RN-06 sin activar la metrica, porque
    la subcadena literal no estaba. Y no se arregla anadiendo `puede firmar`:
    eso saltaria tambien sobre la respuesta CORRECTA, «no puede firmar». Una
    lista de subcadenas no sabe de negaciones; hace falta poder escribir
    «puede firmar NO precedido de no».
    """
    t = plano(texto)
    if patron.startswith('re:'):
        return re.search(plano(patron[3:]), t) is not None
    return any(plano(alt.strip()) in t for alt in patron.split('|')
               if alt.strip())


# --------------------------------------------------------------------------
# metricas deterministas
# --------------------------------------------------------------------------
def completitud(caso, texto):
    exigencias = caso.get('debe_decir') or []
    if not exigencias:
        return None, []
    faltan = [p for p in exigencias if not aparece(p, texto)]
    return (len(exigencias) - len(faltan)) / len(exigencias), faltan


def sin_prohibidos(caso, texto):
    prohibidos = caso.get('no_debe_decir') or []
    encontrados = [p for p in prohibidos if aparece(p, texto)]
    return (0.0 if encontrados else 1.0), encontrados


# --------------------------------------------------------------------------
# juez de fidelidad
# --------------------------------------------------------------------------
def oraciones(texto):
    """Trocea la respuesta en afirmaciones juzgables.

    El corte por longitud descarta restos de puntuacion, pero se comio
    respuestas enteras: a «que umbral separa el verde del naranja?» el sistema
    contesta «0.85» —correcta y completa— y con el filtro de 15 caracteres se
    quedaba sin ninguna oracion, asi que su fidelidad salia «sin medir». Una
    respuesta corta no es una respuesta vacia: si nada supera el corte pero hay
    texto, el texto entero cuenta como una afirmacion.
    """
    texto = (texto or '').strip()
    partes = re.split(r'(?<=[.;:!?])\s+|\n+', texto)
    largas = [p.strip() for p in partes if len(p.strip()) > 15]
    if largas:
        return largas
    return [texto] if texto else []


def _contenido(frase):
    palabras = re.findall(r'[a-z0-9_\-]+', plano(frase))
    return [p for p in palabras if len(p) >= LARGO_PALABRA]


def _cifras(frase):
    return re.findall(r'\d+(?:[.,]\d+)?\s?%?', frase or '')


class JuezHeuristico:
    """Sin modelo, determinista, reproducible.

    Una oracion esta respaldada si (a) todas sus cifras aparecen en los
    fragmentos y (b) al menos `APOYO_MINIMO` de sus palabras con contenido
    tambien. La regla de las cifras va primero a proposito: inventar un numero
    es el fallo que mas dano hace en un informe clinico, y es el unico que se
    puede detectar sin juzgar sentido.
    """

    nombre = 'heuristico'
    coste_llamadas = 0
    coste_tokens = 0

    def fidelidad(self, texto, fuentes):
        frases = oraciones(texto)
        if not frases:
            return None, []
        base = plano(' '.join(fuentes))
        no_respaldadas = []
        for f in frases:
            cifras_malas = [c for c in _cifras(f)
                            if plano(c.replace(' ', '')) not in base.replace(' ', '')]
            palabras = _contenido(f)
            apoyo = (sum(1 for p in palabras if p in base) / len(palabras)
                     if palabras else 1.0)
            if cifras_malas or apoyo < APOYO_MINIMO:
                no_respaldadas.append({
                    'oracion': f,
                    'motivo': ('cifra ausente en las fuentes: %s' % ', '.join(cifras_malas))
                              if cifras_malas else 'apoyo lexico %.2f' % apoyo,
                })
        return (len(frases) - len(no_respaldadas)) / len(frases), no_respaldadas


class JuezModelo:
    """El mismo modelo local, preguntado oracion a oracion.

    Cuesta una llamada por oracion y se contabiliza: una evaluacion que no
    declara su coste no permite decidir si se corre en cada despliegue o solo
    cuando se toca el prompt.
    """

    nombre = 'modelo'

    PROMPT = (
        'Eres un verificador. Te doy FRAGMENTOS y una AFIRMACION. '
        'Responde si la afirmacion esta respaldada por los fragmentos. '
        'Respaldada significa que se deduce de lo que dicen, sin anadir nada. '
        'Si trae una cifra, un nombre o una condicion que no aparece en los '
        'fragmentos, NO esta respaldada. No uses conocimiento propio.'
    )
    SCHEMA = {
        'type': 'json_schema',
        'json_schema': {
            'name': 'veredicto', 'strict': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'respaldada': {'type': 'boolean'},
                    'motivo': {'type': 'string'},
                },
                'required': ['respaldada', 'motivo'],
                'additionalProperties': False,
            },
        },
    }

    def __init__(self):
        self.coste_llamadas = 0
        self.coste_tokens = 0

    def fidelidad(self, texto, fuentes):
        from django.conf import settings
        from openai import OpenAI

        frases = oraciones(texto)
        if not frases:
            return None, []
        cliente = OpenAI(
            base_url=getattr(settings, 'CLINIC_LLM_URL', 'http://localhost:11434/v1'),
            api_key='ollama',
            timeout=float(getattr(settings, 'CLINIC_LLM_TIMEOUT', 240.0)))
        contexto = '\n\n'.join(fuentes)[:4000]
        no_respaldadas = []
        for f in frases:
            try:
                r = cliente.chat.completions.create(
                    model=getattr(settings, 'CLINIC_LLM_MODEL', 'llama3.2:3b'),
                    messages=[
                        {'role': 'system', 'content': self.PROMPT},
                        {'role': 'user', 'content':
                            'FRAGMENTOS:\n%s\n\nAFIRMACION: %s' % (contexto, f)},
                    ],
                    response_format=self.SCHEMA, temperature=0.0, max_tokens=200)
                self.coste_llamadas += 1
                uso = getattr(r, 'usage', None)
                self.coste_tokens += ((getattr(uso, 'prompt_tokens', 0) or 0) +
                                      (getattr(uso, 'completion_tokens', 0) or 0))
                d = json.loads(r.choices[0].message.content or '{}')
            except Exception as exc:                      # noqa: BLE001
                # Un juez caido no puede aprobar por defecto: se cuenta como
                # no respaldada y se dice por que.
                no_respaldadas.append({'oracion': f,
                                       'motivo': 'juez no disponible: %s' % exc})
                continue
            if not d.get('respaldada'):
                no_respaldadas.append({'oracion': f,
                                       'motivo': d.get('motivo', '')[:120]})
        return (len(frases) - len(no_respaldadas)) / len(frases), no_respaldadas


def juez_de(nombre):
    return JuezModelo() if nombre == 'modelo' else JuezHeuristico()


# --------------------------------------------------------------------------
# generar: hablar con el sistema real
# --------------------------------------------------------------------------
def django_listo():
    sys.path.insert(0, str(RAIZ / 'backend-clinic'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_backend.settings')
    import django
    django.setup()


def generar(version):
    django_listo()
    from django.conf import settings
    from apps.samples.rag_qa import responder_documental

    if not getattr(settings, 'CLINIC_LLM_ENABLED', False):
        raise SystemExit('CLINIC_LLM_ENABLED esta desactivado: no habria juez '
                         'y todas las respuestas saldrian vacias')

    instruccion = prompt_de(version)
    salida, t0 = [], time.time()
    for n, c in enumerate(casos(), 1):
        ini = time.time()
        r = responder_documental(c['pregunta'], system_prompt=instruccion)
        salida.append({
            'id': c['id'],
            'pregunta': c['pregunta'],
            'responde': r.responde,
            'texto': r.texto,
            'motivo': r.motivo,
            # Los fragmentos que el modelo VIO. La fidelidad se juzga contra
            # esto y no contra el corpus entero: preguntar si algo esta «en
            # alguna parte del corpus» no mide si la respuesta se fundo en lo
            # que se le dio.
            'fuentes': [{'fuente': x.fragmento.fuente,
                         'seccion': x.fragmento.seccion,
                         'similitud': x.porcentaje,
                         'texto': x.fragmento.texto[:900]} for x in r.candidatos],
            'citas': [x.fragmento.fuente for x in r.citas],
            'tokens_entrada': r.tokens_entrada,
            'tokens_salida': r.tokens_salida,
            'latency_ms': r.latency_ms,
        })
        print('  [%2d/%2d] %s  %-9s %4.0fs  %s'
              % (n, len(casos()), c['id'],
                 'responde' if r.responde else 'ABSTIENE',
                 time.time() - ini, (r.texto or r.motivo)[:52]))
        sys.stdout.flush()

    ruta = ruta_respuestas(version)
    with io.open(ruta, 'w', encoding='utf-8', newline='\n') as f:
        for r in salida:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    tok = sum(r['tokens_entrada'] + r['tokens_salida'] for r in salida)
    print('\nescrito %s' % ruta.relative_to(RAIZ))
    print('corrida completa: %d preguntas, %.1f min, %d tokens del juez'
          % (len(salida), (time.time() - t0) / 60, tok))
    return 0


# --------------------------------------------------------------------------
# correr: puntuar
# --------------------------------------------------------------------------
def puntuar(version, nombre_juez='heuristico'):
    juez = juez_de(nombre_juez)
    datos = respuestas(version)
    filas = []
    for c in casos():
        r = datos.get(c['id'])
        if r is None:
            raise SystemExit('falta %s en respuestas/%s.jsonl' % (c['id'], version))
        texto = r.get('texto') or ''
        fila = {'id': c['id'], 'categoria': c['categoria'],
                'critico': c['critico'], 'responde': r.get('responde', False),
                'texto': texto, 'motivo': r.get('motivo', ''),
                'latency_ms': r.get('latency_ms', 0),
                'tokens': r.get('tokens_entrada', 0) + r.get('tokens_salida', 0)}

        if c.get('debe_abstenerse'):
            # No se puntua completitud ni fidelidad de un texto que no deberia
            # existir: el acierto es no haberlo escrito.
            fila['abstuvo'] = not r.get('responde', False)
            fila['completitud'] = None
            fila['fidelidad'] = None
            fila['sin_prohibidos'], fila['prohibidos'] = sin_prohibidos(c, texto)
            fila['ok'] = bool(fila['abstuvo']) and fila['sin_prohibidos'] == 1.0
        else:
            comp, faltan = completitud(c, texto)
            sp, hallados = sin_prohibidos(c, texto)
            fuentes = [f['texto'] for f in r.get('fuentes', [])]
            fid, no_resp = juez.fidelidad(texto, fuentes)
            fila.update({'completitud': comp, 'faltan': faltan,
                         'sin_prohibidos': sp, 'prohibidos': hallados,
                         'fidelidad': fid, 'no_respaldadas': no_resp,
                         'abstuvo': not r.get('responde', False)})
            # Un caso solo esta bien si dice todo lo que debe, nada de lo que
            # no debe, y cada oracion se sostiene en las fuentes.
            fila['ok'] = (comp == 1.0 and sp == 1.0 and (fid or 0) >= 1.0)
        filas.append(fila)
    return filas, juez


def promedio(valores):
    v = [x for x in valores if x is not None]
    return sum(v) / len(v) if v else None


def compuerta(filas, u):
    comp = promedio([f['completitud'] for f in filas])
    fid = promedio([f['fidelidad'] for f in filas])
    sp = promedio([f['sin_prohibidos'] for f in filas])
    criticos = [f for f in filas if f['critico']]
    criticos_ok = sum(1 for f in criticos if f['ok'])
    razones = []
    # «Sin medir» NO es cero. Un cero dice que el sistema fallo; un «sin medir»
    # dice que el instrumento no llego a mirar, y confundirlos es exactamente
    # como se fabrica una cifra falsa. La compuerta bloquea en los dos casos
    # —no se despliega lo que no se ha podido medir— pero escribe razones
    # distintas, porque lo que hay que arreglar despues no es lo mismo.
    def revisar(clave, valor, minimo):
        if valor is None:
            razones.append('%s SIN MEDIR (ningun caso aporto dato)' % clave)
        elif valor < minimo:
            razones.append('%s %.2f < %.2f' % (clave, valor, minimo))

    revisar('completitud', comp, u['completitud_minima'])
    revisar('fidelidad', fid, u['fidelidad_minima'])
    revisar('sin_prohibidos', sp, u['sin_prohibidos_minimo'])
    if criticos_ok < len(criticos):
        razones.append('criticos %d/%d (se exigen todos)' % (criticos_ok, len(criticos)))
    return {'completitud': comp, 'fidelidad': fid, 'sin_prohibidos': sp,
            'criticos_ok': criticos_ok, 'criticos': len(criticos),
            'pasa': not razones, 'razones': razones}


def informe(version, filas, res, juez, nombre_juez):
    lineas = ['# Corrida de evaluacion — %s' % version, '',
              '| | |', '|---|---|',
              '| Prompt | `prompts/%s.txt` |' % version,
              '| Juez de fidelidad | %s |' % nombre_juez,
              '| Casos | %d (%d criticos) |'
              % (len(filas), sum(1 for f in filas if f['critico'])),
              '| Fecha | %s |' % time.strftime('%Y-%m-%d %H:%M'), '', '## Compuerta', '',
              '| Metrica | Valor | Umbral | |', '|---|---|---|---|']
    u = umbrales()
    for clave, umbral in (('completitud', u['completitud_minima']),
                          ('fidelidad', u['fidelidad_minima']),
                          ('sin_prohibidos', u['sin_prohibidos_minimo'])):
        v = res[clave]
        marca = 'OK' if v is not None and v >= umbral else 'BLOQUEA'
        lineas.append('| %s | %s | %.2f | %s |'
                      % (clave, '%.3f' % v if v is not None else 'sin medir',
                         umbral, marca))
    lineas.append('| criticos perfectos | %d/%d | todos | %s |'
                  % (res['criticos_ok'], res['criticos'],
                     'OK' if res['criticos_ok'] == res['criticos'] else 'BLOQUEA'))
    lineas += ['', '**La compuerta devuelve %d** (%s).'
               % (0 if res['pasa'] else 1, 'PASA' if res['pasa'] else 'BLOQUEA'), '']
    if res['razones']:
        lineas += ['Por que bloquea:', '']
        lineas += ['- %s' % r for r in res['razones']]
        lineas.append('')

    lineas += ['## Caso por caso', '',
               '| Caso | Categoria | Crit | Resp | Compl | Fidel | Proh | OK |',
               '|---|---|---|---|---|---|---|---|']
    for f in filas:
        num = lambda v: '%.2f' % v if v is not None else '-'          # noqa: E731
        lineas.append('| %s | %s | %s | %s | %s | %s | %s | %s |' % (
            f['id'], f['categoria'], 'si' if f['critico'] else '',
            'abst' if f['abstuvo'] else 'si',
            num(f['completitud']), num(f['fidelidad']),
            'si' if f['sin_prohibidos'] == 1.0 else 'NO',
            'OK' if f['ok'] else 'fallo'))

    abstencion = {c['id'] for c in casos() if c.get('debe_abstenerse')}
    fallos = [f for f in filas if not f['ok']]
    if fallos:
        lineas += ['', '## Que fallo, en concreto', '']
        for f in fallos:
            lineas.append('### %s (%s%s)' % (f['id'], f['categoria'],
                                             ', CRITICO' if f['critico'] else ''))
            # El fallo de un caso de abstencion no se explica con lo que «no
            # dijo»: se explica con que hablo. Sin esta linea el informe deja
            # en blanco justo el fallo mas grave que mide el dataset.
            if not f.get('abstuvo') and f['id'] in abstencion:
                lineas.append('- **Respondio cuando debia abstenerse.** Contesto: '
                              '«%s»' % (f['texto'][:160] or '(vacio)'))
            if f.get('faltan'):
                lineas.append('- No dijo: %s' % '; '.join('`%s`' % x for x in f['faltan']))
            if f.get('prohibidos'):
                lineas.append('- Dijo lo prohibido: %s'
                              % '; '.join('`%s`' % x for x in f['prohibidos']))
            if f.get('abstuvo') and not f['critico'] and f.get('completitud') == 0:
                lineas.append('- Se abstuvo en una pregunta que el corpus SI cubre (motivo: %s)'
                              % (f['motivo'] or 'sin motivo'))
            for nr in (f.get('no_respaldadas') or [])[:3]:
                lineas.append('- Sin respaldo: «%s» — %s'
                              % (nr['oracion'][:110], nr['motivo']))
            lineas.append('')

    tok_gen = sum(f['tokens'] for f in filas)
    lineas += ['', '## Coste de una corrida completa', '',
               '| | |', '|---|---|',
               '| Llamadas al modelo (generacion) | %d |' % len(filas),
               '| Tokens de generacion | %d |' % tok_gen,
               '| Tiempo de generacion | %.1f min |'
               % (sum(f['latency_ms'] for f in filas) / 60000.0),
               '| Llamadas al juez | %d |' % juez.coste_llamadas,
               '| Tokens del juez | %d |' % juez.coste_tokens,
               '| Coste en dinero | 0 — `llama3.2:3b` local (ADR-0024) |', '',
               'El coste real de esta evaluacion es **tiempo de CPU**, no dinero. '
               'Por eso `generar` y `correr` estan separados: se paga una vez y '
               'se puntua tantas veces como haga falta.', '']
    return '\n'.join(lineas)


def correr(version, nombre_juez):
    filas, juez = puntuar(version, nombre_juez)
    res = compuerta(filas, umbrales())
    ruta = BASE / 'resultados' / ('%s_%s.md' % (version, nombre_juez))
    io.open(ruta, 'w', encoding='utf-8', newline='\n').write(
        informe(version, filas, res, juez, nombre_juez))

    print('%s  juez=%s' % (version, nombre_juez))
    for clave in ('completitud', 'fidelidad', 'sin_prohibidos'):
        v = res[clave]
        print('  %-16s %s' % (clave, '%.3f' % v if v is not None else 'sin medir'))
    print('  %-16s %d/%d' % ('criticos ok', res['criticos_ok'], res['criticos']))
    print('  compuerta        %s' % ('PASA' if res['pasa'] else 'BLOQUEA'))
    for r in res['razones']:
        print('    - %s' % r)
    print('\ninforme en %s' % ruta.relative_to(RAIZ))
    return 0 if res['pasa'] else 1


def comparar(a, b, nombre_juez):
    salida = {}
    for v in (a, b):
        filas, juez = puntuar(v, nombre_juez)
        salida[v] = (filas, compuerta(filas, umbrales()))
    print('%-18s %10s %10s' % ('', a, b))
    for clave in ('completitud', 'fidelidad', 'sin_prohibidos'):
        f = lambda v: ('%.3f' % v) if v is not None else '-'          # noqa: E731
        print('%-18s %10s %10s' % (clave, f(salida[a][1][clave]), f(salida[b][1][clave])))
    for v in (a, b):
        r = salida[v][1]
        print('%-18s %10s' % ('criticos (%s)' % v, '%d/%d' % (r['criticos_ok'], r['criticos'])))
    print()
    for v in (a, b):
        print('compuerta %-8s %s' % (v, 'PASA' if salida[v][1]['pasa'] else 'BLOQUEA'))

    # Lo que un promedio esconde: quien cambio de lado.
    fa = {f['id']: f['ok'] for f in salida[a][0]}
    fb = {f['id']: f['ok'] for f in salida[b][0]}
    mejoran = [i for i in fa if not fa[i] and fb[i]]
    empeoran = [i for i in fa if fa[i] and not fb[i]]
    print('\nmejoran de %s a %s : %s' % (a, b, ', '.join(mejoran) or 'ninguno'))
    print('empeoran de %s a %s: %s' % (a, b, ', '.join(empeoran) or 'ninguno'))
    return 0


# --------------------------------------------------------------------------
# calibracion del juez contra etiquetas humanas
# --------------------------------------------------------------------------
CAMPOS_ETIQUETA = ['version', 'caso', 'n', 'oracion', 'fuentes', 'fiel',
                   'anotador', 'nota']


def plantilla(versiones):
    """CSV con una fila por oracion, para que una persona la etiquete.

    Deliberadamente NO se rellena sola: la calibracion compara al juez con un
    HUMANO. Rellenarla con otro modelo mediria el acuerdo entre dos maquinas y
    no diria nada de si el juez sirve.

    Acepta varias versiones porque con una sola no salian las 15 filas: este
    asistente se abstiene tanto que apenas produce texto que juzgar. Que hagan
    falta dos o tres corridas para reunir 15 oraciones no es un apaño del
    formato — es el mismo hallazgo que mide la completitud, visto desde otro
    lado, y conviene decirlo en el informe en vez de disimularlo.
    """
    filas = []
    for version in versiones:
        datos = respuestas(version)
        for c in casos():
            r = datos[c['id']]
            fuentes = ' | '.join(sorted({f['fuente'] for f in r.get('fuentes', [])}))
            for n, frase in enumerate(oraciones(r.get('texto') or ''), 1):
                filas.append({'version': version, 'caso': c['id'], 'n': n,
                              'oracion': frase, 'fuentes': fuentes,
                              'fiel': '', 'anotador': '', 'nota': ''})
    with io.open(ETIQUETAS, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_ETIQUETA)
        w.writeheader()
        w.writerows(filas)
    print('escrito %s con %d oraciones de %s'
          % (ETIQUETAS.relative_to(RAIZ), len(filas), ', '.join(versiones)))
    if len(filas) < 15:
        print('AVISO: son menos de 15. Anade otra version a la plantilla.')
    print('rellena la columna «fiel» con 1 (respaldada) o 0 (no respaldada) y')
    print('pon tu nombre en «anotador».')
    return 0


def kappa_cohen(a, b):
    """Acuerdo corregido por azar. Sin esto, dos jueces que dicen «fiel» a todo
    parecerian coincidir al 100 % sin haber juzgado nada."""
    n = len(a)
    if not n:
        return None
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = 0.0
    for v in (0, 1):
        pe += (a.count(v) / n) * (b.count(v) / n)
    if pe == 1.0:
        return None
    return (po - pe) / (1 - pe)


def calibrar(version, nombre_juez):
    if not ETIQUETAS.exists():
        raise SystemExit('no hay etiquetas: corre «plantilla %s» y rellenala' % version)
    with io.open(ETIQUETAS, encoding='utf-8') as f:
        etiquetas = [r for r in csv.DictReader(f) if (r.get('fiel') or '').strip() in ('0', '1')]
    if len(etiquetas) < 15:
        raise SystemExit('solo hay %d etiquetas rellenadas; la consigna pide 15'
                         % len(etiquetas))

    juez = juez_de(nombre_juez)
    # El veredicto se calcula para cada version que aparezca en las etiquetas,
    # no solo para la pedida: una etiqueta sin su veredicto correspondiente se
    # caeria en silencio y el acuerdo saldria calculado sobre menos filas de
    # las que la persona etiqueto.
    veredictos = {}
    for v in sorted({(e.get('version') or version) for e in etiquetas}):
        datos = respuestas(v)
        for c in casos():
            r = datos[c['id']]
            texto = r.get('texto') or ''
            fuentes = [f['texto'] for f in r.get('fuentes', [])]
            _, no_resp = juez.fidelidad(texto, fuentes)
            malas = {nr['oracion'] for nr in no_resp}
            for n, frase in enumerate(oraciones(texto), 1):
                veredictos[(v, c['id'], str(n))] = 0 if frase in malas else 1

    humano, maquina, desacuerdos = [], [], []
    olvidadas = []
    for e in etiquetas:
        clave = (e.get('version') or version, e['caso'], e['n'])
        if clave not in veredictos:
            # No se descarta en silencio: una etiqueta que el juez no puede
            # emparejar suele significar que las respuestas se regeneraron
            # despues de etiquetar, y entonces la calibracion entera esta
            # midiendo dos corridas distintas.
            olvidadas.append('%s/%s.%s' % clave)
            continue
        h, m = int(e['fiel']), veredictos[clave]
        humano.append(h)
        maquina.append(m)
        if h != m:
            desacuerdos.append({'caso': '%s %s' % (clave[0], e['caso']),
                                'n': e['n'],
                                'oracion': e['oracion'], 'humano': h,
                                'juez': m, 'nota': e.get('nota', '')})
    if olvidadas:
        print('AVISO: %d etiqueta(s) sin veredicto -> %s'
              % (len(olvidadas), ', '.join(olvidadas[:6])))

    n = len(humano)
    acuerdo = sum(1 for x, y in zip(humano, maquina) if x == y) / n if n else 0
    k = kappa_cohen(humano, maquina)
    anotadores = sorted({e.get('anotador', '').strip() for e in etiquetas
                         if e.get('anotador', '').strip()})

    lineas = ['# Calibracion del juez — %s, juez %s' % (version, nombre_juez), '',
              '| | |', '|---|---|',
              '| Oraciones etiquetadas | %d |' % n,
              '| Anotador(es) | %s |' % (', '.join(anotadores) or 'sin declarar'),
              '| Acuerdo | %.1f %% |' % (acuerdo * 100),
              '| Kappa de Cohen | %s |' % ('%.3f' % k if k is not None else 'indefinida'),
              '| Coste del juez | %d llamadas, %d tokens |'
              % (juez.coste_llamadas, juez.coste_tokens), '']
    if k is not None:
        lectura = ('pobre' if k < 0.2 else 'aceptable' if k < 0.4 else
                   'moderada' if k < 0.6 else 'sustancial' if k < 0.8 else 'casi total')
        lineas += ['Concordancia **%s** segun la escala de Landis y Koch. El '
                   'acuerdo bruto por si solo enganaria: si casi todo es fiel, '
                   'decir «fiel» a todo ya acierta mucho sin juzgar nada; la '
                   'kappa descuenta ese azar.' % lectura, '']
    lineas += ['## Desacuerdos (%d)' % len(desacuerdos), '']
    if desacuerdos:
        lineas += ['| Caso | Humano | Juez | Oracion | Nota del anotador |',
                   '|---|---|---|---|---|']
        for d in desacuerdos:
            lineas.append('| %s.%s | %s | %s | %s | %s |' % (
                d['caso'], d['n'],
                'fiel' if d['humano'] else 'no fiel',
                'fiel' if d['juez'] else 'no fiel',
                d['oracion'][:90].replace('|', '/'), d['nota'][:60]))
    else:
        lineas.append('Ninguno.')
    lineas.append('')

    ruta = BASE / 'resultados' / ('calibracion_%s_%s.md' % (version, nombre_juez))
    io.open(ruta, 'w', encoding='utf-8', newline='\n').write('\n'.join(lineas))
    print('oraciones comparadas: %d' % n)
    print('acuerdo            : %.1f %%' % (acuerdo * 100))
    print('kappa de Cohen     : %s' % ('%.3f' % k if k is not None else 'indefinida'))
    print('desacuerdos        : %d' % len(desacuerdos))
    print('\ninforme en %s' % ruta.relative_to(RAIZ))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('accion', choices=['generar', 'correr', 'comparar',
                                       'plantilla', 'calibrar'])
    ap.add_argument('version')
    ap.add_argument('version_b', nargs='*')
    ap.add_argument('--juez', default='heuristico', choices=['heuristico', 'modelo'])
    o = ap.parse_args()

    if o.accion == 'generar':
        return generar(o.version)
    if o.accion == 'correr':
        return correr(o.version, o.juez)
    if o.accion == 'comparar':
        if len(o.version_b) != 1:
            raise SystemExit('comparar necesita exactamente dos versiones')
        return comparar(o.version, o.version_b[0], o.juez)
    if o.accion == 'plantilla':
        return plantilla([o.version] + list(o.version_b))
    if o.accion == 'calibrar':
        if o.juez == 'modelo':
            django_listo()
        return calibrar(o.version, o.juez)
    return 1


if __name__ == '__main__':
    sys.exit(main())
