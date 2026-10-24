"""Contrato OpenAPI de backend-clinic (DD-API-001).

El contrato se genera desde el código con drf-spectacular
(`python manage.py spectacular --file openapi.json --validate`) y el CI comprueba
que `backend-clinic/openapi.json` es exactamente lo que genera (drift).

Las vistas del servicio son `APIView` que leen `request.data` sin serializer de
entrada, así que el generador no sabe qué esperan ni qué devuelven. Aquí:

- **Los endpoints de la corrección manual (DD-KARYO-007, FSD-UC-003)** se
  describen enteros: cuerpo de entrada, respuesta y cada error con su `code`.
  Son los de la funcionalidad que se presenta en la Demo 2 de M8.
- **El resto** se declara con una respuesta genérica (objeto JSON sin
  describir). Es deuda declarada en DD-API-001 D2, no un olvido: así aparecen en
  el contrato y el generador no los descarta en silencio.

Se aplica al importarse desde `urls.py`, antes de que nadie genere el esquema.
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers

from . import views
from .models import CHROMOSOME_CLASSES
from .serializers import ChromosomeSerializer, KaryotypeSerializer
from .services import MOTIVOS_DESCARTE


class SharedJWTScheme(OpenApiAuthenticationExtension):
    """El JWT que emite backend-admin (ADR-0020), en `Authorization: Bearer`."""

    target_class = 'apps.samples.auth_bridge.SharedJWTAuthentication'
    name = 'jwtBackendAdmin'

    def get_security_definition(self, auto_schema):
        return {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}


# ---------------------------------------------------------------------------
# Piezas comunes
# ---------------------------------------------------------------------------

ErrorApi = inline_serializer('ErrorApi', {
    'code': serializers.CharField(help_text='Código estable del error, p. ej. CASE_LOCKED.'),
    'detail': serializers.CharField(help_text='Motivo legible, para mostrar al analista.'),
})

Caja = inline_serializer('Caja', {
    'x': serializers.IntegerField(min_value=0),
    'y': serializers.IntegerField(min_value=0),
    'w': serializers.IntegerField(min_value=1),
    'h': serializers.IntegerField(min_value=1),
})


def _error(descripcion: str) -> OpenApiResponse:
    return OpenApiResponse(ErrorApi, description=descripcion)


SIN_SESION = _error('Sin JWT o JWT caducado.')
NO_ES_SUYO = _error('NOT_OWNER: la muestra es de otro analista (RN-06), o falta el permiso sample.edit.')
CASO_BLOQUEADO = _error('CASE_LOCKED: el caso ya está validado y no admite correcciones (RN-04).')



# ---------------------------------------------------------------------------
# DD-KARYO-007 — corrección manual sobre la metafase (FSD-UC-003)
# ---------------------------------------------------------------------------

extend_schema(
    tags=['Cariotipo'],
    summary='Cariotipo de la muestra',
    description='Cromosomas activos con su caja y su silueta en píxeles de la metafase, y el resumen del semáforo.',
    responses={200: KaryotypeSerializer, 401: SIN_SESION, 403: NO_ES_SUYO,
               404: _error('NOT_FOUND / NO_KARYOTYPE: la muestra no existe o aún no tiene cariotipo.')},
)(views.KaryotypeView)

extend_schema(
    tags=['Cariotipo'],
    summary='Metafase segmentada',
    description='La imagen sobre la que se segmentó el cariotipo; las cajas y siluetas están en sus píxeles.',
    responses={(200, 'image/*'): OpenApiResponse(OpenApiTypes.BINARY, description='BMP, PNG o JPEG.'),
               401: SIN_SESION, 403: NO_ES_SUYO,
               404: _error('NO_KARYOTYPE / NO_METAPHASE_IMAGE: no hay metafase utilizable (RN-07).')},
)(views.MetaphaseImageView)

extend_schema(
    tags=['Corrección manual'],
    summary='Completar las siluetas que faltan',
    description='Calcula con backend-ml el contorno de los cromosomas que solo tienen caja (casos anteriores a DD-KARYO-007). No emite evento de auditoría.',
    request=None,
    responses={200: inline_serializer('ContornosCompletados', {'completados': serializers.IntegerField(min_value=0)}),
               401: SIN_SESION, 403: NO_ES_SUYO,
               404: _error('NO_KARYOTYPE / NO_METAPHASE_IMAGE.'), 409: CASO_BLOQUEADO,
               503: _error('ML_UNAVAILABLE: backend-ml no responde; no cambia nada (RN-07).')},
)(views.KaryotypeContoursView)

extend_schema(
    tags=['Corrección manual'],
    summary='Añadir un cromosoma que la segmentación no vio',
    description='Evento ADD_OBJECT. Sin `clase` la decide el modelo; con `clase`, el analista (entra resuelto, BR-003).',
    request=inline_serializer('AnadirObjeto', {
        'bbox': Caja,
        'clase': serializers.ChoiceField(choices=CHROMOSOME_CLASSES, required=False,
                                         help_text='Vacío o ausente: la decide el modelo.'),
    }),
    responses={201: ChromosomeSerializer, 401: SIN_SESION, 403: NO_ES_SUYO,
               400: _error('VALIDATION_ERROR (caja inválida o fuera de la metafase) / INVALID_CLASS.'),
               404: _error('NO_KARYOTYPE / NO_METAPHASE_IMAGE.'), 409: CASO_BLOQUEADO,
               503: _error('CLASS_REQUIRED: la IA no responde y no se eligió clase; no se crea nada.')},
)(views.KaryotypeObjectsView)

extend_schema(
    tags=['Corrección manual'],
    summary='Descartar un objeto que no es un cromosoma',
    description='Evento REJECT_OBJECT. Borrado suave (`is_active = false`): la fila y su historia se quedan (RN-05).',
    request=inline_serializer('DescartarObjeto', {
        'motivo': serializers.ChoiceField(choices=sorted(MOTIVOS_DESCARTE)),
    }),
    responses={200: ChromosomeSerializer, 401: SIN_SESION, 403: NO_ES_SUYO,
               400: _error('VALIDATION_ERROR: motivo fuera de la lista.'),
               404: _error('CHROMOSOME_NOT_FOUND / NO_KARYOTYPE.'),
               409: _error('CASE_LOCKED / OBJECT_INACTIVE (ya descartado o absorbido).')},
)(views.ChromosomeRejectView)

extend_schema(
    tags=['Corrección manual'],
    summary='Separar un objeto por la línea trazada',
    description=('Evento SPLIT. backend-ml corta la máscara del objeto por la línea (en ráster); el original '
                 'se queda con el trozo mayor y cada trozo se reclasifica. Ya no hay corte por la mitad.'),
    request=inline_serializer('SepararObjeto', {
        'linea': serializers.ListField(
            child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2),
            min_length=2, help_text='Polilínea [[x, y], …] en píxeles de la metafase.'),
    }),
    responses={201: inline_serializer('Separado', {
                   'origen': ChromosomeSerializer(),
                   'creados': ChromosomeSerializer(many=True),
               }),
               401: SIN_SESION, 403: NO_ES_SUYO,
               400: _error('VALIDATION_ERROR: sin línea o mal formada.'),
               404: _error('CHROMOSOME_NOT_FOUND / NO_METAPHASE_IMAGE.'),
               409: _error('CASE_LOCKED / OBJECT_INACTIVE.'),
               422: _error('INVALID_CUT: la línea no separa el objeto; nada cambia.'),
               503: _error('ML_UNAVAILABLE: el corte lo calcula backend-ml; nada cambia (RN-07).')},
)(views.ChromosomeSplitView)

extend_schema(
    tags=['Corrección manual'],
    summary='Unir dos fragmentos',
    description='Evento JOIN. Une las siluetas (vía backend-ml) o, sin ellas, las cajas; el absorbido queda inactivo.',
    request=inline_serializer('UnirObjetos', {'other_id': serializers.UUIDField()}),
    responses={200: ChromosomeSerializer, 401: SIN_SESION, 403: NO_ES_SUYO,
               400: _error('JOIN_SELF / CROSS_KARYOTYPE.'),
               404: _error('CHROMOSOME_NOT_FOUND.'), 409: CASO_BLOQUEADO},
)(views.ChromosomeJoinView)

extend_schema(
    tags=['Corrección manual'],
    summary='Corregir el recorte de un cromosoma',
    description='Evento RECROP. Mueve el límite de uno y lo reclasifica; vuelve a quedar pendiente.',
    request=inline_serializer('Recortar', {'bbox': Caja}),
    responses={200: ChromosomeSerializer, 401: SIN_SESION, 403: NO_ES_SUYO,
               400: _error('VALIDATION_ERROR.'), 404: _error('CHROMOSOME_NOT_FOUND.'),
               409: CASO_BLOQUEADO},
)(views.ChromosomeRecropView)

extend_schema(
    tags=['Corrección manual'],
    summary='Girar 180° o voltear en el cariograma',
    description='Evento ORIENT. Presentación: se guarda en `measures.orientacion`; no toca bbox ni contour (D7).',
    request=inline_serializer('Orientar', {
        'giro': serializers.ChoiceField(choices=[0, 180]),
        'volteo': serializers.BooleanField(),
    }),
    responses={200: ChromosomeSerializer, 401: SIN_SESION, 403: NO_ES_SUYO,
               400: _error('VALIDATION_ERROR.'), 404: _error('CHROMOSOME_NOT_FOUND.'),
               409: _error('CASE_LOCKED / OBJECT_INACTIVE.')},
)(views.ChromosomeOrientView)

UltimaEdicion = inline_serializer('UltimaEdicion', {
    'evento': serializers.UUIDField(),
    'tipo': serializers.CharField(help_text='SPLIT, JOIN, RECROP, REJECT_OBJECT o ADD_OBJECT.'),
    'propia': serializers.BooleanField(help_text='Solo se deshace lo propio.'),
    'actor_name': serializers.CharField(),
    'created_at': serializers.DateTimeField(),
})

views.KaryotypeUndoView.get = extend_schema(
    tags=['Corrección manual'],
    summary='Qué desharía «Deshacer»',
    responses={200: inline_serializer('UltimaEdicionRespuesta', {'ultima': UltimaEdicion}),
               401: SIN_SESION, 403: NO_ES_SUYO, 404: _error('NO_KARYOTYPE.')},
)(views.KaryotypeUndoView.get)

views.KaryotypeUndoView.post = extend_schema(
    tags=['Corrección manual'],
    summary='Deshacer la última edición propia',
    description='Evento UNDO_EDIT que compensa al anterior; no borra nada (RN-05, D6).',
    request=None,
    responses={200: inline_serializer('Deshecho', {
                   'evento': serializers.UUIDField(), 'deshace': serializers.UUIDField(),
                   'tipo': serializers.CharField()}),
               401: SIN_SESION, 403: NO_ES_SUYO, 404: _error('NO_KARYOTYPE.'),
               409: _error('NOTHING_TO_UNDO / UNDO_NOT_OWN / UNDO_UNAVAILABLE / CASE_LOCKED.')},
)(views.KaryotypeUndoView.post)


# ---------------------------------------------------------------------------
# El resto: respuesta genérica, deuda declarada (DD-API-001 D2)
# ---------------------------------------------------------------------------

DESCRITAS = {
    views.KaryotypeView, views.MetaphaseImageView, views.KaryotypeContoursView,
    views.KaryotypeObjectsView, views.ChromosomeRejectView, views.ChromosomeSplitView,
    views.ChromosomeJoinView, views.ChromosomeRecropView, views.ChromosomeOrientView,
    views.KaryotypeUndoView,
}

SIN_DESCRIBIR = 'Sin describir todavía en el contrato (DD-API-001 D2): objeto JSON.'

for _nombre in dir(views):
    _vista = getattr(views, _nombre)
    if not (isinstance(_vista, type) and issubclass(_vista, views.APIView)
            and _vista.__module__ == views.__name__ and _vista not in DESCRITAS):
        continue
    if getattr(_vista, 'serializer_class', None) is None:
        extend_schema(
            tags=['Sin describir'],
            request=OpenApiTypes.OBJECT,
            responses={200: OpenApiResponse(OpenApiTypes.OBJECT, description=SIN_DESCRIBIR)},
        )(_vista)
    else:
        # Vistas genéricas con serializer: el generador ya las describe bien.
        extend_schema(tags=['Muestras'])(_vista)
