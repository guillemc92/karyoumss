"""Contrato de errores: que cada fallo del dominio salga con SU codigo HTTP.

## El hueco que esto tapa

Los servicios estan bien probados: `test_supervisor_s2.py` comprueba que
`sign_report` levanta `MfaLockedError` cuando toca, `test_karyotype_p3.py` que
`reclassify_chromosome` levanta `CaseLockedError`, y asi. Lo que nadie
comprobaba es el **tramo siguiente**: que la vista traduzca esa excepcion al
codigo que el frontend espera.

Es un hueco de verdad, no formal. Si `MfaLockedError` acabara devolviendo 500 en
vez de 423, los tests de servicio seguirian en verde y la pantalla del
supervisor mostraria «error del sistema» donde deberia decir «cuenta bloqueada,
espere N minutos». El sintoma clinico es distinto y la accion del usuario
tambien.

Catorce codigos del contrato no aparecian en ninguna prueba del clinico. Tres de
ellos son reglas de negocio:

    SEGREGATION_VIOLATION   RN-06 — quien valida no puede firmar
    FORBIDDEN_OVERRIDE      RN-04 — el ISCN no se sobrescribe sin permiso
    SAMPLE_VALIDATED        no se borra un caso ya validado

## Por que en tabla y no un test por endpoint

Doce endpoints de cromosoma repiten literalmente las mismas dos guardas
(`_get_owned_sample_or_none` y `_get_owned_chromosome_or_error`). Probarlas una
a una serian 24 tests casi identicos —y la clase de duplicado que la Actividad 2
buscaba—. En tabla, un endpoint nuevo que olvide una guarda aparece como una
fila roja el dia que se anada a la lista.

No se dobla nada salvo la frontera MFA (`admin_client.verify_mfa`), que es red.
"""
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.samples.admin_client import MfaServiceError
from apps.samples.models import Chromosome, Karyotype, Sample, SampleStatus
from apps.samples.models_rbac import Opcion, PrivilegioIndividual
from apps.samples.services import (
    CaseBlockedError,
    CaseLockedError,
    ChnDuplicateError,
    CrossKaryotypeError,
    ImagenNoEsMetafaseError,
    InvalidClassError,
    InvalidDecisionError,
    JoinSelfError,
    MfaLockedError,
    MfaNotEnrolledError,
    NotAuditableError,
    NotOrangeError,
    NotSignableError,
    SameClassError,
    SegregationError,
    XaiRequiredError,
)

pytestmark = pytest.mark.django_db

UUID_INEXISTENTE = '00000000-0000-4000-8000-000000000000'


@pytest.fixture
def muestra(analyst_user):
    return Sample.objects.create(chn_code='CHN-2026-09-07-1000', analyst=analyst_user,
                                 status=SampleStatus.READY, sample_type='sangre')


@pytest.fixture
def caso(muestra):
    """Muestra CON cariotipo y un cromosoma, para poder llegar mas adentro."""
    k = Karyotype.objects.create(sample=muestra, model_version='v0')
    Chromosome.objects.create(karyotype=k, predicted_class='1', position_index=0,
                              confidence_score=Decimal('0.950'), order=0)
    return muestra


def cromosoma_de(sample):
    return sample.karyotype.chromosomes.first()


def borrar(sample):
    """Borrado logico. Las dos columnas van juntas por una CHECK constraint de
    la base (`samples_deactivated_implies_deleted_at`): desactivar sin registrar
    CUANDO no es un borrado, es un dato perdido. Ponerlo aqui evita que cada
    test lo redescubra con un IntegrityError."""
    sample.is_active = False
    sample.deleted_at = timezone.now()
    sample.save(update_fields=['is_active', 'deleted_at'])


# ---------------------------------------------------------------------------
# Las dos guardas que comparten TODOS los endpoints de cromosoma
# ---------------------------------------------------------------------------

# (nombre de ruta, metodo). Anadir un endpoint nuevo aqui es una linea.
ENDPOINTS_CROMOSOMA = [
    ('samples:chromosome-xai', 'post'),
    ('samples:chromosome-resolve', 'post'),
    ('samples:chromosome-anomaly', 'post'),
    ('samples:chromosome-reclassify', 'post'),
    ('samples:chromosome-split', 'post'),
    ('samples:chromosome-recrop', 'post'),
    ('samples:chromosome-join', 'post'),
    ('samples:chromosome-cross', 'post'),
]
IDS_CROMOSOMA = [n.split(':')[1] for n, _ in ENDPOINTS_CROMOSOMA]


