"""El despachador del agente: que sabe hacer y que devuelve cuando lo hace.

`agente_acciones` es la pieza que traduce entre el modelo y el dominio. Tiene
dos responsabilidades y ninguna de las dos necesita un LLM para probarse:

    schemas()   publicar el catalogo en el formato de tool calling
    ejecutar()  resolver el nombre que el modelo eligio y devolver la observacion

Ambas son **deterministas**: mismo nombre, misma salida. Lo probabilistico —si
el modelo elige bien la herramienta— se mide aparte, con el banco de
`eval_enrutado`; aqui no se afirma nada sobre esa eleccion.

## Lo que estas pruebas protegen

1. Que los schemas se **derivan** del catalogo, no se copian. La copia es la
   forma habitual de que el agente y el servidor MCP se desincronicen.
2. Que la procedencia (`Fuente: tabla X`) viaja en la descripcion. Sin ella el
   modelo no puede citar de donde salio el dato, y citar es obligatorio.
3. Que un nombre inventado por el modelo produce una observacion util —«no
   existe, tienes estas»— y no un fallo. Es la diferencia entre que el agente
   rectifique en el siguiente paso o que la conversacion se caiga.
4. Que las sugerencias del RAG viajan **tambien en el fallo**: un «no lo sé»
   sin salida es un callejon.

Nada se dobla salvo el propio RAG (que es red + disco) y la accion de
escritura (que tiene su propio fichero de pruebas).
"""
import pytest

from apps.samples import agente_acciones as acciones
from apps.samples.agente_acciones import NOMBRE_RAG, ejecutar, schemas
from apps.samples.agente_escritura import NOMBRE as NOMBRE_ESCRITURA
from apps.samples.rag_corpus import Fragmento
from apps.samples.rag_index import Resultado
from apps.samples.rag_qa import RespuestaRag
from apps.samples.tools import CATALOGO, ToolSpec


def resultado(fuente, seccion, similitud):
    return Resultado(Fragmento(texto='texto de ' + fuente, fuente=fuente,
                               seccion=seccion, orden=1), similitud)


def montar_rag(monkeypatch, respuesta):
    """Doble del RAG. `ejecutar` lo importa dentro de la funcion, asi que hay
    que sustituirlo en su modulo de origen, no en el de acciones."""
    from apps.samples import rag_qa
    recibido = {}

    def falso(pregunta):
        recibido['pregunta'] = pregunta
        return respuesta

    monkeypatch.setattr(rag_qa, 'responder_documental', falso)
    return recibido


# --- el catalogo publicado --------------------------------------------------

def test_los_schemas_se_derivan_del_catalogo():
    """Nada se reescribe: cada herramienta del catalogo sale publicada."""
    publicados = [s['function']['name'] for s in schemas()]
    assert publicados == [t.name for t in CATALOGO] + [NOMBRE_RAG, NOMBRE_ESCRITURA]


def test_una_herramienta_nueva_aparece_sin_tocar_este_modulo(monkeypatch):
    """La propiedad que hace que el agente y el MCP no se desincronicen.

    Si `schemas()` copiara los nombres a mano, esta prueba fallaria — y ese es
    exactamente el fallo que se quiere impedir.
    """
    nueva = ToolSpec(name='CASOS_RECHAZADOS', description='Los casos rechazados.',
                     source='clinic_samples', keywords=('rechazado',),
                     run=lambda: [])
    monkeypatch.setattr(acciones, 'CATALOGO', tuple(CATALOGO) + (nueva,))
    assert 'CASOS_RECHAZADOS' in [s['function']['name'] for s in schemas()]


def test_cada_consulta_declara_que_no_recibe_argumentos():
    """Declararlo explicitamente evita que el modelo se invente parametros."""
    for schema in schemas()[:len(CATALOGO)]:
        params = schema['function']['parameters']
        assert params == {'type': 'object', 'properties': {}, 'required': []}


def test_la_descripcion_lleva_la_tabla_de_origen():
    """La procedencia viaja al modelo: es lo que le permite citar la fuente."""
    for schema, tool in zip(schemas(), CATALOGO):
        assert schema['function']['description'].endswith(
            'Fuente: tabla %s.' % tool.source)


