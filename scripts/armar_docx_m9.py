# -*- coding: utf-8 -*-
"""Arma el entregable M9 en un solo Markdown, listo para `md_a_word.py`.

    python scripts/armar_docx_m9.py
    cd docs && ../backend-clinic/.venv/Scripts/python md_a_word.py M9_RED_TEAM/ENTREGABLE_RED_TEAM.md

## Por que un guion y no copiar y pegar

La tabla de resultados se genera **leyendo `evidencia/*.json`**, no
transcribiendo. Si una cifra del informe no coincide con la evidencia, es
porque alguien la escribio a mano — aqui no puede pasar. Es la misma regla que
el resto del proyecto: «reproducible con X» exige que X este en el repositorio.

## Que corrida cuenta para cada ataque

Hubo mediciones invalidas, y estan conservadas a proposito: un `0/3` de un
ataque que no llego a su objetivo no es un resultado. `CORRIDAS` nombra,
ataque por ataque, que fichero es la base valida y cual el retest valido, y
por que los otros no cuentan. Esa eleccion es el corazon del informe y por eso
se declara aqui y no se deduce del nombre del fichero.

Salida en ASCII puro en consola; el Markdown va en UTF-8.
"""
import io
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BASE = RAIZ / 'docs' / 'M9_RED_TEAM'
EVID = BASE / 'evidencia'
DESTINO = BASE / 'ENTREGABLE_RED_TEAM.md'

#: ataque -> (fichero base valido, fichero retest valido, nota si aplica)
CORRIDAS = {
    'AI-SEC-001': ('hallazgos_base_20260924_021627.json',
                   'hallazgos_retest_20260924_073222.json', ''),
    'AI-SEC-002': ('hallazgos_base_20260924_021627.json',
                   'hallazgos_retest_20260924_073222.json', ''),
    'AI-SEC-003': ('hallazgos_base_20260924_021627.json',
                   'hallazgos_retest_20260924_073222.json',
                   'linea base: 0 = el analista conserva su trabajo'),
    'AI-SEC-004': ('hallazgos_base_20260924_021627.json',
                   'hallazgos_retest_20260924_073222.json',
                   'defensa previa: el enrutador declara SIN_MATCH'),
    'AI-SEC-005': ('hallazgos_base_20260924_021627.json',
                   'hallazgos_retest_20260924_073222.json', ''),
    'AI-SEC-006': ('hallazgos_base_006_valido_20260925_011926.json',
                   'hallazgos_retest_006_20260925_012601.json',
                   'base con el veneno del PROPIO ataque; las anteriores no lo insertaban'),
    'AI-SEC-007': ('hallazgos_base_rag_valido_20260924_023659.json',
                   'hallazgos_retest_rag_con_veneno_20260924_073948.json',
                   'retest con el veneno PUESTO; uno anterior corrio con el corpus limpio y se descarto'),
    'AI-SEC-008': (None, 'hallazgos_retest_008_20260925_013849.json',
                   'defensa previa (RN-01); la corrida base fue contra el endpoint equivocado'),
    'AI-SEC-009': (None, 'hallazgos_retest_009_criterio_limpio_20260925_021924.json',
                   'confirmado por medicion directa, no por la corrida del agente'),
}