def url_cromosoma(nombre, sample_id, chromo_id):
    return reverse(nombre, kwargs={'pk': sample_id, 'cid': chromo_id})


@pytest.mark.parametrize('nombre,metodo', ENDPOINTS_CROMOSOMA, ids=IDS_CROMOSOMA)
def test_sin_cariotipo_todos_responden_404_no_karyotype(analyst_client, muestra,
                                                        nombre, metodo):
    """Una muestra recien registrada no tiene cariotipo todavia.

    Es un estado NORMAL del flujo, no una anomalia: entre el registro y el
    procesamiento la muestra existe y no tiene cromosomas. Devolver 500 aqui
    convertiria un caso corriente en un incidente.
    """
    r = getattr(analyst_client, metodo)(
        url_cromosoma(nombre, muestra.id, UUID_INEXISTENTE), {}, format='json')
    assert r.status_code == 404
    assert r.json()['code'] == 'NO_KARYOTYPE'


@pytest.mark.parametrize('nombre,metodo', ENDPOINTS_CROMOSOMA, ids=IDS_CROMOSOMA)
def test_un_cromosoma_que_no_existe_da_404_chromosome_not_found(analyst_client, caso,
                                                                nombre, metodo):
    """Distinguirlo de NO_KARYOTYPE importa: el visor reacciona distinto a
    «este caso aun no se proceso» que a «ese cromosoma ya no esta»."""
    r = getattr(analyst_client, metodo)(
        url_cromosoma(nombre, caso.id, UUID_INEXISTENTE), {}, format='json')
    assert r.status_code == 404
    assert r.json()['code'] == 'CHROMOSOME_NOT_FOUND'


@pytest.mark.parametrize('nombre,metodo', ENDPOINTS_CROMOSOMA, ids=IDS_CROMOSOMA)
def test_un_cromosoma_de_otro_caso_no_se_alcanza(analyst_client, caso, analyst_user,
                                                 nombre, metodo):
    """RN-06 dentro del propio analista: los cromosomas se buscan SIEMPRE dentro
    del cariotipo de la muestra de la URL.

    Sin esta comprobacion, pasar el id de un cromosoma de otro caso editaria un
    caso distinto del que dice la URL — y la bitacora lo registraria contra el
    caso equivocado.
    """
    otro = Sample.objects.create(chn_code='CHN-2026-09-07-1001', analyst=analyst_user,
                                 status=SampleStatus.READY)
    k = Karyotype.objects.create(sample=otro, model_version='v0')
    ajeno = Chromosome.objects.create(karyotype=k, predicted_class='2',
                                      position_index=0, order=0)

    r = getattr(analyst_client, metodo)(
        url_cromosoma(nombre, caso.id, ajeno.id), {}, format='json')
    assert r.status_code == 404
    assert r.json()['code'] == 'CHROMOSOME_NOT_FOUND'


# ---------------------------------------------------------------------------
# Las guardas de propiedad, comunes a los endpoints de caso
# ---------------------------------------------------------------------------

# Los que puede tocar un analista: llevan opciones RBAC que su grupo si tiene.
ENDPOINTS_CASO = [
    ('samples:sample-process', 'post'),
    ('samples:sample-status', 'get'),
    ('samples:sample-karyotype', 'get'),
    ('samples:sample-validate', 'post'),
    ('samples:sample-audit', 'get'),
]
IDS_CASO = [n.split(':')[1] for n, _ in ENDPOINTS_CASO]

# Los del supervisor: exigen `case.sign`, que el analista NO tiene.
#
# Aqui NO hay fila de NOT_OWNER, y no es un olvido: `case.sign` solo lo tienen
# Supervisor y Admin, y `_get_owned_sample_or_none` deja pasar a todo `is_staff`
# sin mirar de quien es el caso. La rama NOT_OWNER de estos dos endpoints es
# **inalcanzable** con la matriz RBAC sembrada. Afirmarla seria inventarse un
# escenario que el sistema no produce.
ENDPOINTS_SUPERVISOR = [
    ('samples:case-narrative', 'post'),
    ('samples:case-iscn', 'post'),
]
IDS_SUPERVISOR = [n.split(':')[1] for n, _ in ENDPOINTS_SUPERVISOR]