def test_el_rag_declara_su_unico_parametro():
    """A diferencia de las consultas, el RAG SI recibe algo: la pregunta."""
    rag = next(s for s in schemas() if s['function']['name'] == NOMBRE_RAG)
    assert rag['function']['parameters']['required'] == ['pregunta']


# --- ejecutar: las consultas de estado --------------------------------------

def test_una_consulta_devuelve_filas_con_su_procedencia(monkeypatch):
    tool = ToolSpec(name='CASOS_DEMO', description='Demo.', source='clinic_samples',
                    keywords=(), run=lambda: [{'chn': 'CHN-1'}, {'chn': 'CHN-2'}])
    monkeypatch.setattr(acciones, 'POR_NOMBRE', {'CASOS_DEMO': tool})

    obs = ejecutar('CASOS_DEMO', {})
    assert obs == {'herramienta': 'CASOS_DEMO', 'fuente': 'clinic_samples',
                   'n': 2, 'filas': [{'chn': 'CHN-1'}, {'chn': 'CHN-2'}]}


def test_se_mandan_veinte_filas_pero_se_declara_el_total(monkeypatch):
    """`n` es el total real; `filas` es lo que cabe en la ventana del modelo.

    Recortar sin decir cuantas habia haria que el agente respondiera «hay 20
    casos» cuando hay 40. El numero y la muestra son cosas distintas.
    """
    tool = ToolSpec(name='MUCHOS', description='.', source='clinic_samples',
                    keywords=(), run=lambda: [{'i': i} for i in range(40)])
    monkeypatch.setattr(acciones, 'POR_NOMBRE', {'MUCHOS': tool})

    obs = ejecutar('MUCHOS', {})
    assert obs['n'] == 40
    assert len(obs['filas']) == 20


def test_un_nombre_inventado_devuelve_lo_que_si_existe():
    """El modelo puede inventarse un nombre pese al schema. No es un fallo: es
    una observacion de la que puede rectificar en el paso siguiente."""
    obs = ejecutar('CASOS_INVENTADOS', {})
    assert 'no existe' in obs['error']
    assert obs['disponibles'] == [t.name for t in CATALOGO] + [NOMBRE_RAG,
                                                               NOMBRE_ESCRITURA]


def test_una_consulta_que_revienta_es_una_observacion_no_una_caida(monkeypatch):
    """Hallazgo de esta tanda: el contrato decia una cosa y el codigo otra.

    El docstring de `ejecutar` promete «devuelve siempre un dict — nunca lanza»,
    y `agente_grafo.actuar` llama sin envolver apoyandose en esa promesa. Pero
    `tool.run()` es una consulta al ORM: una caida de la base salia disparada
    hacia arriba y tumbaba el turno entero del agente.

    Ahora la caida llega al modelo como observacion, con el nombre de la
    herramienta y el motivo, y la conversacion sigue.
    """
    def revienta():
        raise RuntimeError('la base no responde')

    tool = ToolSpec(name='CASOS_ROTOS', description='.', source='clinic_samples',
                    keywords=(), run=revienta)
    monkeypatch.setattr(acciones, 'POR_NOMBRE', {'CASOS_ROTOS': tool})

    obs = ejecutar('CASOS_ROTOS', {})
    assert 'la base no responde' in obs['error']
    assert obs['herramienta'] == 'CASOS_ROTOS'
    assert 'filas' not in obs      # no se inventa una lista vacia de resultados


def test_un_fallo_de_escritura_si_sale_disparado(monkeypatch):
    """La asimetria es deliberada, no un olvido.

    Leer y fallar es recuperable. Escribir y fallar a mitad de una transaccion,
    no: tragarse esa excepcion dejaria al modelo diciendo «hecho» sobre algo que
    no se guardo. RN-05 no admite eso.
    """
    def revienta(argumentos):
        raise RuntimeError('integridad')

    monkeypatch.setattr(acciones, 'ejecutar_escritura', revienta)
    with pytest.raises(RuntimeError):
        ejecutar(NOMBRE_ESCRITURA, {'chn_code': 'CHN-1'})


