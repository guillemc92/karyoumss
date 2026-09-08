"""Tests del servicio de narrativa asistida por LLM (ADR-0024 D3).

Cubre el cableado: persistir el borrador, dejar traza de auditoría, y —lo más
importante— **degradar sin bloquear**. Si el LLM falla, el caso debe poder
seguir su curso hacia el informe (RN-07).

El cliente LLM se mockea: estos tests no requieren Ollama corriendo.
"""
from decimal import Decimal

import pytest

from apps.samples import llm_client as llm_mod
from apps.samples.llm_client import LlmServiceError
from apps.samples.models import AuditEvent, Chromosome, Karyotype, Sample
from apps.samples.services import generate_narrative

pytestmark = pytest.mark.django_db

NARRATIVA = (
    'El análisis citogenético muestra un complemento cromosómico femenino normal, '
    'sin alteraciones numéricas ni estructurales detectables. Se recomienda '
    'correlación clínica.'
)


def _mock_llm(monkeypatch, *, text=NARRATIVA, raises=None, tokens=310, latency=95000):
    def fake(iscn, sample_type, chn_code, counts):
        if raises is not None:
            raise raises
        return {
            'text': text, 'model': 'llama3.2:3b', 'tokens': tokens,
            'latency_ms': latency, 'intentos': 1,
            'structured': {
                'hallazgo': 'Hallazgo de prueba para el caso analizado.',
                'interpretacion': text,
                'es_normal': True, 'anomalias_citadas': [], 'nivel_confianza': 'alta',
            },
        }
    monkeypatch.setattr(llm_mod.llm_client, 'generate_narrative', fake)


def _case(analyst, n_chromo=6):
    s = Sample.objects.create(
        chn_code=f'CHN-NARR-{Sample.objects.count():04d}',
        analyst=analyst,
        status='SIGNED',
        sample_type='sangre',
    )
    if n_chromo:
        k = Karyotype.objects.create(sample=s)
        for i in range(n_chromo):
            Chromosome.objects.create(
                karyotype=k, predicted_class=str((i % 3) + 1), position_index=i,
                confidence_score=Decimal('0.950'), order=i,
            )
    return s


class TestGeneracionYPersistencia:
    def test_persiste_el_borrador_y_su_procedencia(self, monkeypatch, analyst_user, supervisor_user):
        _mock_llm(monkeypatch)
        s = _case(analyst_user)
        out = generate_narrative(s, supervisor_user, '46,XX')

        assert out['generated'] is True
        s.refresh_from_db()
        assert s.narrative_draft == NARRATIVA
        assert s.narrative_model == 'llama3.2:3b'
        assert s.narrative_generated_at is not None

    def test_emite_evento_auditable_con_el_iscn_de_entrada(self, monkeypatch, analyst_user, supervisor_user):
        """Para poder auditar después una narrativa incorrecta hace falta saber
        qué modelo la escribió y sobre qué dato."""
        _mock_llm(monkeypatch)
        s = _case(analyst_user)
        generate_narrative(s, supervisor_user, '47,XY,+21')

        ev = AuditEvent.objects.get(sample=s, event_type='NARRATIVE_GENERATED')
        assert ev.actor_id == supervisor_user.id
        assert ev.payload['model'] == 'llama3.2:3b'
        assert ev.payload['iscn_input'] == '47,XY,+21'
        assert ev.payload['tokens'] == 310
        assert ev.payload['is_draft'] is True

    def test_el_evento_entra_en_la_cadena_de_hash(self, monkeypatch, analyst_user, supervisor_user):
        _mock_llm(monkeypatch)
        s = _case(analyst_user)
        generate_narrative(s, supervisor_user, '46,XX')
        ev = AuditEvent.objects.get(sample=s, event_type='NARRATIVE_GENERATED')
        assert ev.current_hash and len(ev.current_hash) == 64

    def test_pasa_el_conteo_de_cromosomas_activos(self, monkeypatch, analyst_user, supervisor_user):
        capturado = {}

        def fake(iscn, sample_type, chn_code, counts):
            capturado.update(counts=counts, iscn=iscn, sample_type=sample_type, chn=chn_code)
            return {'text': NARRATIVA, 'model': 'm', 'tokens': 1, 'latency_ms': 1}

        monkeypatch.setattr(llm_mod.llm_client, 'generate_narrative', fake)
        s = _case(analyst_user, n_chromo=6)
        generate_narrative(s, supervisor_user, '46,XX')

        assert sum(capturado['counts'].values()) == 6
        assert capturado['sample_type'] == 'sangre'
        assert capturado['chn'] == s.chn_code

    def test_regenerar_sobrescribe_el_borrador_y_deja_dos_eventos(self, monkeypatch, analyst_user, supervisor_user):
        """El borrador se reemplaza, pero la traza es append-only (RN-05)."""
        _mock_llm(monkeypatch, text=NARRATIVA)
        s = _case(analyst_user)
        generate_narrative(s, supervisor_user, '46,XX')
        _mock_llm(monkeypatch, text=NARRATIVA.replace('femenino', 'masculino'))
        generate_narrative(s, supervisor_user, '46,XY')

        s.refresh_from_db()
        assert 'masculino' in s.narrative_draft
        assert AuditEvent.objects.filter(sample=s, event_type='NARRATIVE_GENERATED').count() == 2


