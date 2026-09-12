"""Los tres guardrails «no negociables» del nivel 4, probados.

El material del módulo los enuncia así: **freno** (`MAX_PASOS`), **cinturón**
(confirmación de escritura) y **caja negra** (traza). Hasta aquí estaban
implementados y documentados, pero **sin un solo test**: la afirmación de que
este sistema es *más estricto* que el laboratorio se sostenía solo en el
docstring.

Un guardrail sin test es una intención. Si alguien invierte una condición
mañana, el sistema seguiría pareciendo seguro y nadie se enteraría.

El modelo se sustituye por un doble: lo que se mide aquí es la política y el
control del bucle, no la calidad de `llama3.2:3b` — eso se mide aparte, en
`eval_enrutado` y `eval_memoria`.
"""
import json

import pytest

from apps.samples.agente import MAX_PASOS, TEMPERATURA, AgenteError, ejecutar_agente
from apps.samples.agente_escritura import NOMBRE, SCHEMA, ejecutar, preparar_validacion
from apps.samples.models import Sample, SampleStatus

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------
# Doble del cliente OpenAI: devuelve mensajes preparados sin salir a la red.
# --------------------------------------------------------------------------
class _Funcion:
    def __init__(self, nombre, argumentos):
        self.name, self.arguments = nombre, argumentos


class _Llamada:
    def __init__(self, nombre, argumentos='{}', id_='c1'):
        self.id, self.function, self.type = id_, _Funcion(nombre, argumentos), 'function'


class _Mensaje:
    def __init__(self, contenido=None, tool_calls=None):
        self.content, self.tool_calls = contenido, tool_calls

    def model_dump(self, exclude_none=False):
        return {'role': 'assistant', 'content': self.content}


class _Uso:
    def __init__(self, entrada, salida):
        self.prompt_tokens, self.completion_tokens = entrada, salida


class _Respuesta:
    def __init__(self, mensaje, uso=None):
        self.choices = [type('C', (), {'message': mensaje})()]
        self.usage = uso


class ClienteFalso:
    """Va devolviendo el guion. Registra con qué parámetros se le llamó."""

    def __init__(self, guion):
        self.guion = list(guion)
        self.llamadas = []
        self.chat = type('Chat', (), {'completions': self})()

    def create(self, **kwargs):
        self.llamadas.append(kwargs)
        return self.guion.pop(0) if self.guion else _Respuesta(_Mensaje('fin'))


@pytest.fixture
def cliente(monkeypatch, settings):
    settings.CLINIC_LLM_ENABLED = True

    def montar(guion):
        falso = ClienteFalso(guion)
        monkeypatch.setattr('apps.samples.agente._cliente', lambda: falso)
        return falso

    return montar


def texto(contenido):
    return _Respuesta(_Mensaje(contenido))


def pide(nombre, argumentos='{}'):
    return _Respuesta(_Mensaje(None, [_Llamada(nombre, argumentos)]))


# ==========================================================================
# 1 · EL FRENO — «un agente sin tope es una fuga de dinero»
# ==========================================================================
class TestFreno:
    def test_un_modelo_que_nunca_para_se_corta_en_MAX_PASOS(self, cliente):
        falso = cliente([pide('T') for _ in range(50)])

        r = ejecutar_agente('bucle', [], lambda n, a: {'ok': 1}, 'sys')

        assert r.completado is False
        assert len(falso.llamadas) == MAX_PASOS

    def test_el_corte_queda_en_la_traza_y_no_se_disfraza_de_respuesta(self, cliente):
        cliente([pide('T') for _ in range(50)])

        r = ejecutar_agente('bucle', [], lambda n, a: {}, 'sys')

        assert any(p['tipo'] == 'corte' for p in r.traza.pasos)

    def test_el_tope_se_puede_bajar_pero_no_ignorar(self, cliente):
        falso = cliente([pide('T') for _ in range(50)])

        ejecutar_agente('x', [], lambda n, a: {}, 'sys', max_pasos=2)

        assert len(falso.llamadas) == 2

    def test_si_responde_texto_corta_antes_del_tope(self, cliente):
        falso = cliente([texto('ya está')])

        r = ejecutar_agente('x', [], lambda n, a: {}, 'sys')

        assert r.completado is True and len(falso.llamadas) == 1


