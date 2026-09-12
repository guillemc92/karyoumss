"""Contrato del endpoint principal: `GET /api/clinic/samples/{id}/karyotype/`.

Valida la FORMA de la respuesta contra el JSON Schema de `contratos.py`:
campos, tipos, catalogos cerrados y codigos HTTP.

**No valida el contenido.** Que un cromosoma salga de la clase 7 o de la 12 lo
decide el modelo; afirmarlo aqui produciria una prueba que falla cada vez que el
clasificador mejora. Lo que no puede cambiar sin avisar es el contrato: si
`semaphore` dejara de ser uno de tres valores, el visor no sabria que color
pintar y RN-02 no sabria si bloquear.

Estas pruebas no encienden modelo ni red: crean el cariotipo en la base de
prueba y consultan el endpoint.
"""
from decimal import Decimal

import pytest
from jsonschema import Draft202012Validator

from apps.samples.contratos import (
    CLASES_CROMOSOMA,
    CODIGOS_HTTP,
    KARYOTYPE_SCHEMA,
    RESOLUCIONES,
    SEMAFOROS,
)
from apps.samples.models import Chromosome, Karyotype, Sample, SampleStatus

pytestmark = pytest.mark.django_db


def url(sample):
    return f'/api/clinic/samples/{sample.id}/karyotype/'


@pytest.fixture
def caso(analyst_user):
    """Un caso con los tres semaforos, para que el contrato se ejercite entero."""
    muestra = Sample.objects.create(chn_code='CHN-2026-09-07-0001',
                                    analyst=analyst_user,
                                    status=SampleStatus.READY,
                                    sample_type='sangre')
    k = Karyotype.objects.create(sample=muestra, model_version='opencv-v0+efnb3-v3')
    Chromosome.objects.create(karyotype=k, predicted_class='1', position_index=0,
                              confidence_score=Decimal('0.950'), order=0)   # verde
    Chromosome.objects.create(karyotype=k, predicted_class='21', position_index=0,
                              confidence_score=Decimal('0.400'), order=1,
                              resolution_status='PENDING')                  # naranja
    Chromosome.objects.create(karyotype=k, predicted_class='X', position_index=0,
                              confidence_score=None, order=2)               # rojo
    return muestra


def validar(payload):
    """Falla mostrando TODOS los incumplimientos, no solo el primero."""
    errores = sorted(Draft202012Validator(KARYOTYPE_SCHEMA).iter_errors(payload),
                     key=lambda e: list(e.path))
    assert not errores, '\n'.join(
        '%s: %s' % ('/'.join(str(p) for p in e.path) or '(raiz)', e.message)
        for e in errores)


# --- la forma ---------------------------------------------------------------

def test_la_respuesta_cumple_el_esquema(analyst_client, caso):
    r = analyst_client.get(url(caso))
    assert r.status_code == 200
    validar(r.json())


def test_el_esquema_es_valido_como_json_schema():
    """Un esquema mal escrito valida cualquier cosa y no protege de nada."""
    Draft202012Validator.check_schema(KARYOTYPE_SCHEMA)


def test_estan_todos_los_campos_obligatorios(analyst_client, caso):
    datos = analyst_client.get(url(caso)).json()
    for campo in KARYOTYPE_SCHEMA['required']:
        assert campo in datos, 'falta el campo obligatorio %s' % campo


def test_el_summary_no_admite_campos_de_mas(analyst_client, caso):
    """`additionalProperties: False` — el visor lee estos seis y solo estos."""
    resumen = analyst_client.get(url(caso)).json()['summary']
    assert set(resumen) == set(KARYOTYPE_SCHEMA['properties']['summary']['required'])


# --- los catalogos ----------------------------------------------------------

def test_los_semaforos_estan_dentro_del_catalogo(analyst_client, caso):
    datos = analyst_client.get(url(caso)).json()
    for c in datos['chromosomes']:
        assert c['semaphore'] in SEMAFOROS


def test_las_clases_estan_dentro_del_catalogo(analyst_client, caso):
    datos = analyst_client.get(url(caso)).json()
    for c in datos['chromosomes']:
        assert c['predicted_class'] in CLASES_CROMOSOMA


def test_las_resoluciones_estan_dentro_del_catalogo(analyst_client, caso):
    datos = analyst_client.get(url(caso)).json()
    for c in datos['chromosomes']:
        assert c['resolution_status'] in RESOLUCIONES


def test_is_blocked_es_booleano_no_cadena(analyst_client, caso):
    """RN-02 decide con este campo. Una cadena 'false' es verdadera en JS."""
    resumen = analyst_client.get(url(caso)).json()['summary']
    assert resumen['is_blocked'] is True or resumen['is_blocked'] is False


def test_los_conteos_del_summary_cuadran_con_los_cromosomas(analyst_client, caso):
    datos = analyst_client.get(url(caso)).json()
    s = datos['summary']
    assert s['total'] == len(datos['chromosomes'])
    assert s['green'] + s['orange'] + s['red'] == s['total']


# --- los codigos HTTP -------------------------------------------------------

def test_sin_token_devuelve_401(api_client, caso):
    assert api_client.get(url(caso)).status_code == 401


def test_un_analista_ajeno_al_caso_recibe_403(caso, django_user_model):
    """RN-06: el analista solo ve lo suyo."""
    from apps.samples.tests.conftest import auth_client
    otro = django_user_model.objects.create_user(username='dr_otro', password='x')
    assert auth_client(otro).get(url(caso)).status_code == 403


def test_el_supervisor_ve_cualquier_caso(supervisor_client, caso):
    r = supervisor_client.get(url(caso))
    assert r.status_code == 200
    validar(r.json())


def test_una_muestra_sin_cariotipo_devuelve_404(analyst_client, analyst_user):
    vacia = Sample.objects.create(chn_code='CHN-2026-09-07-0002',
                                  analyst=analyst_user,
                                  status=SampleStatus.PENDING_AI)
    assert analyst_client.get(url(vacia)).status_code == 404


def test_el_endpoint_no_devuelve_codigos_fuera_del_contrato(
        api_client, analyst_client, supervisor_client, caso, analyst_user):
    """Barrido de los cuatro escenarios declarados en CODIGOS_HTTP."""
    vacia = Sample.objects.create(chn_code='CHN-2026-09-07-0003',
                                  analyst=analyst_user,
                                  status=SampleStatus.PENDING_AI)
    observados = {
        api_client.get(url(caso)).status_code,
        analyst_client.get(url(caso)).status_code,
        supervisor_client.get(url(caso)).status_code,
        analyst_client.get(url(vacia)).status_code,
    }
    assert observados <= set(CODIGOS_HTTP), 'codigo fuera del contrato: %s' % (
        observados - set(CODIGOS_HTTP))
