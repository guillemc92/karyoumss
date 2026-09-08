"""Ejercicio 2 del LabX — tests del endpoint generados por un agente, AUDITADOS.

    generados por  llama3.2:3b (local, sin red)
    coste          3.264 tokens de entrada, 519 de salida, 1.012 s
    devueltos      6 tests
    sobrevivieron  4

La copia intacta esta en `docs/M7_UNIT_AGENTE/salida_agente/endpoint_crudo.py`.
El detalle test por test esta en `docs/M7_UNIT_AGENTE/README.md`.

## Por que aqui sobrevivieron cuatro y en el ejercicio 1 solo uno

Porque el prompt fue mejor: los cinco casos se comprobaron **ausentes** del
fichero a mano antes de pedirlos. La diferencia no la hizo el modelo — hizo lo
mismo de siempre— sino quien escribio el encargo.

Aun asi, ninguno de los seis corria tal cual: cinco por una fixture que el
modelo dio por heredada y no lo es, y uno por una CHECK constraint de la base
que no podia conocer.
"""
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.samples.models import Chromosome, Karyotype, Sample, SampleStatus

pytestmark = [pytest.mark.django_db, pytest.mark.auditado]


@pytest.fixture
def caso(analyst_user):
    """El agente uso una fixture `caso` que NO existe en el conftest: vive en
    `test_contrato_karyotype.py`, y las fixtures no se heredan entre modulos.

    Es el fallo mas caro de los suyos —cinco de seis tests murieron por esto— y
    el mas invisible en una revision por encima: el codigo se lee perfecto.
    """
    muestra = Sample.objects.create(chn_code='CHN-2026-09-07-3000',
                                    analyst=analyst_user,
                                    status=SampleStatus.READY,
                                    sample_type='sangre')
    k = Karyotype.objects.create(sample=muestra, model_version='opencv-v0+efnb3-v3')
    for i in range(3):
        Chromosome.objects.create(karyotype=k, predicted_class=str(i + 1),
                                  position_index=0, order=i,
                                  confidence_score=Decimal('0.950'))
    return muestra


def url(sample):
    return f'/api/clinic/samples/{sample.id}/karyotype/'


def test_una_muestra_desactivada_devuelve_404_aunque_tenga_cariotipo(analyst_client,
                                                                     caso):
    """Version auditada de `test_muestra_desactivada_devuelve_404`.

    El agente lo escribio con `is_active=False` a secas, y la base lo rechazo:
    hay una CHECK (`samples_deactivated_implies_deleted_at`) que exige registrar
    CUANDO se borro. No podia saberlo — no estaba en los dos ficheros que se le
    dieron.

    Y tenia un segundo problema mas serio: su muestra no tenia cariotipo, asi
    que el 404 habria salido igual sin mirar `is_active`. **El test habria
    pasado en verde sin probar nada.** Corregido: el caso SI tiene cariotipo, y
    entonces el 404 solo puede venir del borrado logico.
    """
    caso.is_active = False
    caso.deleted_at = timezone.now()
    caso.save(update_fields=['is_active', 'deleted_at'])

    assert analyst_client.get(url(caso)).status_code == 404


def test_los_cromosomas_llegan_ordenados_por_el_campo_order(analyst_client, caso):
    """Version auditada de `test_cromosomas_estan_ordenados_por_order`.

    El agente afirmaba `chromosomes[0]['order'] == 0`, `[1] == 1`, `[2] == 2`.
    Funciona, pero solo mientras la fixture tenga exactamente tres cromosomas:
    es una afirmacion sobre el fixture disfrazada de afirmacion sobre el orden.

    Corregido: se compara la lista entera contra su propia version ordenada. Da
    igual cuantos cromosomas haya, y se pone rojo si el endpoint deja de
    ordenar — que es lo unico que se queria proteger. El visor los pinta en ese
    orden en el cariograma; desordenados, el analista veria un cariotipo que no
    corresponde a la metafase.
    """
    ordenes = [c['order'] for c in analyst_client.get(url(caso)).json()['chromosomes']]

    assert ordenes == sorted(ordenes)
    assert len(ordenes) == 3, 'sin cromosomas el assert de arriba pasa en vacio'


def test_sample_iscn_llega_vacio_mientras_no_se_ha_generado(analyst_client, caso):
    """Version auditada de `test_sample_iscn_es_cadena_vacia_mientras_no_seha_generado`.

    El assert estaba bien; lo unico que se toco es el nombre, que venia con una
    palabra partida («no_seha_generado»). Suena menor y no lo es: el nombre del
    test es lo que se lee en la salida de pytest cuando algo se rompe.

    Que sea cadena vacia y no `null` es del contrato (RN-04, `contratos.py`): el
    visor concatena ese campo, y un `null` le pintaria «null» al analista.
    """
    datos = analyst_client.get(url(caso)).json()

    assert datos['sample_iscn'] == ''
    assert isinstance(datos['sample_iscn'], str)


def test_model_version_declara_que_produjo_el_cariotipo(analyst_client, caso):
    """Version auditada de `test_model_version_viaja_en_la_respuesta`.

    El agente escribio `assert r.json()['model_version'] is not None`, **justo
    lo que el prompt prohibia** («assert exacto sobre el JSON»). Ese assert pasa
    con la cadena vacia, y una cadena vacia es exactamente el fallo que
    importa: un cariotipo sin declarar que modelo lo produjo no es trazable
    (ADR-0021).

    Corregido a igualdad exacta contra lo que la fixture sembro.
    """
    datos = analyst_client.get(url(caso)).json()

    assert datos['model_version'] == 'opencv-v0+efnb3-v3'