@pytest.mark.parametrize('nombre,metodo', ENDPOINTS_SUPERVISOR, ids=IDS_SUPERVISOR)
def test_un_analista_no_alcanza_los_endpoints_de_firma(analyst_client, caso,
                                                       nombre, metodo):
    """RN-06 en la capa RBAC: la segregacion se corta antes de mirar el caso.

    El analista redacta y valida; narrar y nomenclar son pasos posteriores a la
    firma. El corte es de opcion (`case.sign`), no de propiedad — por eso el
    cuerpo no trae `code`: no llego a la vista.
    """
    url = reverse(nombre, kwargs={'pk': caso.id})
    r = (analyst_client.get(url) if metodo == 'get'
         else analyst_client.post(url, {}, format='json'))
    assert r.status_code == 403


@pytest.mark.parametrize('nombre,metodo', ENDPOINTS_SUPERVISOR, ids=IDS_SUPERVISOR)
def test_los_endpoints_de_firma_tambien_dan_404_si_no_hay_caso(supervisor_client,
                                                               nombre, metodo):
    url = reverse(nombre, kwargs={'pk': UUID_INEXISTENTE})
    r = (supervisor_client.get(url) if metodo == 'get'
         else supervisor_client.post(url, {}, format='json'))
    assert r.status_code == 404
    assert r.json()['code'] == 'NOT_FOUND'


@pytest.mark.parametrize('nombre,metodo', ENDPOINTS_SUPERVISOR, ids=IDS_SUPERVISOR)
def test_los_endpoints_de_firma_no_ven_una_muestra_borrada(supervisor_client, caso,
                                                           nombre, metodo):
    borrar(caso)
    url = reverse(nombre, kwargs={'pk': caso.id})
    r = (supervisor_client.get(url) if metodo == 'get'
         else supervisor_client.post(url, {}, format='json'))
    assert r.status_code == 404


@pytest.mark.parametrize('nombre,metodo', ENDPOINTS_CASO, ids=IDS_CASO)
def test_una_muestra_inexistente_da_404_not_found(analyst_client, nombre, metodo):
    url = reverse(nombre, kwargs={'pk': UUID_INEXISTENTE})
    r = (analyst_client.get(url) if metodo == 'get'
         else analyst_client.post(url, {}, format='json'))
    assert r.status_code == 404
    assert r.json()['code'] == 'NOT_FOUND'


@pytest.mark.parametrize('nombre,metodo', ENDPOINTS_CASO, ids=IDS_CASO)
def test_el_caso_de_otro_analista_da_403_not_owner(caso, django_user_model,
                                                   nombre, metodo):
    """RN-06. Es 403 y no 404 a proposito: el caso existe, y ocultarlo no
    aportaria nada frente a un usuario del propio laboratorio."""
    from apps.samples.tests.conftest import auth_client
    otro = django_user_model.objects.create_user(username='dr_ajeno', password='x')
    cliente = auth_client(otro)

    url = reverse(nombre, kwargs={'pk': caso.id})
    r = cliente.get(url) if metodo == 'get' else cliente.post(url, {}, format='json')
    assert r.status_code == 403
    assert r.json()['code'] == 'NOT_OWNER'


@pytest.mark.parametrize('nombre,metodo', ENDPOINTS_CASO, ids=IDS_CASO)
def test_una_muestra_borrada_deja_de_existir_para_la_api(analyst_client, caso,
                                                          nombre, metodo):
    """El borrado es logico (`is_active=False`), pero desde fuera es un borrado:
    si un endpoint olvidara filtrar por `is_active`, un caso eliminado seguiria
    siendo editable."""
    borrar(caso)

    url = reverse(nombre, kwargs={'pk': caso.id})
    r = (analyst_client.get(url) if metodo == 'get'
         else analyst_client.post(url, {}, format='json'))
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# La firma del supervisor: excepcion del servicio -> codigo HTTP
# ---------------------------------------------------------------------------

