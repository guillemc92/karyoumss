"""Descartar y añadir objetos sobre la metafase (DD-KARYO-007 D5, T3).

Se fija:

- descartar es borrado suave con evento REJECT_OBJECT: la fila se queda, deja
  de contar en el cariotipo y el motivo es uno de los cuatro;
- añadir crea el cromosoma que la segmentación no vio, con la clase del modelo
  (y su semáforo) o la del analista (resuelto, confianza 0, dicho en el evento);
- sin IA y sin clase elegida NO se crea nada (503 CLASS_REQUIRED): una clase
  de relleno contaría en el ISCN;
- sin silueta se crea igual (se ve la caja, RN-07);
- caso validado 409, analista ajeno 403, nada borra eventos (RN-05).

backend-ml se sustituye por un doble: aquí se prueba la lógica clínica.
"""
import struct
from decimal import Decimal

import pytest

from apps.samples.models import (
    AuditEvent, AuditEventType, Chromosome, Karyotype, Sample, SampleImage, SampleImageSource,
)
from apps.samples.pipeline_client import MLDegradedError
from apps.samples.services import (
    CaseLockedError, ClaseRequeridaError, InvalidClassError, ObjetoInactivoError,
    SinMetafaseError, add_object, reject_object,
)

pytestmark = pytest.mark.django_db

CONTORNO = [[60, 40], [90, 40], [90, 120], [60, 120]]
CAJA = {'x': 60, 'y': 40, 'w': 30, 'h': 80}


def _bmp(ancho=200, alto=150) -> bytes:
    """Cabecera BMP con su tamaño: lo único que `dimensiones` lee."""
    cabecera = b'BM' + b'\x00' * 16 + struct.pack('<ii', ancho, alto)
    return cabecera + b'\x00' * 64


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def _caso(dueno, chn, media=None, status='READY', imagen=True):
    s = Sample.objects.create(chn_code=chn, patient_ref='ANON', analyst=dueno, status=status)
    k = Karyotype.objects.create(sample=s, model_version='test-v0')
    if imagen and media is not None:
        (media / chn).mkdir(parents=True, exist_ok=True)
        (media / chn / '0.img').write_bytes(_bmp())
        SampleImage.objects.create(sample=s, image_path=f'{chn}/0.img', order=0,
                                   source=SampleImageSource.UPLOAD)
    return s, k


def _crom(k, cls='7', order=0, activo=True, pos=0):
    return Chromosome.objects.create(
        karyotype=k, predicted_class=cls, position_index=pos, order=order,
        confidence_score=Decimal('0.950'), is_active=activo,
        bbox={'x': 10, 'y': 20, 'w': 30, 'h': 90},
    )


@pytest.fixture
def ml(monkeypatch):
    """Doble de backend-ml: clasifica como 21 con 0,91 y da una silueta por caja."""
    llamadas = {'classify': [], 'contours': []}

    def clasificar(image_bytes, bbox, filename=''):
        llamadas['classify'].append(dict(bbox))
        return {'predicted_class': '21', 'confidence_score': 0.91}

    def contornos(image_bytes, bboxes, filename=''):
        llamadas['contours'].append(list(bboxes))
        return [CONTORNO for _ in bboxes]

    monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop', clasificar)
    monkeypatch.setattr('apps.samples.services.pipeline_client.contours', contornos)
    return llamadas


def _caida(*a, **kw):
    raise MLDegradedError('circuit_open')