class TestDecisionesReproducibles:
    def test_temperatura_cero_en_TODAS_las_llamadas(self, cliente):
        # Enrutar es una decisión técnica: la misma pregunta debe dar la misma
        # herramienta. Con temperatura > 0 el sistema deja de ser auditable.
        falso = cliente([pide('T'), texto('fin')])

        ejecutar_agente('x', [], lambda n, a: {}, 'sys')

        assert TEMPERATURA == 0.0
        assert all(ll['temperature'] == 0.0 for ll in falso.llamadas)


# ==========================================================================
# 2 · EL CINTURÓN — la escritura no ejecuta, ni confirmada
# ==========================================================================
class TestCinturon:
    """Aquí este sistema es MÁS estricto que el laboratorio de clase, donde
    `confirmado=true` sí ejecuta la acción."""

    def test_con_confirmado_true_NO_ejecuta(self):
        r = preparar_validacion('CHN-2026-08-06-0001', confirmado=True)

        assert r['ejecutado'] is False
        assert r['motivo'] == 'RN-01'

    def test_la_negativa_llega_ANTES_de_mirar_los_datos(self):
        # Con un caso inexistente y confirmado=true, la respuesta sigue siendo
        # la política: el guardrail no depende de que el caso exista.
        r = preparar_validacion('CHN-NO-EXISTE', confirmado=True)

        assert r['motivo'] == 'RN-01'
        assert 'error' not in r

    def test_sin_confirmar_devuelve_un_PLAN_y_tampoco_ejecuta(self, analyst_user):
        caso = Sample.objects.create(chn_code='CHN-G-1', patient_ref='ANON-G1',
                                     analyst=analyst_user, status=SampleStatus.READY)

        r = preparar_validacion(caso.chn_code)

        assert r['plan'] is True and r['ejecutado'] is False

    def test_el_estado_del_caso_NO_cambia_ni_confirmando(self, analyst_user):
        """La prueba de fondo: que la política no sea solo un mensaje."""
        caso = Sample.objects.create(chn_code='CHN-G-2', patient_ref='ANON-G2',
                                     analyst=analyst_user, status=SampleStatus.READY)

        preparar_validacion(caso.chn_code, confirmado=True)

        caso.refresh_from_db()
        assert caso.status == SampleStatus.READY

    def test_un_caso_inexistente_se_dice_no_se_inventa(self):
        r = preparar_validacion('CHN-FANTASMA')

        assert r['ejecutado'] is False and 'no existe' in r['error']

    def test_el_guardrail_viaja_en_la_DESCRIPCION_que_lee_el_modelo(self):
        # Se publica por MCP: el cliente que la descubra solo lee esto.
        descripcion = SCHEMA['function']['description']

        assert 'confirmado=false' in descripcion
        assert 'agente no puede validar' in descripcion

    def test_ejecutar_normaliza_argumentos_ausentes(self):
        assert ejecutar({})['ejecutado'] is False
        assert ejecutar(None)['ejecutado'] is False

    def test_el_nombre_publicado_es_el_que_espera_el_catalogo(self):
        assert SCHEMA['function']['name'] == NOMBRE