# Cada fila dice al supervisor algo distinto y le pide algo distinto. Colapsar
# dos de estas en el mismo codigo dejaria la pantalla sin saber que ofrecer.
FALLOS_DE_FIRMA = [
    (NotSignableError('el caso no esta validado'), 409, 'NOT_SIGNABLE'),
    (SegregationError('quien valido no puede firmar'), 403, 'SEGREGATION_VIOLATION'),
    (MfaLockedError('bloqueado por 3 intentos'), 423, 'MFA_LOCKED'),
    (MfaNotEnrolledError('sin MFA dado de alta'), 400, 'MFA_NOT_ENROLLED'),
    (MfaServiceError('backend-admin no responde'), 503, 'MFA_SERVICE'),
]
IDS_FIRMA = [f[2] for f in FALLOS_DE_FIRMA]


@pytest.mark.parametrize('excepcion,http,codigo', FALLOS_DE_FIRMA, ids=IDS_FIRMA)
def test_cada_fallo_de_firma_sale_con_su_codigo(supervisor_client, caso, monkeypatch,
                                                excepcion, http, codigo):
    """El servicio ya esta probado; lo que se prueba aqui es la TRADUCCION.

    `SEGREGATION_VIOLATION` es RN-06 y `MFA_LOCKED` es un 423, no un 500: la
    pantalla tiene que poder decir «espere» en vez de «error del sistema».
    """
    def revienta(*a, **kw):
        raise excepcion

    monkeypatch.setattr('apps.samples.views.sign_report', revienta)
    r = supervisor_client.post(reverse('samples:case-sign', kwargs={'pk': caso.id}),
                               {'mfa_code': '123456'}, format='json')
    assert r.status_code == http
    assert r.json()['code'] == codigo


def test_el_detalle_del_fallo_de_mfa_no_filtra_el_codigo(supervisor_client, caso,
                                                         monkeypatch):
    """El 503 lleva un mensaje fijo, no el texto de la excepcion.

    Es deliberado: la excepcion de `httpx` puede arrastrar la URL interna de
    backend-admin, y eso no tiene por que llegar al navegador.
    """
    def revienta(*a, **kw):
        raise MfaServiceError('http://admin.interno:8000/api/internal/mfa/verify/')

    monkeypatch.setattr('apps.samples.views.sign_report', revienta)
    r = supervisor_client.post(reverse('samples:case-sign', kwargs={'pk': caso.id}),
                               {'mfa_code': '123456'}, format='json')
    assert r.status_code == 503
    assert 'admin.interno' not in r.json()['detail']


# ---------------------------------------------------------------------------
# RN-04: el ISCN no se sobrescribe sin permiso
# ---------------------------------------------------------------------------

def sin_opcion(usuario, codigo):
    """Excepcion individual que QUITA una opcion (ADR-0019, deny-overrides).

    Es el mecanismo real del RBAC portado de MetaClass: la excepcion individual
    gana siempre sobre el grupo, para dar o para quitar. Se usa aqui porque la
    matriz sembrada da `case.override_iscn` a todo Supervisor, y sin quitarsela
    a alguien la rama FORBIDDEN_OVERRIDE de la vista no se puede alcanzar.
    """
    opcion = Opcion.objects.get(codigo=codigo)
    PrivilegioIndividual.objects.update_or_create(
        usuario=usuario, opcion=opcion, defaults={'permitido': False})


def test_un_override_de_iscn_sin_permiso_da_403(supervisor_client, supervisor_user,
                                                caso):
    """RN-04. No hay PATCH del ISCN: la unica via de cambio es un `override`
    justificado, y exige `case.override_iscn` ademas de `case.sign`.

    La comprobacion vive en la vista, despues del permiso de endpoint: sin este
    test, quitarla no rompe nada visible — el supervisor normal la tiene y
    pasaria igual.
    """
    sin_opcion(supervisor_user, 'case.override_iscn')

    r = supervisor_client.post(reverse('samples:case-iscn', kwargs={'pk': caso.id}),
                               {'override': '47,XY,+21', 'justification': 'a mano'},
                               format='json')
    assert r.status_code == 403
    assert r.json()['code'] == 'FORBIDDEN_OVERRIDE'


