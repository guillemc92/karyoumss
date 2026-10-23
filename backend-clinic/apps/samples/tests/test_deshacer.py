"""Deshacer la última edición (DD-KARYO-007 D6, T6).

La auditoría es solo de inserción (RN-05, ADR-0022): deshacer no puede borrar
el evento anterior. Emite UNDO_EDIT y restaura el estado que el evento original
guardó. Se fija, para cada edición de la segmentación:

- el estado vuelve a ser EXACTAMENTE el de antes (caja, silueta, clase,
  confianza, resolución, activo);
- el evento original sigue en la cadena y la cadena de hashes sigue íntegra;
- solo un nivel, solo lo propio, nunca en un caso validado;
- un corte o una unión de antes de D6 (sin estado previo) no se deshace a ciegas.
"""
from decimal import Decimal

import pytest

from apps.samples.models import (
    AuditEvent, AuditEventType, Chromosome, Karyotype, Sample, SampleImage, SampleImageSource,
)
from apps.samples.services import (
    CaseLockedError, DeshacerAjenoError, DeshacerNoDisponibleError, NadaQueDeshacerError,
    add_object, emit_audit_event, join_chromosomes, recrop_chromosome, reject_object,
    split_chromosome, ultima_edicion_deshacible, undo_last_edit, verify_audit_chain,
)

pytestmark = pytest.mark.django_db

SILUETA = [[10, 20], [40, 20], [40, 110], [10, 110]]
TROZOS = [
    {'contour': [[10, 20], [40, 20], [40, 60]], 'bbox': {'x': 10, 'y': 20, 'w': 30, 'h': 40}, 'area': 900},
    {'contour': [[10, 70], [40, 70], [40, 110]], 'bbox': {'x': 10, 'y': 70, 'w': 30, 'h': 40}, 'area': 800},
]


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def ml(monkeypatch):
    monkeypatch.setattr('apps.samples.services.pipeline_client.split', lambda *a, **kw: TROZOS)
    monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop',
                        lambda *a, **kw: {'predicted_class': '5', 'confidence_score': 0.6})
    monkeypatch.setattr('apps.samples.services.pipeline_client.contours',
                        lambda img, bboxes, filename='': [SILUETA for _ in bboxes])
    monkeypatch.setattr('apps.samples.services.pipeline_client.join',
                        lambda contornos: {'contour': SILUETA, 'bbox': {'x': 10, 'y': 20, 'w': 30, 'h': 90}})


def _caso(dueno, chn, media, status='READY'):
    s = Sample.objects.create(chn_code=chn, patient_ref='ANON', analyst=dueno, status=status)
    k = Karyotype.objects.create(sample=s, model_version='test-v0')
    (media / chn).mkdir(parents=True, exist_ok=True)
    (media / chn / '0.img').write_bytes(b'BM' + b'\x00' * 100)
    SampleImage.objects.create(sample=s, image_path=f'{chn}/0.img', order=0, source=SampleImageSource.UPLOAD)
    return s, k


def _crom(k, cls='1', order=0, contour=SILUETA, bbox=None):
    return Chromosome.objects.create(
        karyotype=k, predicted_class=cls, position_index=0, order=order,
        confidence_score=Decimal('0.950'), resolution_status='RESOLVED', xai_viewed=True,
        bbox=bbox or {'x': 10, 'y': 20, 'w': 30, 'h': 90}, contour=contour,
    )


CAMPOS = ('bbox', 'contour', 'predicted_class', 'confidence_score', 'resolution_status',
          'xai_viewed', 'is_active')


def _foto(c):
    c.refresh_from_db()
    return {f: getattr(c, f) for f in CAMPOS}


def _activos(k):
    return sorted(str(c.id) for c in k.chromosomes.filter(is_active=True))