class TestDegradacionNoBloqueante:
    """RN-07 — la narrativa nunca puede impedir que el informe se emita."""

    def test_servicio_caido_no_lanza(self, monkeypatch, analyst_user, supervisor_user):
        _mock_llm(monkeypatch, raises=LlmServiceError('circuit_open'))
        s = _case(analyst_user)
        out = generate_narrative(s, supervisor_user, '46,XX')

        assert out['generated'] is False
        assert out['reason'] == 'circuit_open'
        s.refresh_from_db()
        assert s.narrative_draft == ''

    def test_alucinacion_descarta_el_borrador(self, monkeypatch, analyst_user, supervisor_user):
        """Si la validación rechaza el texto, no se persiste nada: mejor sin
        narrativa que con una que afirme una anomalía inexistente."""
        _mock_llm(monkeypatch, raises=LlmServiceError('alucinación: "+21" no está en el ISCN'))
        s = _case(analyst_user)
        out = generate_narrative(s, supervisor_user, '46,XX')

        assert out['generated'] is False
        s.refresh_from_db()
        assert s.narrative_draft == ''

    def test_fallo_no_emite_evento_de_auditoria(self, monkeypatch, analyst_user, supervisor_user):
        """No hubo narrativa: no hay nada que auditar."""
        _mock_llm(monkeypatch, raises=LlmServiceError('timeout'))
        s = _case(analyst_user)
        generate_narrative(s, supervisor_user, '46,XX')
        assert not AuditEvent.objects.filter(sample=s, event_type='NARRATIVE_GENERATED').exists()

    def test_sin_iscn_no_llama_al_modelo(self, monkeypatch, analyst_user, supervisor_user):
        """El LLM redacta SOBRE un ISCN ya calculado (ADR-0024 D1). Sin ese dato
        no hay nada que narrar — y pedirlo invitaría al modelo a inventarlo."""
        def explota(**kwargs):
            raise AssertionError('no debió llamarse al LLM sin ISCN')
        monkeypatch.setattr(llm_mod.llm_client, 'generate_narrative', explota)

        s = _case(analyst_user)
        out = generate_narrative(s, supervisor_user, '')
        assert out['generated'] is False
        assert out['reason'] == 'sin_iscn'

    def test_caso_sin_cariotipo_no_revienta(self, monkeypatch, analyst_user, supervisor_user):
        _mock_llm(monkeypatch)
        s = _case(analyst_user, n_chromo=0)
        assert generate_narrative(s, supervisor_user, '46,XX')['generated'] is True


class TestModoDegradado:
    def test_propaga_el_modo_al_evento(self, monkeypatch, analyst_user, supervisor_user):
        """FSD-UC-007 §7: las acciones en modo manual quedan marcadas."""
        _mock_llm(monkeypatch)
        s = _case(analyst_user)
        generate_narrative(s, supervisor_user, '46,XX', mode='degradado')
        ev = AuditEvent.objects.get(sample=s, event_type='NARRATIVE_GENERATED')
        assert ev.mode == 'degradado'