def test_al_mismo_usuario_sin_override_no_se_le_corta_el_calculo(supervisor_client,
                                                                 supervisor_user,
                                                                 caso):
    """La guarda es del override, no del endpoint.

    Mismo usuario y misma excepcion individual que el test anterior: lo unico
    que cambia es que no manda `override`. Si el corte estuviera puesto en el
    endpoint entero, este caso tambien daria 403 — y el supervisor no podria ni
    generar el ISCN normal.
    """
    sin_opcion(supervisor_user, 'case.override_iscn')

    r = supervisor_client.post(reverse('samples:case-iscn', kwargs={'pk': caso.id}),
                               {}, format='json')
    assert r.status_code != 403


def test_un_supervisor_normal_si_puede_sobrescribir(supervisor_client, caso):
    """El contrapunto: sin esto, los dos de arriba pasarian aunque el override
    estuviera prohibido para todo el mundo."""
    r = supervisor_client.post(reverse('samples:case-iscn', kwargs={'pk': caso.id}),
                               {'override': '47,XY,+21', 'justification': 'a mano'},
                               format='json')
    # Pasa la guarda de permiso; que despues el caso no este firmado (409
    # NOT_REPORTABLE) es otra regla, y no es la que se prueba aqui.
    assert r.status_code != 403


# ---------------------------------------------------------------------------
# El borrado y el registro
# ---------------------------------------------------------------------------

def test_no_se_borra_una_muestra_validada(admin_client, caso):
    """El caso validado es el insumo del informe: borrarlo romperia la
    trazabilidad que RN-05 exige mantener."""
    caso.status = SampleStatus.VALIDATED
    caso.save(update_fields=['status'])

    r = admin_client.delete(reverse('samples:sample-detail', kwargs={'pk': caso.id}))
    assert r.status_code == 409
    assert r.json()['code'] == 'SAMPLE_VALIDATED'
    caso.refresh_from_db()
    assert caso.is_active is True      # y sigue ahi


def test_una_muestra_no_validada_si_se_borra(admin_client, caso):
    """El contrapunto: sin esto, el test de arriba pasaria aunque el DELETE
    estuviera roto para todos los casos."""
    r = admin_client.delete(reverse('samples:sample-detail', kwargs={'pk': caso.id}))
    assert r.status_code == 204
    caso.refresh_from_db()
    assert caso.is_active is False and caso.deleted_at is not None


# ---------------------------------------------------------------------------
# El agente: quedarse sin IA degrada, no rompe (RN-07)
# ---------------------------------------------------------------------------

def test_una_pregunta_vacia_al_agente_es_400_no_una_llamada_al_modelo(analyst_client,
                                                                      monkeypatch):
    """Se corta ANTES de gastar una llamada al modelo."""
    def no_deberia(*a, **kw):
        raise AssertionError('no deberia llegar al modelo')

    monkeypatch.setattr('apps.samples.agente.ejecutar_agente', no_deberia)
    r = analyst_client.post(reverse('samples:agente'), {'pregunta': '   '},
                            format='json')
    assert r.status_code == 400
    assert r.json()['code'] == 'VALIDATION_ERROR'


def test_sin_modelo_el_agente_responde_503_y_no_500(analyst_client, monkeypatch):
    """RN-07: sin IA el sistema degrada. Un 500 le diria al frontend que el
    fallo es suyo; el 503 con `AGENT_UNAVAILABLE` le dice que reintente."""
    from apps.samples.agente import AgenteError

    def sin_modelo(*a, **kw):
        raise AgenteError('modelo no disponible')

    monkeypatch.setattr('apps.samples.agente.ejecutar_agente', sin_modelo)
    r = analyst_client.post(reverse('samples:agente'), {'pregunta': '¿que casos hay?'},
                            format='json')
    assert r.status_code == 503
    assert r.json()['code'] == 'AGENT_UNAVAILABLE'


def test_sin_langgraph_la_memoria_se_declara_no_disponible(analyst_client, monkeypatch):
    """`thread_id` pide memoria conversacional (nivel 5). LangGraph se importa
    dentro de la vista para que su ausencia no impida arrancar el sistema; el
    endpoint tiene que decirlo con su propio codigo, distinto del anterior."""
    import builtins
    real = builtins.__import__

    def sin_grafo(nombre, *a, **kw):
        if 'agente_grafo' in nombre:
            raise ImportError('No module named langgraph')
        return real(nombre, *a, **kw)

    monkeypatch.setattr(builtins, '__import__', sin_grafo)
    r = analyst_client.post(reverse('samples:agente'),
                            {'pregunta': '¿y el primero?', 'thread_id': 'hilo-1'},
                            format='json')
    assert r.status_code == 503
    assert r.json()['code'] == 'MEMORY_UNAVAILABLE'