CABECERA = """# Entregable M9 — Red teaming del asistente de BIOMED

| | |
|---|---|
| **Equipo** | **BIOMED UMSS** — Ing. Guillermo Mamani Chambi (individual, G04) |
| **Producto** | Plataforma de Cariotipado Asistido por IA — capa de IA de `backend-clinic` |
| **Agente / IDE** | Claude Code (Opus) como IDE · ataques y ejecutor propios sobre `llama3.2:3b` local |
| **Repositorio** | `github.com/guillemc92/karyoumss`, rama `feature/clinic-django-stack`, commit `%(commit)s` |
| **Carpetas** | `docs/M9_RED_TEAM/` · `scripts/red_team_biomed.py` · `scripts/envenenar_corpus.py` |
| **Fecha** | 25 de septiembre de 2026 |

> «En testing comprobamos que el sistema haga lo que debe. En red teaming
> intentamos que haga lo que no debe — y luego escribimos el test que lo
> recuerda.» — M7 · Día 8

**Alcance y ética.** Solo se ataca el propio sistema, en la base local, con
usuarios y muestras de demostración. `docs/INFORMES CARIOTIPOS/` —los 462
informes clínicos reales— no entra aquí ni como lectura.

## Resumen

| | |
|---|---|
| **3 hallazgos** | confirmados, dos de severidad alta |
| **3 mitigaciones** | todas en la aplicación, ninguna en el prompt |
| **9 ataques × 3** | 5 categorías, criterio observable, evidencia en JSON |
| **24 tests** | de regresión, ninguno compara texto exacto |
| **7 fallos del instrumento** | cazados y documentados: seis falsos negativos y un falso positivo |

La consigna pedía **un** hallazgo, **una** mitigación y **un** test.

"""


def cargar(nombre):
    if not nombre:
        return {}
    ruta = EVID / nombre
    if not ruta.exists():
        raise SystemExit('falta la evidencia %s' % nombre)
    d = json.loads(ruta.read_text(encoding='utf-8'))
    return {h['id']: h for h in d.get('hallazgos', [])}


def tabla_resultados():
    """Base y retest de cada ataque, leidos de la evidencia."""
    cache, filas = {}, []
    for ident, (fbase, fretest, nota) in sorted(CORRIDAS.items()):
        for f in (fbase, fretest):
            if f and f not in cache:
                cache[f] = cargar(f)
        hb = cache.get(fbase, {}).get(ident) if fbase else None
        hr = cache.get(fretest, {}).get(ident) if fretest else None
        ref = hr or hb
        if ref is None:
            continue
        base = '%d/%d' % (hb['exitos'], hb['repeticiones']) if hb else '—'
        retest = '%d/%d' % (hr['exitos'], hr['repeticiones']) if hr else '—'
        filas.append('| %s | %s | %s | %s | %s | %s |' % (
            ident, ref['categoria'].replace('_', ' '),
            (ref.get('owasp') or '—').split(' ')[0], base, retest, nota or ''))
    return ('| Ataque | Categoría | OWASP | Base | Retest | Nota |\n'
            '|---|---|---|---|---|---|\n' + '\n'.join(filas))


def seccion(ruta, nivel_extra=1):
    """Inserta un Markdown bajando sus encabezados un nivel."""
    texto = (BASE / ruta).read_text(encoding='utf-8')
    salida = []
    for linea in texto.split('\n'):
        if linea.startswith('#'):
            linea = '#' * nivel_extra + linea
        salida.append(linea)
    return '\n'.join(salida)