class TestEndpointNarrativa:
    """POST /samples/{id}/narrative/ (ADR-0024) — el extra "exponerlo como
    endpoint" de la consigna del módulo de IA."""

    def _url(self, sample):
        return f'/api/clinic/samples/{sample.id}/narrative/'

    def test_devuelve_el_borrador(self, monkeypatch, supervisor_client, supervisor_user):
        _mock_llm(monkeypatch)
        s = _case(supervisor_user)
        r = supervisor_client.post(self._url(s), {'iscn': '46,XX'}, format='json')

        assert r.status_code == 200
        assert r.data['generated'] is True
        assert r.data['narrative_draft'] == NARRATIVA
        assert r.data['model'] == 'llama3.2:3b'
        assert r.data['iscn_input'] == '46,XX'

    def test_marca_la_salida_como_borrador(self, monkeypatch, supervisor_client, supervisor_user):
        """ADR-0024 D3: el consumidor tiene que saber que requiere revisión."""
        _mock_llm(monkeypatch)
        s = _case(supervisor_user)
        r = supervisor_client.post(self._url(s), {'iscn': '46,XX'}, format='json')
        assert r.data['is_draft'] is True

    def test_usa_el_iscn_persistido_del_caso(self, monkeypatch, supervisor_client, supervisor_user):
        """Desde S3 (ADR-0025) el ISCN es un dato del caso, no algo que la vista
        derive: el LLM narra lo que la función determinística ya calculó."""
        capturado = {}

        def fake(iscn, sample_type, chn_code, counts):
            capturado['iscn'] = iscn
            return {'text': NARRATIVA, 'model': 'm', 'tokens': 1, 'latency_ms': 1}

        monkeypatch.setattr(llm_mod.llm_client, 'generate_narrative', fake)
        s = _case(supervisor_user, n_chromo=6)
        s.iscn_nomenclature = '47,XY,+21'
        s.save(update_fields=['iscn_nomenclature'])
        r = supervisor_client.post(self._url(s), {}, format='json')

        assert r.status_code == 200
        assert capturado['iscn'] == '47,XY,+21'

    def test_sin_iscn_generado_no_narra(self, monkeypatch, supervisor_client, supervisor_user):
        """Sin S3 ejecutado no hay dato clínico que narrar — y pedirle al LLM que
        lo invente es justo lo que ADR-0024 D1 prohíbe."""
        def explota(**kwargs):
            raise AssertionError('no debió llamarse al LLM sin ISCN')
        monkeypatch.setattr(llm_mod.llm_client, 'generate_narrative', explota)

        s = _case(supervisor_user, n_chromo=6)     # sin iscn_nomenclature
        r = supervisor_client.post(self._url(s), {}, format='json')

        assert r.status_code == 200
        assert r.data['generated'] is False
        assert r.data['reason'] == 'sin_iscn'

    def test_el_llm_caido_devuelve_200_no_error(self, monkeypatch, supervisor_client, supervisor_user):
        """RN-07: el endpoint no puede propagar el fallo del LLM como error HTTP —
        el informe se emite igual, solo sin narrativa."""
        _mock_llm(monkeypatch, raises=LlmServiceError('circuit_open'))
        s = _case(supervisor_user)
        r = supervisor_client.post(self._url(s), {'iscn': '46,XX'}, format='json')

        assert r.status_code == 200
        assert r.data['generated'] is False
        assert r.data['reason'] == 'circuit_open'
        assert r.data['narrative_draft'] == ''

    def test_el_analista_no_puede_generarla(self, monkeypatch, analyst_client, analyst_user):
        """Requiere case.sign: es parte del cierre del informe (RN-06)."""
        _mock_llm(monkeypatch)
        s = _case(analyst_user)
        r = analyst_client.post(self._url(s), {'iscn': '46,XX'}, format='json')
        assert r.status_code == 403

    def test_anonimo_rechazado(self, monkeypatch, supervisor_user):
        from rest_framework.test import APIClient
        _mock_llm(monkeypatch)
        s = _case(supervisor_user)
        r = APIClient().post(self._url(s), {'iscn': '46,XX'}, format='json')
        # Medido: el endpoint devuelve 401 de forma determinista. El
        # `in (401, 403)` que habia aqui aceptaba un codigo que el sistema
        # nunca produce, asi que habria seguido verde si la autenticacion
        # pasara a 403 — que significa otra cosa (credencial valida sin
        # permiso, no ausencia de credencial).
        assert r.status_code == 401

    def test_devuelve_el_objeto_estructurado(self, monkeypatch, supervisor_client, supervisor_user):
        """ADR-0024 D4: el consumidor recibe campos tipados, no solo prosa."""
        _mock_llm(monkeypatch)
        s = _case(supervisor_user)
        s.iscn_nomenclature = '46,XX'
        s.save(update_fields=['iscn_nomenclature'])
        r = supervisor_client.post(self._url(s), {}, format='json')

        assert r.status_code == 200
        est = r.data['structured']
        assert est['es_normal'] is True
        assert est['anomalias_citadas'] == []
        assert est['nivel_confianza'] == 'alta'

    def test_sin_narrativa_el_estructurado_es_nulo(self, monkeypatch, supervisor_client, supervisor_user):
        _mock_llm(monkeypatch, raises=LlmServiceError('circuit_open'))
        s = _case(supervisor_user)
        s.iscn_nomenclature = '46,XX'
        s.save(update_fields=['iscn_nomenclature'])
        r = supervisor_client.post(self._url(s), {}, format='json')

        assert r.status_code == 200
        assert r.data['structured'] is None