def test_el_catalogo_del_agente_se_publica_sin_modelo(analyst_client):
    """El GET describe lo que el agente sabe hacer y no invoca nada: tiene que
    responder aunque no haya IA encendida."""
    r = analyst_client.get(reverse('samples:agente'))
    assert r.status_code == 200
    assert r.json()['acciones'] and r.json()['max_pasos'] >= 1


# ---------------------------------------------------------------------------
# El resto del mapeo excepcion -> codigo, en una tabla
# ---------------------------------------------------------------------------
#
# Mismo hueco que con la firma, extendido a las ediciones del cariotipo y a la
# auditoria: los servicios levantan la excepcion correcta —eso ya lo prueban
# `test_karyotype_p2/p3.py` y `test_supervisor_s1.py`— pero nadie comprobaba que
# la vista la convirtiera en el codigo que el visor espera.
#
# Cada fila dice: endpoint, funcion del servicio a doblar, excepcion, HTTP,
# codigo. El servicio se sustituye porque montar el estado real que produce cada
# excepcion —un caso bloqueado, un cromosoma que no es naranja, dos cariotipos
# distintos— ya esta probado en su sitio; aqui se prueba la traduccion.

def _lanza(excepcion):
    def falso(*a, **kw):
        raise excepcion
    return falso


MAPEO_CROMOSOMA = [
    ('samples:chromosome-resolve', 'resolve_chromosome',
     XaiRequiredError('hay que ver el XAI primero'), 409, 'XAI_REQUIRED'),
    ('samples:chromosome-resolve', 'resolve_chromosome',
     NotOrangeError('no es naranja'), 400, 'NOT_ORANGE'),
    ('samples:chromosome-reclassify', 'reclassify_chromosome',
     CaseLockedError('el caso ya se valido'), 409, 'CASE_LOCKED'),
    ('samples:chromosome-reclassify', 'reclassify_chromosome',
     InvalidClassError('la clase 23 no existe'), 400, 'INVALID_CLASS'),
    ('samples:chromosome-reclassify', 'reclassify_chromosome',
     SameClassError('ya estaba en esa clase'), 400, 'SAME_CLASS'),
    ('samples:chromosome-split', 'split_chromosome',
     CaseLockedError('el caso ya se valido'), 409, 'CASE_LOCKED'),
    ('samples:chromosome-cross', 'resolve_cross',
     CaseLockedError('el caso ya se valido'), 409, 'CASE_LOCKED'),
]
IDS_MAPEO = [ruta.split(':')[1] + '-' + codigo
             for ruta, _s, _e, _h, codigo in MAPEO_CROMOSOMA]


@pytest.mark.parametrize('ruta,servicio,excepcion,http,codigo', MAPEO_CROMOSOMA,
                         ids=IDS_MAPEO)
def test_cada_fallo_de_edicion_sale_con_su_codigo(analyst_client, caso, monkeypatch,
                                                  ruta, servicio, excepcion, http,
                                                  codigo):
    """Un 409 y un 400 piden cosas distintas al analista: reintentar mas tarde
    frente a corregir lo que mando. Colapsarlos en un 500 los borra a los dos."""
    monkeypatch.setattr('apps.samples.views.' + servicio, _lanza(excepcion))

    r = analyst_client.post(url_cromosoma(ruta, caso.id, cromosoma_de(caso).id),
                            {'target_class': '7'}, format='json')
    assert r.status_code == http
    assert r.json()['code'] == codigo
    assert str(excepcion) in r.json()['detail']   # el motivo llega al usuario