def test_la_escritura_se_delega_entera_al_guardrail(monkeypatch):
    """El guardrail RN-01 vive DENTRO de la herramienta para viajar con ella al
    MCP. El despachador no lo replica: lo llama y devuelve lo que diga."""
    visto = {}

    def falso(argumentos):
        visto.update(argumentos)
        return {'preparado': False, 'motivo': 'faltan naranjas por resolver'}

    monkeypatch.setattr(acciones, 'ejecutar_escritura', falso)
    obs = ejecutar(NOMBRE_ESCRITURA, {'chn_code': 'CHN-2026-09-07-0001'})

    assert obs == {'preparado': False, 'motivo': 'faltan naranjas por resolver'}
    assert visto == {'chn_code': 'CHN-2026-09-07-0001'}


# --- ejecutar: el RAG -------------------------------------------------------

def test_el_rag_devuelve_respuesta_con_documento_seccion_y_similitud(monkeypatch):
    citas = [resultado('FSD_vFinal.md', '5 Reglas de negocio > RN-02', 0.81)]
    montar_rag(monkeypatch, RespuestaRag(responde=True, texto='Confianza < 0.85.',
                                         citas=citas, candidatos=citas))

    obs = ejecutar(NOMBRE_RAG, {'pregunta': '¿que es un naranja?'})

    assert obs['encontrado'] is True
    assert obs['respuesta'] == 'Confianza < 0.85.'
    assert obs['fuentes'] == [{'documento': 'FSD_vFinal.md',
                               'seccion': '5 Reglas de negocio > RN-02',
                               'similitud': '81.0%'}]


def test_un_fragmento_sin_seccion_no_deja_el_campo_vacio(monkeypatch):
    """Se sustituye por una raya: un campo vacio en el prompt del modelo invita
    a rellenarlo por su cuenta."""
    citas = [resultado('ISCN 2024.md', None, 0.7)]
    montar_rag(monkeypatch, RespuestaRag(responde=True, texto='x', citas=citas,
                                         candidatos=citas))
    obs = ejecutar(NOMBRE_RAG, {'pregunta': 'p'})
    assert obs['fuentes'][0]['seccion'] == '—'


def test_el_no_se_del_rag_viaja_con_sugerencias(monkeypatch):
    """La prueba que mas importa de este modulo.

    Cuando el corpus no responde, el modelo recibe `encontrado: False` mas una
    lista de por donde seguir. Sin ella el agente se da por vencido en el primer
    paso; con ella reformula. Se midio: es la diferencia entre 0/8 y 4/8.
    """
    candidatos = [resultado('ADR-0023.md', 'Decision > D2', 0.62),
                  resultado('ADR-0022.md', 'Decision > D1', 0.58)]
    montar_rag(monkeypatch, RespuestaRag(responde=False, texto='',
                                         candidatos=candidatos,
                                         motivo='el corpus no cubre la pregunta'))

    obs = ejecutar(NOMBRE_RAG, {'pregunta': '¿cual es el presupuesto?'})

    assert obs['encontrado'] is False
    assert obs['motivo'] == 'el corpus no cubre la pregunta'
    assert obs['sugerencias'], 'un «no lo sé» sin salida es un callejon'
    assert 'respuesta' not in obs      # no se fabrica un texto cuando no lo hay


def test_sin_motivo_se_explica_igualmente(monkeypatch):
    """`motivo` puede venir vacio; el modelo nunca recibe un fallo mudo."""
    montar_rag(monkeypatch, RespuestaRag(responde=False, texto='', motivo=''))
    obs = ejecutar(NOMBRE_RAG, {'pregunta': 'p'})
    assert obs['motivo'] == 'la documentación no cubre eso'


@pytest.mark.parametrize('argumentos', [{}, {'pregunta': None}])
def test_una_llamada_al_rag_sin_pregunta_no_revienta(monkeypatch, argumentos):
    """El modelo omite argumentos con mas frecuencia de la que parece."""
    recibido = montar_rag(monkeypatch,
                          RespuestaRag(responde=False, texto='',
                                       motivo='consulta vacía'))
    obs = ejecutar(NOMBRE_RAG, argumentos)
    assert recibido['pregunta'] == ''
    assert obs['encontrado'] is False
