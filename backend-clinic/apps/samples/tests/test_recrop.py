"""Tests del recorte manual de un cromosoma (RECROP).

Lo que se fija aquí es la propiedad que da sentido a la función: **corregir el
recorte tiene que arrastrar una nueva clasificación**. La segmentación falla por
sub-segmentación —cúmulos contados como uno— y ese recorte malo es el origen
medido de las falsas «clase 1». Si el recorte se corrigiera sin reclasificar, el
sistema mostraría una clase calculada sobre píxeles que ya nadie ve.

El servicio de inferencia se sustituye por un doble: estos tests miden la
lógica clínica, no la precisión del modelo.
"""
from decimal import Decimal

import pytest

from apps.samples.models import AuditEvent, AuditEventType, Chromosome, Sample
from apps.samples.pipeline_client import MLDegradedError
from apps.samples.services import recrop_chromosome

pytestmark = pytest.mark.django_db


BBOX_NUEVO = {'x': 10, 'y': 20, 'w': 30, 'h': 90}


@pytest.fixture
def own_sample(analyst_user):
    """El caso del analista, en READY (editable)."""
    return Sample.objects.create(chn_code='CHN-2026-08-17-RC1', patient_ref='ANON-RC',
                                 analyst=analyst_user, status='READY')


@pytest.fixture
def cromosoma(own_sample):
    """Un cromosoma con bbox, como los que produce la segmentación."""
    from apps.samples.models import Karyotype

    karyo = Karyotype.objects.create(sample=own_sample, model_version='test-v0')
    return Chromosome.objects.create(
        karyotype=karyo,
        predicted_class='1',
        confidence_score=Decimal('0.310'),
        position_index=0,
        order=0,
        bbox={'x': 10, 'y': 20, 'w': 80, 'h': 90},
    )


@pytest.fixture
def clasificador(monkeypatch):
    """Doble del servicio de inferencia: devuelve la clase que se le diga."""
    llamadas = []

    def falso(image_bytes, bbox, filename='m.bmp'):
        llamadas.append(bbox)
        return {'predicted_class': '3', 'confidence_score': 0.62}

    monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop', falso)
    return llamadas


@pytest.fixture
def imagen(own_sample, tmp_path, settings):
    """Una imagen real en MEDIA_ROOT: sin ella no hay nada que reclasificar."""
    from apps.samples.models import SampleImage

    settings.MEDIA_ROOT = str(tmp_path)
    ruta = tmp_path / 'metafase.bmp'
    ruta.write_bytes(b'BM' + b'\x00' * 100)
    return SampleImage.objects.create(sample=own_sample, image_path='metafase.bmp',
                                      order=0, source='upload')


class TestReclasificacion:
    def test_el_recorte_arrastra_una_clase_nueva(self, own_sample, cromosoma,
                                                 imagen, clasificador, analyst_user):
        """Es la razón de ser de la función: la clase anterior se calculó sobre
        un recorte que ya no existe."""
        actualizado = recrop_chromosome(own_sample, cromosoma, BBOX_NUEVO, analyst_user)

        assert actualizado.predicted_class == '3'
        assert actualizado.confidence_score == Decimal('0.62')
        assert actualizado.bbox == BBOX_NUEVO

    def test_se_clasifica_con_el_bbox_NUEVO(self, own_sample, cromosoma, imagen,
                                            clasificador, analyst_user):
        """Clasificar con el bbox viejo daría exactamente la clase que se
        intenta corregir."""
        recrop_chromosome(own_sample, cromosoma, BBOX_NUEVO, analyst_user)

        assert clasificador == [BBOX_NUEVO]


class TestVuelveALaCola:
    def test_un_recorte_nuevo_reabre_la_revision(self, own_sample, cromosoma,
                                                 imagen, clasificador, analyst_user):
        """La decisión anterior se tomó mirando otros píxeles: no vale."""
        cromosoma.resolution_status = 'RESOLVED'
        cromosoma.xai_viewed = True
        cromosoma.save(update_fields=['resolution_status', 'xai_viewed'])

        actualizado = recrop_chromosome(own_sample, cromosoma, BBOX_NUEVO, analyst_user)

        assert actualizado.resolution_status == 'PENDING'
        assert actualizado.xai_viewed is False


class TestDegradacion:
    def test_sin_IA_se_guarda_el_recorte_igual(self, own_sample, cromosoma, imagen,
                                               monkeypatch, analyst_user):
        """Perder la corrección manual del analista por una caída de
        infraestructura sería peor que quedarse sin reclasificar (RN-07)."""
        def cae(*_a, **_k):
            raise MLDegradedError('circuit_open')

        monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop', cae)

        actualizado = recrop_chromosome(own_sample, cromosoma, BBOX_NUEVO, analyst_user)

        assert actualizado.bbox == BBOX_NUEVO
        assert actualizado.predicted_class == '1'  # se conserva la anterior

    def test_la_traza_dice_que_NO_se_reclasifico(self, own_sample, cromosoma, imagen,
                                                 monkeypatch, analyst_user):
        """Si no se reclasificó, tiene que constar: si no, un revisor creería
        que la clase corresponde al recorte nuevo."""
        monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop',
                            lambda *a, **k: (_ for _ in ()).throw(MLDegradedError('caido')))

        recrop_chromosome(own_sample, cromosoma, BBOX_NUEVO, analyst_user)

        ev = AuditEvent.objects.filter(sample=own_sample,
                                       event_type=AuditEventType.RECROP).latest('created_at')
        assert ev.payload['reclasificado'] is False
        assert 'caido' in ev.payload['motivo']


class TestTraza:
    def test_guarda_el_antes_y_el_despues(self, own_sample, cromosoma, imagen,
                                          clasificador, analyst_user):
        """Es lo que permite revisar si la corrección manual mejoró el caso."""
        bbox_previo = dict(cromosoma.bbox)

        recrop_chromosome(own_sample, cromosoma, BBOX_NUEVO, analyst_user)

        ev = AuditEvent.objects.filter(sample=own_sample,
                                       event_type=AuditEventType.RECROP).latest('created_at')
        assert ev.payload['bbox_previo'] == bbox_previo
        assert ev.payload['bbox_nuevo'] == BBOX_NUEVO
        assert ev.payload['clase_previa'] == '1'
        assert ev.payload['clase_nueva'] == '3'


class TestValidacion:
    @pytest.mark.parametrize('bbox', [
        {},
        {'x': 1, 'y': 2},                       # incompleto
        {'x': 1, 'y': 2, 'w': 0, 'h': 10},      # ancho nulo
        {'x': 1, 'y': 2, 'w': 10, 'h': -5},     # alto negativo
    ])
    def test_un_bbox_invalido_se_rechaza(self, own_sample, cromosoma, imagen,
                                         clasificador, analyst_user, bbox):
        with pytest.raises(ValueError):
            recrop_chromosome(own_sample, cromosoma, bbox, analyst_user)

    def test_un_bbox_invalido_no_deja_evento(self, own_sample, cromosoma, imagen,
                                             clasificador, analyst_user):
        """Un rechazo no es un acto clínico: no debe ensuciar el audit trail."""
        with pytest.raises(ValueError):
            recrop_chromosome(own_sample, cromosoma, {}, analyst_user)

        assert not AuditEvent.objects.filter(sample=own_sample,
                                             event_type=AuditEventType.RECROP).exists()