@pytest.mark.parametrize('excepcion,http,codigo', [
    (CaseLockedError('el caso ya se valido'), 409, 'CASE_LOCKED'),
    (ValueError('el bbox se sale de la imagen'), 400, 'VALIDATION_ERROR'),
])
def test_el_recorte_manual_traduce_sus_dos_fallos(analyst_client, caso, monkeypatch,
                                                  excepcion, http, codigo):
    """`recrop_chromosome` se importa DENTRO del metodo de la vista, asi que el
    doble va en `services` y no en `views`. La diferencia importa: puesto en el
    sitio equivocado el test pasaria sin ejercitar nada."""
    monkeypatch.setattr('apps.samples.services.recrop_chromosome', _lanza(excepcion))

    r = analyst_client.post(
        url_cromosoma('samples:chromosome-recrop', caso.id, cromosoma_de(caso).id),
        {'bbox': {'x': 1, 'y': 1, 'w': 5, 'h': 5}}, format='json')
    assert r.status_code == http
    assert r.json()['code'] == codigo


# --- unir dos cromosomas ----------------------------------------------------

@pytest.mark.parametrize('excepcion,codigo', [
    (JoinSelfError('es el mismo cromosoma'), 'JOIN_SELF'),
    (CrossKaryotypeError('cariotipos distintos'), 'CROSS_KARYOTYPE'),
])
def test_unir_mal_da_400_con_el_codigo_que_lo_explica(analyst_client, caso,
                                                      monkeypatch, excepcion, codigo):
    """`CROSS_KARYOTYPE` no aparecia en ninguna prueba del clinico. Distingue
    «te equivocaste de cromosoma» de «este caso esta cerrado», y sin el codigo el
    visor solo podria decir «error»."""
    monkeypatch.setattr('apps.samples.views.join_chromosomes', _lanza(excepcion))

    r = analyst_client.post(
        url_cromosoma('samples:chromosome-join', caso.id, cromosoma_de(caso).id),
        {'other_id': str(cromosoma_de(caso).id)}, format='json')
    assert r.status_code == 400
    assert r.json()['code'] == codigo


def test_un_other_id_que_no_existe_se_corta_antes_del_servicio(analyst_client, caso,
                                                               monkeypatch):
    """La vista resuelve los DOS cromosomas antes de llamar al servicio. Si no,
    el servicio recibiria `None` y el fallo saldria como AttributeError."""
    monkeypatch.setattr('apps.samples.views.join_chromosomes',
                        _lanza(AssertionError('no deberia llamarse')))

    r = analyst_client.post(
        url_cromosoma('samples:chromosome-join', caso.id, cromosoma_de(caso).id),
        {'other_id': UUID_INEXISTENTE}, format='json')
    assert r.status_code == 404
    assert r.json()['code'] == 'CHROMOSOME_NOT_FOUND'


def test_validar_un_caso_con_naranjas_sin_resolver_da_409(analyst_client, caso,
                                                          monkeypatch):
    """RN-01 en la capa HTTP. El gate esta probado en el servicio; esto fija que
    el visor reciba CASE_BLOCKED y pueda decir cuantos quedan."""
    monkeypatch.setattr('apps.samples.views.validate_case',
                        _lanza(CaseBlockedError('quedan 3 naranjas sin resolver')))

    r = analyst_client.post(reverse('samples:sample-validate', kwargs={'pk': caso.id}),
                            {}, format='json')
    assert r.status_code == 409
    assert r.json()['code'] == 'CASE_BLOCKED'
    assert '3 naranjas' in r.json()['detail']


# --- la auditoria del 5 % ---------------------------------------------------

def test_decidir_sobre_un_cromosoma_fuera_de_la_muestra_del_5_da_404(
        supervisor_client, caso):
    """El supervisor solo audita los que salieron sorteados. Pedir decision
    sobre otro no es un error del sistema: es que ese no estaba en la muestra."""
    r = supervisor_client.post(
        reverse('samples:audit-decide',
                kwargs={'pk': caso.id, 'cid': cromosoma_de(caso).id}),
        {'decision': 'CONFIRMED'}, format='json')
    assert r.status_code == 404
    assert r.json()['code'] == 'REVIEW_NOT_FOUND'