# ============================================================================
# Descartar
# ============================================================================
class TestDescartar:
    def test_borrado_suave_con_evento(self, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0101')
        c = _crom(k)
        reject_object(s, c, 'nucleo', analyst_user)
        c.refresh_from_db()
        assert c.is_active is False
        assert Chromosome.objects.filter(id=c.id).exists()  # la fila se queda (RN-05)
        ev = AuditEvent.objects.get(sample=s, event_type=AuditEventType.REJECT_OBJECT)
        assert ev.chromosome_id == c.id
        assert ev.payload['motivo'] == 'nucleo'
        assert ev.payload['clase'] == '7'
        assert ev.payload['bbox'] == {'x': 10, 'y': 20, 'w': 30, 'h': 90}

    @pytest.mark.parametrize('motivo', ['', 'basura', None])
    def test_motivo_invalido(self, analyst_user, motivo):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0102')
        c = _crom(k)
        with pytest.raises(ValueError):
            reject_object(s, c, motivo, analyst_user)
        c.refresh_from_db()
        assert c.is_active is True
        assert AuditEvent.objects.filter(sample=s).count() == 0

    def test_no_se_descarta_dos_veces(self, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0103')
        c = _crom(k, activo=False)
        with pytest.raises(ObjetoInactivoError):
            reject_object(s, c, 'suciedad', analyst_user)

    @pytest.mark.parametrize('estado', ['ANALYST_VALIDATED', 'VALIDATED'])
    def test_caso_validado(self, analyst_user, estado):
        s, k = _caso(analyst_user, f'CHN-2026-10-23-01{len(estado):02d}', status=estado)
        c = _crom(k)
        with pytest.raises(CaseLockedError):
            reject_object(s, c, 'otro', analyst_user)


# ============================================================================
# Añadir
# ============================================================================
class TestAnadir:
    def test_clase_del_modelo_y_silueta(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0111', media)
        _crom(k, cls='21', order=4, pos=0)
        c = add_object(s, CAJA, analyst_user)
        assert c.predicted_class == '21'
        assert c.confidence_score == Decimal('0.910')
        assert c.semaphore == 'green'
        assert c.resolution_status == 'AUTO'
        assert c.position_index == 1     # el segundo 21
        assert c.order == 5              # al final del orden de render
        assert c.bbox == CAJA
        assert c.contour == CONTORNO
        assert ml['classify'] == [CAJA]
        ev = AuditEvent.objects.get(sample=s, event_type=AuditEventType.ADD_OBJECT)
        assert ev.chromosome_id == c.id
        assert ev.payload == {'bbox': CAJA, 'clase': '21', 'confianza': '0.91',
                              'clasificado_por': 'modelo', 'con_silueta': True}

    def test_confianza_baja_entra_naranja_pendiente(self, analyst_user, media, ml, monkeypatch):
        monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop',
                            lambda *a, **kw: {'predicted_class': '19', 'confidence_score': 0.4})
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0112', media)
        c = add_object(s, CAJA, analyst_user)
        assert c.semaphore == 'orange'
        assert c.resolution_status == 'PENDING'   # RN-01: hay que revisarlo

    def test_clase_del_analista_no_pregunta_al_modelo(self, analyst_user, media, ml):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0113', media)
        c = add_object(s, CAJA, analyst_user, clase='22')
        assert ml['classify'] == []
        assert c.predicted_class == '22'
        assert c.confidence_score == Decimal('0')   # no la calculó nadie
        assert c.resolution_status == 'RESOLVED'    # autoridad del analista (BR-003)
        ev = AuditEvent.objects.get(sample=s, event_type=AuditEventType.ADD_OBJECT)
        assert ev.payload['clasificado_por'] == 'analista'

    def test_sin_ia_y_sin_clase_no_crea_nada(self, analyst_user, media, monkeypatch):
        monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop', _caida)
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0114', media)
        with pytest.raises(ClaseRequeridaError):
            add_object(s, CAJA, analyst_user)
        assert k.chromosomes.count() == 0
        assert AuditEvent.objects.filter(sample=s).count() == 0

    def test_el_modelo_devuelve_una_clase_que_no_existe(self, analyst_user, media, monkeypatch):
        monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop',
                            lambda *a, **kw: {'predicted_class': '', 'confidence_score': 0.9})
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0115', media)
        with pytest.raises(ClaseRequeridaError):
            add_object(s, CAJA, analyst_user)
        assert k.chromosomes.count() == 0

    def test_sin_silueta_se_crea_igual(self, analyst_user, media, ml, monkeypatch):
        monkeypatch.setattr('apps.samples.services.pipeline_client.contours', _caida)
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0116', media)
        c = add_object(s, CAJA, analyst_user)
        assert c.contour is None
        ev = AuditEvent.objects.get(sample=s, event_type=AuditEventType.ADD_OBJECT)
        assert ev.payload['con_silueta'] is False

    @pytest.mark.parametrize('caja', [
        {}, {'x': 1, 'y': 1, 'w': 5}, {'x': 'a', 'y': 1, 'w': 5, 'h': 5},
        {'x': 0, 'y': 0, 'w': 0, 'h': 5}, {'x': -1, 'y': 0, 'w': 5, 'h': 5},
        {'x': 190, 'y': 0, 'w': 20, 'h': 5},    # se sale por la derecha (ancho 200)
        {'x': 0, 'y': 140, 'w': 5, 'h': 20},    # se sale por abajo (alto 150)
    ])
    def test_caja_invalida(self, analyst_user, media, ml, caja):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0117', media)
        with pytest.raises(ValueError):
            add_object(s, caja, analyst_user)
        assert k.chromosomes.count() == 0
        assert ml['classify'] == []

    def test_formato_desconocido_no_bloquea(self, analyst_user, media, ml):
        """Si no se sabe el tamaño de la imagen, no se rechaza la caja."""
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0118', media)
        (media / 'CHN-2026-10-23-0118' / '0.img').write_bytes(b'XX' + b'\x00' * 40)
        assert add_object(s, {'x': 5000, 'y': 0, 'w': 5, 'h': 5}, analyst_user).predicted_class == '21'

    def test_clase_invalida(self, analyst_user, media, ml):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0119', media)
        with pytest.raises(InvalidClassError):
            add_object(s, CAJA, analyst_user, clase='25')

    def test_sin_metafase(self, analyst_user, media, ml):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0120', media, imagen=False)
        with pytest.raises(SinMetafaseError):
            add_object(s, CAJA, analyst_user)

    def test_sin_cariotipo(self, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-10-23-0121', patient_ref='ANON',
                                  analyst=analyst_user, status='READY')
        with pytest.raises(ValueError):
            add_object(s, CAJA, analyst_user)

    def test_caso_validado(self, analyst_user, media, ml):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0122', media, status='ANALYST_VALIDATED')
        with pytest.raises(CaseLockedError):
            add_object(s, CAJA, analyst_user)
        assert ml['classify'] == []


# ============================================================================
# Vistas
# ============================================================================
@pytest.fixture
def otro_analista(django_user_model):
    return django_user_model.objects.create_user(username='otra_analista_objetos', password='x')


def _reject(s, c):
    return f'/api/clinic/samples/{s.id}/chromosomes/{c.id}/reject/'


def _objects(s):
    return f'/api/clinic/samples/{s.id}/karyotype/objects/'


class TestVistaDescartar:
    def test_descarta_y_sale_del_cariotipo(self, analyst_client, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0131')
        c = _crom(k)
        _crom(k, order=1)
        resp = analyst_client.post(_reject(s, c), {'motivo': 'suciedad'}, format='json')
        assert resp.status_code == 200
        assert resp.data['is_active'] is False
        cariotipo = analyst_client.get(f'/api/clinic/samples/{s.id}/karyotype/').data
        assert [x['id'] for x in cariotipo['chromosomes']] != [] and \
            str(c.id) not in [x['id'] for x in cariotipo['chromosomes']]
        assert cariotipo['summary']['total'] == 1

    def test_motivo_invalido_400(self, analyst_client, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0132')
        resp = analyst_client.post(_reject(s, _crom(k)), {'motivo': 'x'}, format='json')
        assert resp.status_code == 400
        assert resp.data['code'] == 'VALIDATION_ERROR'

    def test_ya_descartado_409(self, analyst_client, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0133')
        resp = analyst_client.post(_reject(s, _crom(k, activo=False)), {'motivo': 'otro'}, format='json')
        assert resp.status_code == 409
        assert resp.data['code'] == 'OBJECT_INACTIVE'

    def test_caso_validado_409(self, analyst_client, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0134', status='ANALYST_VALIDATED')
        resp = analyst_client.post(_reject(s, _crom(k)), {'motivo': 'otro'}, format='json')
        assert resp.status_code == 409
        assert resp.data['code'] == 'CASE_LOCKED'

    def test_analista_ajeno_403(self, analyst_client, otro_analista):
        s, k = _caso(otro_analista, 'CHN-2026-10-23-0135')
        c = _crom(k)
        resp = analyst_client.post(_reject(s, c), {'motivo': 'otro'}, format='json')
        assert resp.status_code == 403
        assert resp.data['code'] == 'NOT_OWNER'
        c.refresh_from_db()
        assert c.is_active is True

    def test_cromosoma_de_otro_caso_404(self, analyst_client, analyst_user):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0136')
        _, k2 = _caso(analyst_user, 'CHN-2026-10-23-0137')
        resp = analyst_client.post(_reject(s, _crom(k2)), {'motivo': 'otro'}, format='json')
        assert resp.status_code == 404


class TestVistaAnadir:
    def test_crea_201_y_aparece_en_el_cariotipo(self, analyst_client, analyst_user, media, ml):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0141', media)
        resp = analyst_client.post(_objects(s), {'bbox': CAJA}, format='json')
        assert resp.status_code == 201
        assert resp.data['predicted_class'] == '21'
        assert resp.data['contour'] == CONTORNO
        cariotipo = analyst_client.get(f'/api/clinic/samples/{s.id}/karyotype/').data
        assert [x['id'] for x in cariotipo['chromosomes']] == [resp.data['id']]

    def test_con_clase_del_analista(self, analyst_client, analyst_user, media, ml):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0142', media)
        resp = analyst_client.post(_objects(s), {'bbox': CAJA, 'clase': 'Y'}, format='json')
        assert resp.status_code == 201
        assert resp.data['predicted_class'] == 'Y'
        assert resp.data['resolution_status'] == 'RESOLVED'

    def test_sin_ia_503_class_required(self, analyst_client, analyst_user, media, monkeypatch):
        monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop', _caida)
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0143', media)
        resp = analyst_client.post(_objects(s), {'bbox': CAJA}, format='json')
        assert resp.status_code == 503
        assert resp.data['code'] == 'CLASS_REQUIRED'
        assert k.chromosomes.count() == 0

    @pytest.mark.parametrize('cuerpo, codigo', [
        ({'bbox': {'x': 1}}, 'VALIDATION_ERROR'),
        ({}, 'VALIDATION_ERROR'),
        ({'bbox': CAJA, 'clase': 'Z'}, 'INVALID_CLASS'),
    ])
    def test_400(self, analyst_client, analyst_user, media, ml, cuerpo, codigo):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0144', media)
        resp = analyst_client.post(_objects(s), cuerpo, format='json')
        assert resp.status_code == 400
        assert resp.data['code'] == codigo

    def test_sin_cariotipo_404(self, analyst_client, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-10-23-0145', patient_ref='ANON',
                                  analyst=analyst_user, status='READY')
        resp = analyst_client.post(_objects(s), {'bbox': CAJA}, format='json')
        assert resp.status_code == 404
        assert resp.data['code'] == 'NO_KARYOTYPE'

    def test_sin_metafase_404(self, analyst_client, analyst_user, media, ml):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0146', media, imagen=False)
        resp = analyst_client.post(_objects(s), {'bbox': CAJA}, format='json')
        assert resp.status_code == 404
        assert resp.data['code'] == 'NO_METAPHASE_IMAGE'

    def test_caso_validado_409(self, analyst_client, analyst_user, media, ml):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0147', media, status='VALIDATED')
        resp = analyst_client.post(_objects(s), {'bbox': CAJA}, format='json')
        assert resp.status_code == 409

    def test_analista_ajeno_403(self, analyst_client, otro_analista, media, ml):
        s, k = _caso(otro_analista, 'CHN-2026-10-23-0148', media)
        resp = analyst_client.post(_objects(s), {'bbox': CAJA}, format='json')
        assert resp.status_code == 403
        assert k.chromosomes.count() == 0
        assert ml['classify'] == []

    def test_modo_degradado_queda_en_el_evento(self, analyst_client, analyst_user, media, ml):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0149', media)
        analyst_client.post(_objects(s), {'bbox': CAJA, 'clase': '3'}, format='json',
                            HTTP_X_BIOMED_MODE='degradado')
        assert AuditEvent.objects.get(sample=s, event_type=AuditEventType.ADD_OBJECT).mode == 'degradado'
