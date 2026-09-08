"""Las salidas de emergencia de `services.py`: integridad y degradacion.

Lo que queda sin cubrir de un servicio bien probado casi nunca es el camino
feliz — son las ramas que solo ocurren cuando algo va mal. Aqui estan las que
importan del nucleo clinico, agrupadas por lo que protegen:

    integridad     RN-05: la cadena de auditoria detecta que la tocaron
    bloqueo        RN-01/RN-02: rojo bloquea igual que naranja sin resolver
    degradacion    RN-07: sin imagen, sin disco o sin modelo se sigue trabajando

La de integridad es la mas seria. `verify_audit_chain` devuelve `True` si la
cadena esta intacta, y **nadie comprobaba que devolviera False**: una funcion de
verificacion que solo se prueba con datos buenos es una funcion que no se ha
probado.

Se dobla solo la frontera con backend-ml (`pipeline_client`). La base, los
hashes y el disco son reales.
"""
import base64
import struct
from decimal import Decimal

import pytest

from apps.samples.models import (
    AuditEvent,
    AuditEventError,
    Chromosome,
    Karyotype,
    Sample,
    SampleStatus,
)
from apps.samples.pipeline_client import MLDegradedError
from apps.samples.services import (
    SampleRegistrationService,
    _pedir_heatmap,
    _unresolved_count,
    emit_audit_event,
    reprocess_sample,
    verify_audit_chain,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def muestra(analyst_user):
    return Sample.objects.create(chn_code='CHN-2026-09-07-2000', analyst=analyst_user,
                                 status=SampleStatus.READY)


def bmp(ancho=1024, alto=768):
    """BMP minimo que pasa el guardrail de metafase: las dimensiones estan en
    los bytes 18..26 y `es_metafase_plausible` exige 640x480."""
    return b'BM' + b'\x00' * 16 + struct.pack('<ii', ancho, alto) + b'\x00' * 200


def cromosoma(karyotype, clase='1', confianza='0.950', **extra):
    return Chromosome.objects.create(
        karyotype=karyotype, predicted_class=clase, position_index=0,
        confidence_score=Decimal(confianza) if confianza is not None else None,
        order=karyotype.chromosomes.count(), **extra)


# --- RN-05: la cadena detecta que la tocaron --------------------------------

def test_una_cadena_intacta_se_verifica(muestra, analyst_user):
    for i in range(3):
        emit_audit_event(muestra, analyst_user, 'SAMPLE_VIEWED', payload={'n': i})
    assert verify_audit_chain(muestra) is True


def test_el_modelo_ni_siquiera_deja_reescribir_un_evento(muestra, analyst_user):
    """Primera capa de RN-05: el ORM bloquea el UPDATE.

    Es lo que protege del error honesto —un `save()` de mas en un servicio—, y
    por eso el ataque de abajo tiene que hacerse por SQL crudo.
    """
    evento = emit_audit_event(muestra, analyst_user, 'SAMPLE_VIEWED', payload={'n': 0})
    evento.payload = {'n': 'otro'}

    with pytest.raises(AuditEventError):
        evento.save(update_fields=['payload'])


def test_un_update_de_queryset_esquiva_el_guard_pero_no_la_cadena(muestra,
                                                                  analyst_user):
    """Segunda capa de RN-05, y la que justifica que la cadena exista.

    El guard de RN-05 esta en `Model.save()`, y **`QuerySet.update()` no pasa por
    ahi**: escribe SQL directo. Lo mismo vale para cualquiera con acceso a la
    base. Es decir, la primera capa protege del error honesto, no de la
    manipulacion.

    Lo que no se puede rehacer sin recalcular la cadena entera es el hash — y eso
    es justo lo que `verify_audit_chain` detecta. Sin esta prueba, la funcion
    solo se habia ejercitado con datos buenos: nunca se comprobo que supiera
    decir que NO.
    """
    for i in range(3):
        emit_audit_event(muestra, analyst_user, 'SAMPLE_VIEWED', payload={'n': i})

    intermedio = AuditEvent.objects.filter(sample=muestra).order_by('created_at')[1]
    escritas = AuditEvent.objects.filter(id=intermedio.id).update(
        payload={'n': 'reescrito'})

    assert escritas == 1, 'el update no llego a la fila: el test no probaria nada'
    assert verify_audit_chain(muestra) is False


def test_si_se_borra_un_eslabon_la_cadena_se_rompe(muestra, analyst_user):
    """RN-05 es append-only. Borrar por debajo deja al siguiente evento
    apuntando a un `previous_hash` que ya no existe."""
    for i in range(3):
        emit_audit_event(muestra, analyst_user, 'SAMPLE_VIEWED', payload={'n': i})

    AuditEvent.objects.filter(sample=muestra).order_by('created_at')[1].delete()

    assert verify_audit_chain(muestra) is False


def test_un_caso_sin_eventos_tiene_una_cadena_valida(muestra):
    """Vacio no es corrupto: una muestra recien creada aun no ha hecho nada."""
    assert verify_audit_chain(muestra) is True


# --- RN-01/RN-02: que bloquea la emision ------------------------------------

def test_un_rojo_bloquea_igual_que_un_naranja_sin_resolver(muestra):
    """Rojo es «sin confianza», no «confianza baja»: son cosas distintas.

    El naranja se resuelve mirando el mapa de calor; el rojo exige intervencion
    manual. Los dos bloquean, y contarlos por separado seria un error facil de
    cometer porque solo el naranja tiene `resolution_status`.
    """
    k = Karyotype.objects.create(sample=muestra)
    cromosoma(k, confianza=None)                                  # rojo
    cromosoma(k, confianza='0.400', resolution_status='PENDING')  # naranja
    cromosoma(k, confianza='0.990')                               # verde

    assert _unresolved_count(k) == 2


def test_un_naranja_resuelto_deja_de_bloquear_pero_el_rojo_no(muestra):
    k = Karyotype.objects.create(sample=muestra)
    cromosoma(k, confianza='0.400', resolution_status='RESOLVED')
    cromosoma(k, confianza=None)

    assert _unresolved_count(k) == 1, 'el rojo no se resuelve marcandolo'


def test_un_fragmento_absorbido_por_un_join_ya_no_cuenta(muestra):
    """P3 desactiva el cromosoma absorbido. Si siguiera contando, un caso
    quedaria bloqueado para siempre por un fragmento que ya no existe."""
    k = Karyotype.objects.create(sample=muestra)
    cromosoma(k, confianza=None, is_active=False)

    assert _unresolved_count(k) == 0


# --- RN-07: degradar es seguir trabajando -----------------------------------

def test_sin_imagen_la_muestra_se_registra_igual_en_pending_ai(analyst_user):
    """Si ninguna imagen se puede decodificar, la muestra NO se pierde: queda
    persistida sin cariotipo y se puede reprocesar. Perder el registro seria
    perder tambien la PII que ya se cifro."""
    servicio = SampleRegistrationService()
    resultado = servicio.register({
        'sample': {'chn_code': 'CHN-2026-09-07-2001', 'sample_type': 'sangre'},
        'patient': {'full_name': 'Paciente Uno'},
        'images': [{'data_base64': 'esto no es base64 !!!', 'filename': 'a.bmp',
                    'source': 'upload'}],
    }, analyst_user)

    assert resultado['status'] == SampleStatus.PENDING_AI
    assert Sample.objects.filter(chn_code='CHN-2026-09-07-2001').exists()


def test_una_imagen_ilegible_no_impide_usar_la_siguiente(analyst_user, monkeypatch):
    """`_first_image_bytes` recorre hasta encontrar una que decodifique.

    Rendirse en la primera dejaria sin analizar un caso en el que la metafase
    buena era la segunda.
    """
    from apps.samples import services

    vistas = []
    monkeypatch.setattr(services.pipeline_client, 'segment_image',
                        lambda raw, **kw: vistas.append(raw) or {'chromosomes': []})

    buena = base64.b64encode(bmp()).decode()
    servicio = SampleRegistrationService()
    servicio.register({
        'sample': {'chn_code': 'CHN-2026-09-07-2002', 'sample_type': 'sangre'},
        'patient': {'full_name': 'Paciente Dos'},
        'images': [{'data_base64': 'esto no es base64 !!!', 'filename': 'a.bmp',
                    'source': 'upload'},
                   {'data_base64': buena, 'filename': 'b.bmp', 'source': 'upload'}],
    }, analyst_user)

    assert vistas, 'no se llego a segmentar: se rindio en la primera imagen'
    assert vistas[0].startswith(b'BM')


def test_reprocesar_sin_la_imagen_en_disco_degrada_con_motivo(muestra, monkeypatch):
    """La fila de la imagen existe pero el fichero no: pasa al restaurar una base
    sin su carpeta de medios. Tiene que salir como ML_DEGRADED —reintentable—
    y no como un 500."""
    muestra.images.create(image_path='no/existe.bmp', order=0)

    with pytest.raises(MLDegradedError, match='no encontrada'):
        reprocess_sample(muestra)


def test_reprocesar_sin_ninguna_imagen_tambien_degrada(muestra):
    with pytest.raises(MLDegradedError, match='sin imagen'):
        reprocess_sample(muestra)


# --- BR-004: el gate se cumple aunque no haya explicacion -------------------

def test_sin_bbox_no_hay_mapa_pero_se_dice_por_que(muestra):
    """Casos anteriores a P3 no tienen bbox. El gate BR-004 tiene que poder
    cumplirse igual: lo que no se hace es devolver un mapa falso."""
    k = Karyotype.objects.create(sample=muestra)
    c = cromosoma(k)

    r = _pedir_heatmap(muestra, c)
    assert r['xai_disponible'] is False
    assert 'bbox' in r['motivo']


def test_sin_imagen_en_la_muestra_tampoco_hay_mapa(muestra):
    k = Karyotype.objects.create(sample=muestra)
    c = cromosoma(k, bbox={'x': 1, 'y': 1, 'w': 10, 'h': 20})

    r = _pedir_heatmap(muestra, c)
    assert r['xai_disponible'] is False
    assert 'imagen' in r['motivo']


def test_con_el_fichero_ausente_el_motivo_lo_distingue(muestra):
    """«la muestra no tiene imagen» y «imagen no encontrada» son problemas
    distintos: uno es de registro, el otro de almacenamiento."""
    muestra.images.create(image_path='no/existe.bmp', order=0)
    k = Karyotype.objects.create(sample=muestra)
    c = cromosoma(k, bbox={'x': 1, 'y': 1, 'w': 10, 'h': 20})

    assert _pedir_heatmap(muestra, c)['motivo'] == 'imagen no encontrada'


def test_si_backend_ml_esta_caido_el_gate_sigue_pudiendose_cumplir(
        muestra, monkeypatch, tmp_path, settings):
    """RN-07 en su forma mas exigente: una caida de inferencia no puede bloquear
    la validacion clinica de TODOS los casos."""
    from apps.samples import services

    settings.MEDIA_ROOT = str(tmp_path)
    (tmp_path / 'metafase.bmp').write_bytes(b'BM' + b'\x00' * 200)
    muestra.images.create(image_path='metafase.bmp', order=0)

    k = Karyotype.objects.create(sample=muestra)
    c = cromosoma(k, bbox={'x': 1, 'y': 1, 'w': 10, 'h': 20})

    def caido(*a, **kw):
        raise MLDegradedError('circuit_open')

    monkeypatch.setattr(services.pipeline_client, 'xai_heatmap', caido)

    r = _pedir_heatmap(muestra, c)
    assert r['xai_disponible'] is False
    assert 'circuit_open' in r['motivo']
    assert 'heatmap_base64' not in r, 'no se inventa un mapa cuando no lo hay'
