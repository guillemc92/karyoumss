"""Endpoint GET /api/clinic/samples/{id}/karyotype/ para agentes."""
pytestmark = pytest.mark.agente


def url(sample):
    return f'/api/clinic/samples/{sample.id}/karyotype/'


def validar(payload):
    """Falla mostrando TODOS los incumplimientos, no solo el primero."""
    errores = sorted(Draft202012Validator(KARYOTYPE_SCHEMA).iter_errors(payload),
                     key=lambda e: list(e.path))
    assert not errores, '\n'.join(
        '%s: %s' % ('/'.join(str(p) for p in e.path) or '(raiz)', e.message)
        for e in errores)


def test_admin_ve_cualquier_caso(supervisor_client, caso):
    r = supervisor_client.get(url(caso))
    assert r.status_code == 200
    validar(r.json())


def test_muestra_desactivada_devuelve_404(analyst_client, analyst_user):
    vacia = Sample.objects.create(chn_code='CHN-2026-09-07-0002',
                                  analyst=analyst_user,
                                  status=SampleStatus.PENDING_AI,
                                  is_active=False)
    assert analyst_client.get(url(vacia)).status_code == 404


def test_cromosomas_estan_ordenados_por_order(analyst_client, caso):
    datos = analyst_client.get(url(caso)).json()
    assert datos['chromosomes'][0]['order'] == 0
    assert datos['chromosomes'][1]['order'] == 1
    assert datos['chromosomes'][2]['order'] == 2


def test_sample_iscn_es_cadena_vacia_mientras_no_seha_generado(analyst_client, caso):
    datos = analyst_client.get(url(caso)).json()
    assert datos['sample_iscn'] == ''


def test_model_version_viaja_en_la_respuesta(analyst_client, caso):
    r = analyst_client.get(url(caso))
    assert r.json()['model_version'] is not None


def test_admin_ve_caso_desactivado(supervisor_client, caso):
    vacia = Sample.objects.create(chn_code='CHN-2026-09-07-0003',
                                  analyst=analyst_user,
                                  status=SampleStatus.PENDING_AI,
                                  is_active=False)
    r = supervisor_client.get(url(vacia))
    assert r.status_code == 200
    validar(r.json())
