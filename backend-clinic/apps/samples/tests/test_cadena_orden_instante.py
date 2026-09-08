"""Regresion: la cadena de auditoria no puede depender del azar.

## El fallo

`emit_audit_event` escribe en orden de insercion, pero `verify_audit_chain`
recorre con `order_by('created_at', 'id')`. Cuando dos eventos comparten el
instante, el desempate lo decide el `id`, que es un UUID ALEATORIO: la mitad de
las veces el segundo evento se verifica antes que el primero y la cadena entera
queda rota, con el mismo aspecto que tendria una manipulacion.

Se descubrio porque `test_karyotype_p4::test_mode_is_part_of_hash_chain` fallaba
1 de cada 3 ejecuciones. Una sonda que forzaba el mismo `created_at` en dos
eventos fallaba 7 de 12 vueltas: justo el ~50% que predice un desempate por
UUID.

## El arreglo

`_instante_posterior_a` garantiza un `created_at` estrictamente creciente por
caso. Estas pruebas van por `emit_audit_event`, que es el camino real: una
prueba que construyera los AuditEvent a mano se saltaria el arreglo y no
probaria nada.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.samples.models import AuditEvent, AuditEventType, Sample
from apps.samples.services import emit_audit_event, verify_audit_chain

TIPOS = [
    AuditEventType.XAI_VIEWED,
    AuditEventType.MARK_ANOMALY,
    AuditEventType.XAI_VIEWED,
    AuditEventType.MARK_ANOMALY,
]


@pytest.fixture
def caso(db):
    usuario = get_user_model().objects.create(username='orden_cadena')
    muestra = Sample.objects.create(chn_code='CHN-ORDEN-001', analyst=usuario)
    return muestra, usuario


@pytest.mark.django_db
@pytest.mark.parametrize('vuelta', range(10))
def test_eventos_seguidos_no_rompen_la_cadena(caso, vuelta):
    """Sin el arreglo esto fallaba de forma intermitente, no siempre.

    Por eso se repite 10 veces: una sola vuelta habria pasado la mitad de las
    veces y el fallo habria seguido escondido.
    """
    muestra, usuario = caso
    for tipo in TIPOS:
        emit_audit_event(muestra, usuario, tipo)
    assert verify_audit_chain(muestra) is True


@pytest.mark.django_db
def test_los_instantes_son_estrictamente_crecientes(caso):
    muestra, usuario = caso
    for tipo in TIPOS:
        emit_audit_event(muestra, usuario, tipo)

    instantes = list(
        AuditEvent.objects.filter(sample=muestra)
        .order_by('created_at', 'id')
        .values_list('created_at', flat=True)
    )
    assert instantes == sorted(instantes)
    assert len(set(instantes)) == len(instantes), 'hay dos eventos en el mismo instante'


@pytest.mark.django_db
def test_el_orden_de_verificacion_es_el_de_escritura(caso):
    """Lo que de verdad importa: que la bitacora se lea como se escribio."""
    muestra, usuario = caso
    for tipo in TIPOS:
        emit_audit_event(muestra, usuario, tipo)

    leidos = list(
        AuditEvent.objects.filter(sample=muestra)
        .order_by('created_at', 'id')
        .values_list('event_type', flat=True)
    )
    assert leidos == [str(t) for t in TIPOS]


@pytest.mark.django_db
def test_cada_evento_apunta_al_anterior(caso):
    muestra, usuario = caso
    for tipo in TIPOS:
        emit_audit_event(muestra, usuario, tipo)

    previo = ''
    for evento in AuditEvent.objects.filter(sample=muestra).order_by('created_at', 'id'):
        assert evento.previous_hash == previo
        previo = evento.current_hash