class TestDeshacerCadaEdicion:
    def test_separar(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0301', media)
        c = _crom(k)
        antes, activos = _foto(c), _activos(k)
        _, nuevo = split_chromosome(s, c, [[0, 65], [50, 65]], analyst_user)
        undo_last_edit(s, analyst_user)
        assert _foto(c) == antes
        assert _activos(k) == activos
        nuevo.refresh_from_db()
        assert nuevo.is_active is False      # el trozo se queda en la base (RN-05)

    def test_unir(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0302', media)
        a = _crom(k, contour=TROZOS[0]['contour'], bbox=TROZOS[0]['bbox'])
        b = _crom(k, order=1, contour=TROZOS[1]['contour'], bbox=TROZOS[1]['bbox'])
        antes_a, antes_b = _foto(a), _foto(b)
        join_chromosomes(s, a, b, analyst_user)
        undo_last_edit(s, analyst_user)
        assert _foto(a) == antes_a and _foto(b) == antes_b

    def test_recortar(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0303', media)
        c = _crom(k)
        antes = _foto(c)
        recrop_chromosome(s, c, {'x': 12, 'y': 22, 'w': 20, 'h': 60}, analyst_user)
        assert _foto(c) != antes
        undo_last_edit(s, analyst_user)
        assert _foto(c) == antes

    def test_descartar(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0304', media)
        c = _crom(k)
        reject_object(s, c, 'nucleo', analyst_user)
        undo_last_edit(s, analyst_user)
        assert _foto(c)['is_active'] is True

    def test_anadir(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0305', media)
        nuevo = add_object(s, {'x': 50, 'y': 50, 'w': 20, 'h': 20}, analyst_user)
        undo_last_edit(s, analyst_user)
        assert _foto(nuevo)['is_active'] is False
        assert _activos(k) == []


class TestReglas:
    def test_el_original_sigue_en_la_cadena_y_la_cadena_es_integra(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0311', media)
        reject_object(s, _crom(k), 'suciedad', analyst_user)
        original = AuditEvent.objects.get(sample=s, event_type='REJECT_OBJECT')
        ev = undo_last_edit(s, analyst_user)
        assert ev.event_type == AuditEventType.UNDO_EDIT
        assert ev.payload['deshace'] == str(original.id)
        assert ev.payload['tipo'] == 'REJECT_OBJECT'
        assert AuditEvent.objects.filter(id=original.id).exists()
        assert verify_audit_chain(s) is True

    def test_solo_un_nivel(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0312', media)
        a, b = _crom(k), _crom(k, order=1)
        reject_object(s, a, 'otro', analyst_user)
        reject_object(s, b, 'otro', analyst_user)
        undo_last_edit(s, analyst_user)          # deshace el de b
        with pytest.raises(NadaQueDeshacerError):
            undo_last_edit(s, analyst_user)      # no sigue con el de a
        assert _foto(a)['is_active'] is False

    def test_sin_ediciones(self, analyst_user, media):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0313', media)
        with pytest.raises(NadaQueDeshacerError):
            undo_last_edit(s, analyst_user)
        assert ultima_edicion_deshacible(s, analyst_user) is None

    def test_las_decisiones_clinicas_no_cuentan_como_edicion(self, analyst_user, media, ml):
        """Después de la edición, el analista consulta XAI: deshacer sigue
        apuntando a la edición, no a la consulta."""
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0314', media)
        c = _crom(k)
        reject_object(s, c, 'otro', analyst_user)
        emit_audit_event(s, analyst_user, AuditEventType.XAI_VIEWED, chromosome=c)
        assert ultima_edicion_deshacible(s, analyst_user)['tipo'] == 'REJECT_OBJECT'
        undo_last_edit(s, analyst_user)
        assert _foto(c)['is_active'] is True

    def test_no_se_deshace_lo_de_otro(self, analyst_user, supervisor_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0315', media)
        c = _crom(k)
        reject_object(s, c, 'otro', supervisor_user)
        assert ultima_edicion_deshacible(s, analyst_user)['propia'] is False
        with pytest.raises(DeshacerAjenoError):
            undo_last_edit(s, analyst_user)
        assert _foto(c)['is_active'] is False

    def test_caso_validado(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0316', media)
        reject_object(s, _crom(k), 'otro', analyst_user)
        s.status = 'ANALYST_VALIDATED'
        s.save(update_fields=['status'])
        with pytest.raises(CaseLockedError):
            undo_last_edit(s, analyst_user)

    @pytest.mark.parametrize('tipo, payload', [
        (AuditEventType.SPLIT, {'origin': 'x', 'created': ['y']}),
        (AuditEventType.JOIN, {'kept': 'x', 'absorbed': 'y'}),
    ])
    def test_un_evento_anterior_a_d6_no_se_deshace_a_ciegas(self, analyst_user, media, tipo, payload):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0317', media)
        emit_audit_event(s, analyst_user, tipo, chromosome=_crom(k), payload=payload)
        with pytest.raises(DeshacerNoDisponibleError):
            undo_last_edit(s, analyst_user)
        assert not AuditEvent.objects.filter(sample=s, event_type='UNDO_EDIT').exists()

    def test_un_cromosoma_que_falta(self, analyst_user, media):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0318', media)
        emit_audit_event(s, analyst_user, AuditEventType.SPLIT, chromosome=_crom(k),
                         payload={'origin': 'no-es-uuid', 'created': [], 'previo': {'bbox': {}}})
        with pytest.raises(DeshacerNoDisponibleError):
            undo_last_edit(s, analyst_user)

    def test_un_recorte_antiguo_vuelve_a_revision(self, analyst_user, media):
        """Los RECROP de antes de D6 no guardaron silueta ni resolución."""
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0319', media)
        c = _crom(k)
        emit_audit_event(s, analyst_user, AuditEventType.RECROP, chromosome=c, payload={
            'bbox_previo': {'x': 1, 'y': 2, 'w': 3, 'h': 4}, 'clase_previa': '9', 'confianza_previa': None})
        undo_last_edit(s, analyst_user)
        f = _foto(c)
        assert f['bbox'] == {'x': 1, 'y': 2, 'w': 3, 'h': 4} and f['predicted_class'] == '9'
        assert f['confidence_score'] is None and f['contour'] is None
        assert f['resolution_status'] == 'PENDING'


def _url(s):
    return f'/api/clinic/samples/{s.id}/karyotype/undo/'


@pytest.fixture
def otro_analista(django_user_model):
    return django_user_model.objects.create_user(username='otra_analista_deshacer', password='x')


class TestVista:
    def test_get_dice_que_se_desharia_y_post_lo_deshace(self, analyst_client, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0321', media)
        c = _crom(k)
        assert analyst_client.get(_url(s)).data == {'ultima': None}
        reject_object(s, c, 'otro', analyst_user)
        ultima = analyst_client.get(_url(s)).data['ultima']
        assert ultima['tipo'] == 'REJECT_OBJECT' and ultima['propia'] is True
        r = analyst_client.post(_url(s))
        assert r.status_code == 200
        assert r.data['tipo'] == 'REJECT_OBJECT'
        assert _foto(c)['is_active'] is True
        assert analyst_client.get(_url(s)).data == {'ultima': None}

    @pytest.mark.parametrize('preparar, codigo', [
        ('nada', 'NOTHING_TO_UNDO'), ('ajeno', 'UNDO_NOT_OWN'),
        ('antiguo', 'UNDO_UNAVAILABLE'), ('validado', 'CASE_LOCKED'),
    ])
    def test_409(self, analyst_client, analyst_user, supervisor_user, media, ml, preparar, codigo):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0322', media)
        c = _crom(k)
        if preparar == 'ajeno':
            reject_object(s, c, 'otro', supervisor_user)
        elif preparar == 'antiguo':
            emit_audit_event(s, analyst_user, AuditEventType.JOIN, chromosome=c, payload={})
        elif preparar == 'validado':
            reject_object(s, c, 'otro', analyst_user)
            s.status = 'VALIDATED'
            s.save(update_fields=['status'])
        r = analyst_client.post(_url(s))
        assert r.status_code == 409
        assert r.data['code'] == codigo

    def test_analista_ajeno_403(self, analyst_client, otro_analista, media):
        s, _ = _caso(otro_analista, 'CHN-2026-10-23-0323', media)
        assert analyst_client.get(_url(s)).status_code == 403
        assert analyst_client.post(_url(s)).status_code == 403

    def test_sin_cariotipo_404(self, analyst_client, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-10-23-0324', patient_ref='ANON',
                                  analyst=analyst_user, status='READY')
        assert analyst_client.post(_url(s)).data['code'] == 'NO_KARYOTYPE'
