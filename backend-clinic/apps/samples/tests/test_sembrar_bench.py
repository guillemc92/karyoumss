"""DD-E3-001 T3 — el seed fijo y el token del banco E3."""
import json
import os
import random

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from apps.samples.management.commands.sembrar_bench import (
    EVENTOS_MAX, EVENTOS_MIN, USUARIO_BENCH, eventos_del_caso,
)
from apps.samples.models import AuditEvent, Sample
from apps.samples.services import verify_audit_chain

pytestmark = pytest.mark.django_db


def _sembrar(tmp_path, semilla=42, muestras=4):
    call_command('sembrar_bench', semilla=semilla, muestras=muestras, salida=tmp_path, stdout=open(os.devnull, 'w'))
    return json.loads((tmp_path / 'ids.json').read_text(encoding='utf-8'))


def _huella():
    """Lo que el seed promete repetir: ids, y tipo y payload de cada evento por caso."""
    return {
        str(s.id): [(e.event_type, e.payload) for e in s.audit_events.order_by('created_at', 'id')]
        for s in Sample.objects.order_by('chn_code')
    }


def _vaciar():
    from django.contrib.auth import get_user_model
    AuditEvent.objects.all().delete()  # queryset.delete() no pasa por save(): es el reset de la base
    Sample.objects.all().delete()
    get_user_model().objects.filter(username=USUARIO_BENCH).delete()


def test_la_misma_semilla_da_los_mismos_datos(tmp_path):
    ids1 = _sembrar(tmp_path)
    huella1 = _huella()
    _vaciar()
    ids2 = _sembrar(tmp_path)
    assert ids1 == ids2
    assert _huella() == huella1


def test_otra_semilla_da_otros_ids(tmp_path):
    ids1 = _sembrar(tmp_path, semilla=42)
    _vaciar()
    assert _sembrar(tmp_path, semilla=7) != ids1


def test_ids_existen_y_cada_caso_tiene_46_cromosomas_y_cadena_valida(tmp_path):
    ids = _sembrar(tmp_path, muestras=3)
    assert len(ids) == 3
    for sid in ids:
        s = Sample.objects.get(pk=sid)
        assert s.karyotype.chromosomes.count() == 46
        assert EVENTOS_MIN <= s.audit_events.count() <= EVENTOS_MAX
        assert verify_audit_chain(s) is True
        assert s.analyst.username == USUARIO_BENCH


def test_no_siembra_sobre_una_base_ya_sembrada(tmp_path):
    _sembrar(tmp_path, muestras=1)
    with pytest.raises(CommandError, match='down -v'):
        _sembrar(tmp_path, muestras=1)


def test_la_distribucion_de_eventos_se_parece_a_la_real():
    """Base de demo medida el 2026-11-02: media 13,6, máximo 70."""
    rng = random.Random(42)
    n = [eventos_del_caso(rng) for _ in range(1000)]
    assert min(n) >= EVENTOS_MIN and max(n) <= EVENTOS_MAX
    assert 12 <= sum(n) / len(n) <= 16


def test_el_token_abre_la_bitacora_de_un_caso_sembrado(tmp_path):
    ids = _sembrar(tmp_path, muestras=1)
    call_command('token_bench', salida=tmp_path / 'token.txt', stdout=open(os.devnull, 'w'))
    token = (tmp_path / 'token.txt').read_text(encoding='utf-8')
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    resp = cliente.get(f'/api/clinic/samples/{ids[0]}/audit/')
    assert resp.status_code == 200
    assert len(resp.json()) == Sample.objects.get(pk=ids[0]).audit_events.count()
    assert cliente.get(f'/api/clinic/samples/{ids[0]}/').status_code == 200