# ==========================================================================
# 3 · LA CAJA NEGRA — sin traza, un agente es un oráculo
# ==========================================================================
class TestCajaNegra:
    def test_registra_pregunta_accion_observacion_y_respuesta(self, cliente):
        cliente([pide('CONSULTA', '{"a": 1}'), texto('listo')])

        r = ejecutar_agente('que hay?', [], lambda n, a: {'n': 3}, 'sys')

        assert [p['tipo'] for p in r.traza.pasos] == [
            'pregunta', 'accion', 'observacion', 'respuesta']

    def test_la_observacion_lleva_lo_que_devolvio_la_herramienta(self, cliente):
        cliente([pide('CONSULTA'), texto('fin')])

        r = ejecutar_agente('x', [], lambda n, a: {'chn': 'CHN-1'}, 'sys')

        assert 'CHN-1' in [p for p in r.traza.pasos if p['tipo'] == 'observacion'][0]['detalle']

    def test_suma_los_tokens_para_poder_ver_el_coste(self, cliente):
        cliente([_Respuesta(_Mensaje(None, [_Llamada('T')]), _Uso(100, 10)),
                 _Respuesta(_Mensaje('fin'), _Uso(250, 20))])

        r = ejecutar_agente('x', [], lambda n, a: {}, 'sys')

        assert (r.traza.tokens_entrada, r.traza.tokens_salida) == (350, 30)

    def test_una_herramienta_que_revienta_NO_tumba_al_agente(self, cliente):
        """El error se le devuelve como observación para que rectifique."""
        def revienta(nombre, args):
            raise RuntimeError('la base no responde')

        cliente([pide('T'), texto('lo siento')])

        r = ejecutar_agente('x', [], revienta, 'sys')

        assert r.completado is True
        assert any('la base no responde' in p['detalle'] for p in r.traza.pasos)

    def test_argumentos_json_invalidos_no_rompen_el_bucle(self, cliente):
        # El modelo puede emitir JSON malformado; el bucle lo trata como {}.
        recibidos = []
        cliente([pide('T', '{esto no es json'), texto('fin')])

        r = ejecutar_agente('x', [], lambda n, a: recibidos.append(a) or {}, 'sys')

        assert recibidos == [{}] and r.completado is True

    def test_la_traza_es_serializable_para_devolverla_por_la_API(self, cliente):
        cliente([pide('T'), texto('fin')])

        r = ejecutar_agente('x', [], lambda n, a: {'ok': True}, 'sys')

        json.dumps(r.traza.as_dict())      # no debe lanzar


# ==========================================================================
# 4 · DEGRADACIÓN (RN-07) — sin IA se avisa, no se revienta
# ==========================================================================
class TestDegradacion:
    def test_con_la_IA_apagada_lanza_AgenteError(self, settings):
        settings.CLINIC_LLM_ENABLED = False

        with pytest.raises(AgenteError):
            ejecutar_agente('x', [], lambda n, a: {}, 'sys')

    def test_si_el_modelo_falla_se_convierte_en_AgenteError_con_traza(self, cliente, settings):
        settings.CLINIC_LLM_ENABLED = True

        class Cae:
            def create(self, **kwargs):
                raise RuntimeError('connection refused')

        falso = ClienteFalso([])
        falso.chat = type('Chat', (), {'completions': Cae()})()
        import apps.samples.agente as mod
        mod._cliente = lambda: falso

        with pytest.raises(AgenteError, match='connection refused'):
            ejecutar_agente('x', [], lambda n, a: {}, 'sys')


class TestElPlanDiceQueBloquea:
    """El valor del plan no es decir «no puedo»: es decir POR QUÉ no se puede,
    para que la persona no tenga que ir a buscarlo."""

    def test_avisa_si_el_caso_no_esta_en_READY(self, analyst_user):
        caso = Sample.objects.create(chn_code='CHN-G-3', patient_ref='ANON-G3',
                                     analyst=analyst_user,
                                     status=SampleStatus.ANALYST_VALIDATED)

        r = preparar_validacion(caso.chn_code)

        assert any('ANALYST_VALIDATED' in b for b in r['bloqueos'])

    def test_cuenta_los_naranjas_sin_resolver_y_cita_RN_02(self, analyst_user):
        from decimal import Decimal

        from apps.samples.models import Chromosome, Karyotype

        caso = Sample.objects.create(chn_code='CHN-G-4', patient_ref='ANON-G4',
                                     analyst=analyst_user, status=SampleStatus.READY)
        karyo = Karyotype.objects.create(sample=caso, model_version='test-v0')
        for i in range(3):
            Chromosome.objects.create(karyotype=karyo, predicted_class='1',
                                      confidence_score=Decimal('0.400'),
                                      position_index=i, order=i,
                                      resolution_status='PENDING')

        r = preparar_validacion(caso.chn_code)

        assert r['naranjas_sin_resolver'] == 3
        assert any('RN-02' in b for b in r['bloqueos'])

    def test_un_caso_limpio_dice_que_puede_validarse(self, analyst_user):
        caso = Sample.objects.create(chn_code='CHN-G-5', patient_ref='ANON-G5',
                                     analyst=analyst_user, status=SampleStatus.READY)

        r = preparar_validacion(caso.chn_code)

        assert r['bloqueos'] == ['ninguno: el caso puede validarse']