@pytest.mark.parametrize('excepcion,http,codigo', [
    (NotAuditableError('el caso no esta validado'), 409, 'NOT_AUDITABLE'),
    (InvalidDecisionError('decision desconocida'), 400, 'INVALID_DECISION'),
])
def test_cada_fallo_de_auditoria_sale_con_su_codigo(supervisor_client, caso,
                                                    monkeypatch, excepcion, http,
                                                    codigo):
    cromo = cromosoma_de(caso)
    caso.audit_reviews.create(chromosome=cromo)
    monkeypatch.setattr('apps.samples.views.decide_audit', _lanza(excepcion))

    r = supervisor_client.post(
        reverse('samples:audit-decide', kwargs={'pk': caso.id, 'cid': cromo.id}),
        {'decision': 'CONFIRMED'}, format='json')
    assert r.status_code == http
    assert r.json()['code'] == codigo


def test_un_analista_no_puede_auditar(analyst_client, caso):
    """RN-06: la auditoria del 5 % es del supervisor. `case.audit` no lo tiene el
    analista, y el corte es de opcion, antes de mirar el caso."""
    r = analyst_client.get(reverse('samples:audit-review', kwargs={'pk': caso.id}))
    assert r.status_code == 403


# --- el registro: que codigo acompana a cada validacion ---------------------

# El serializer exige TRES metafases (RN: se capturan tres campos por caso), asi
# que un payload con menos ni siquiera llega al servicio. Este helper deja claro
# que el minimo es parte del contrato y no un detalle del fixture.
TRES_IMAGENES = [{'data_base64': 'Qk0=', 'filename': 'm%d.bmp' % i,
                  'source': 'upload'} for i in range(3)]


def test_menos_de_tres_metafases_se_rechaza_antes_del_servicio(analyst_client,
                                                               monkeypatch):
    """El corte esta en el serializer, no en el servicio: con dos imagenes el
    registro no llega a tocar la base ni a cifrar la PII."""
    monkeypatch.setattr('apps.samples.views.sample_registration_service.register',
                        _lanza(AssertionError('no deberia llegar al servicio')))

    r = analyst_client.post(reverse('samples:sample-register'), {
        'sample': {'chn_code': 'CHN-2026-09-07-1502', 'sample_type': 'sangre'},
        'patient': {'full_name': 'Paciente'},
        'images': TRES_IMAGENES[:2],
    }, format='json')
    assert r.status_code == 400
    assert r.json()['code'] == 'INSUFFICIENT_IMAGES'


def test_el_registro_sin_chn_lo_dice_con_su_codigo(analyst_client):
    """Un `VALIDATION_ERROR` generico obliga al frontend a leer prosa para saber
    que campo resaltar. El codigo concreto le dice donde poner el foco."""
    r = analyst_client.post(reverse('samples:sample-register'), {}, format='json')
    assert r.status_code == 400
    assert r.json()['code'] in ('CHN_REQUIRED', 'VALIDATION_ERROR')


def test_una_imagen_demasiado_pequena_se_rechaza_con_su_codigo(analyst_client,
                                                               monkeypatch):
    """El guardrail de metafase en la capa HTTP: distinto de VALIDATION_ERROR
    porque el fichero es valido — lo que no encaja es lo que muestra."""
    monkeypatch.setattr(
        'apps.samples.views.sample_registration_service.register',
        _lanza(ImagenNoEsMetafaseError('La imagen 1 mide 60x119 px')))

    r = analyst_client.post(reverse('samples:sample-register'), {
        'sample': {'chn_code': 'CHN-2026-09-07-1500', 'sample_type': 'sangre'},
        'patient': {'full_name': 'Paciente'},
        'images': TRES_IMAGENES,
    }, format='json')
    assert r.status_code == 400
    assert r.json()['code'] == 'IMAGE_TOO_SMALL'
    assert '60x119' in r.json()['detail']


def test_un_chn_repetido_es_409_no_400(analyst_client, monkeypatch):
    """Duplicar el CHN no es un dato mal escrito: es un caso que ya existe, y el
    analista tiene que ir a buscarlo en vez de corregir el formulario."""
    monkeypatch.setattr(
        'apps.samples.views.sample_registration_service.register',
        _lanza(ChnDuplicateError()))

    r = analyst_client.post(reverse('samples:sample-register'), {
        'sample': {'chn_code': 'CHN-2026-09-07-1501', 'sample_type': 'sangre'},
        'patient': {'full_name': 'Paciente'},
        'images': TRES_IMAGENES,
    }, format='json')
    assert r.status_code == 409
    assert r.json()['code'] == 'CHN_DUPLICATE'