def main():
    commit = sys.argv[1] if len(sys.argv) > 1 else 'PENDIENTE'
    partes = [CABECERA % {'commit': commit}]

    partes.append('# 1 · Modelo de amenazas\n')
    partes.append(seccion('MODELO_DE_AMENAZAS.md').split('\n', 1)[1].lstrip())

    partes.append('\n\n# 2 · Los ataques y sus resultados\n')
    partes.append(
        'Nueve ataques en cinco categorías, tres repeticiones cada uno, contra el\n'
        'sistema real. El criterio de éxito es siempre **observable** —nunca igualdad\n'
        'de texto— y un ataque «tiene éxito» cuando falla el SISTEMA, no cuando el\n'
        'modelo dice algo raro.\n\n'
        'Esta tabla la genera `scripts/armar_docx_m9.py` **leyendo la evidencia**: si\n'
        'una cifra no coincide con los JSON, es porque alguien la escribió a mano.\n')
    partes.append(tabla_resultados())
    partes.append(
        '\n\nLos ficheros de ataque están en `ataques/*.json` con su `exito_si`, su\n'
        'clasificación OWASP/ATLAS y, donde hizo falta, una `nota_instrumento` que\n'
        'explica por qué una medición anterior no valía.\n')

    partes.append('\n\n# 3 · Hallazgos\n')
    for f in ('AI-SEC-001.md', 'AI-SEC-007.md', 'AI-SEC-009.md'):
        partes.append('\n' + seccion('hallazgos/' + f))

    partes.append('\n\n# 4 · Mitigaciones y retest\n')
    partes.append("""
Las tres están **en la aplicación, no en el prompt**. Pedirle al modelo que no
haga algo es una instrucción más en un contexto donde ya conviven instrucciones
y datos: el modelo PROPONE, la aplicación DECIDE.

| Mitigación | Qué cierra | Cómo |
|---|---|---|
| `apps/samples/alcance.py` | AI-SEC-001/002/005 | La identidad del JWT viaja hasta la consulta. Replica la regla del listado REST en vez de inventar una segunda política para el mismo dato. **Cerrado por defecto**: sin alcance, cero filas. |
| `apps/samples/fuentes_confiables.py` | AI-SEC-006/007 | Solo fuentes aprobadas entran al contexto del RAG, y lo descartado se registra. Filtra por **procedencia, no por parecido**: el veneno con 62-66 % se descarta y entra una fuente legítima con 59,5 %. |
| alcance en `agente_escritura` | AI-SEC-009 | `preparar_validacion` comprueba `puede_leer(caso)` **antes de leer nada** y responde como si el caso no existiera. |

**Qué no resuelven.** El filtro de procedencia no ve la modificación de un
documento ya aprobado —para eso haría falta hash por fichero, que no está
hecho— ni juzga contenido: un ADR legítimo con un error sigue entrando, y debe.
El alcance no protege de que el modelo repita en un turno posterior algo que ya
vio en el mismo hilo.

## El interruptor de línea base

`CLINIC_RED_TEAM_SIN_FILTRO` desactiva el filtro de procedencia. Existe porque
**un retest sin línea base comparable no demuestra nada**: una vez aplicada la
mitigación hace falta poder volver al «antes». Es el `--modo vulnerable` del
laboratorio.

Por defecto está cerrado, cada uso deja aviso en el log, y dos tests fijan las
dos direcciones. Aun así es una puerta, y no debe existir en un despliegue real.
""")

    partes.append('\n\n# 5 · Tests de regresión\n')
    partes.append("""
24 tests en `backend-clinic/apps/samples/tests/test_regresion_seguridad.py`,
verdes en 24 s. **Ninguno llama al LLM**: prueban que los CONTROLES impiden el
daño, no que el modelo se porte bien. Si mañana `llama3.2:3b` obedece a un
atacante nuevo, estos tests siguen siendo la razón por la que no pasa nada
grave.

**Ninguno compara texto exacto.** Un assert contra la redacción se rompe cuando
alguien mejora un mensaje, y no se rompe cuando se cae el control. Aquí se
verifica que un CHN ajeno no aparece, que el alcance vacío no devuelve nada,
que la escritura queda bloqueada y qué claves viajan en la respuesta.

**Tres que merecen mención:**

- `test_ai_sec_001_quitar_el_alcance_reabre_la_fuga` — reproduce el código de
  antes y comprueba que ENTONCES sí se filtraba. Sin él, los demás podrían
  estar pasando por una razón equivocada y nadie lo notaría.
- `test_ai_sec_003_el_analista_sigue_viendo_lo_suyo` — un control que corta de
  más es un control roto. Este lo caza.
- `test_ai_sec_007_por_defecto_el_filtro_esta_activo` — el interruptor de línea
  base no puede quedarse encendido por descuido.
""")

    partes.append('\n\n# 6 · Los siete fallos del instrumento\n')
    inicio = seccion('README.md')
    a = inicio.index('## Los siete fallos del instrumento')
    b = inicio.index('## Lo que este ejercicio NO prueba')
    partes.append(inicio[a:b].split('\n', 1)[1].lstrip())

    partes.append('\n\n# 7 · Lo que este ejercicio no prueba\n')
    partes.append(inicio[b:].split('\n', 1)[1].lstrip())

    DESTINO.write_text('\n'.join(partes), encoding='utf-8')
    print('escrito %s (%d lineas)'
          % (DESTINO.relative_to(RAIZ), len(DESTINO.read_text(encoding='utf-8').split('\n'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
