from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Sample, SampleStatus
from .permissions import CanRegisterSample, HasOpcion, IsOwnerOrStaff
from .pipeline_client import MLDegradedError, pipeline_client
from .serializers import (
    KaryotypeSerializer,
    SampleCreateSerializer,
    SampleListItemSerializer,
    SampleReadSerializer,
    SampleRegisterSerializer,
    SampleUpdateSerializer,
)
from .services import ChnDuplicateError, sample_registration_service


class SampleListCreateView(generics.ListCreateAPIView):
    """GET /api/clinic/samples/  POST /api/clinic/samples/

    RN-06: analista ve solo sus propias muestras; staff (supervisor/admin) ve todas.
    Filtros server-side (SPEC-008 UC-S-002): status, chn_query, date_from, date_to.
    Shape de respuesta: array plano (el frontend pagina client-side, decisión
    2026-07-16 para no romper SampleListPage/useSamples ya construidos).
    """

    def get_permissions(self):
        codigo = 'sample.create' if self.request.method == 'POST' else 'sample.list'
        return [HasOpcion(codigo)]

    def get_queryset(self):
        qs = Sample.objects.filter(is_active=True)
        user = self.request.user
        if not user.is_staff:
            qs = qs.filter(analyst=user)

        params = self.request.query_params
        status_param = params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        chn_query = params.get('chn_query')
        if chn_query:
            qs = qs.filter(chn_code__icontains=chn_query)
        date_from = params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        date_to = params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SampleCreateSerializer
        return SampleListItemSerializer

    def perform_create(self, serializer):
        serializer.save(analyst=self.request.user)


class SampleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/clinic/samples/{id}/ (ADR-0018, cierre SPEC-008 §6).

    - GET/PATCH: los 3 roles clínicos, scoped por objeto (analista solo
      propias -> 403 NOT_OWNER si no es dueño; supervisor/admin cualquiera).
    - DELETE: solo admin (is_superuser). Soft-delete; rechaza con 409 si la
      muestra ya está VALIDATED (irreversible por diseño, RN-04/05 spirit).
    """

    queryset = Sample.objects.filter(is_active=True)
    lookup_field = 'pk'

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [HasOpcion('sample.delete')]
        codigo = 'sample.edit' if self.request.method in ('PATCH', 'PUT') else 'sample.view'
        return [HasOpcion(codigo), IsOwnerOrStaff()]

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return SampleUpdateSerializer
        return SampleReadSerializer

    def destroy(self, request, *args, **kwargs):
        sample = self.get_object()
        if sample.status == SampleStatus.VALIDATED:
            return Response(
                {'code': 'SAMPLE_VALIDATED', 'detail': 'No se puede eliminar una muestra validada'},
                status=status.HTTP_409_CONFLICT,
            )
        sample.is_active = False
        sample.deleted_at = timezone.now()
        sample.save(update_fields=['is_active', 'deleted_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SampleRegisterView(APIView):
    """POST /api/clinic/samples/register/ — Registro de Muestras (ADR-0016, SPEC-009).

    Endpoint compuesto: crea Sample + PatientVault + N SampleImage en una
    transacción atómica. RN-03: PII cifrada en PatientVault. RN-07: si el
    pipeline FastAPI está degradado, la muestra se persiste igual.
    """

    permission_classes = [CanRegisterSample]

    def post(self, request):
        serializer = SampleRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'code': self._error_code(serializer.errors), 'detail': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = sample_registration_service.register(serializer.validated_data, request.user)
        except ChnDuplicateError:
            return Response({'code': 'CHN_DUPLICATE', 'detail': 'CHN ya existe'}, status=status.HTTP_409_CONFLICT)

        return Response(result, status=status.HTTP_201_CREATED)

    @staticmethod
    def _error_code(errors) -> str:
        flat = str(errors)
        for code in ('INVALID_CHN_FORMAT', 'PATIENT_NAME_REQUIRED', 'INSUFFICIENT_IMAGES'):
            if code in flat:
                return code
        sample_errors = errors.get('sample')
        if isinstance(sample_errors, dict) and 'chn_code' in sample_errors:
            return 'CHN_REQUIRED'
        return 'VALIDATION_ERROR'


def _get_owned_sample_or_none(pk, user):
    """Busca la muestra activa por pk. Devuelve (sample, None) o (None, error_response)."""
    try:
        sample = Sample.objects.get(pk=pk, is_active=True)
    except Sample.DoesNotExist:
        return None, Response({'code': 'NOT_FOUND', 'detail': 'Muestra no encontrada'}, status=status.HTTP_404_NOT_FOUND)
    if not user.is_staff and sample.analyst_id != user.id:
        return None, Response({'code': 'NOT_OWNER', 'detail': 'No es dueño de esta muestra'}, status=status.HTTP_403_FORBIDDEN)
    return sample, None


class SampleProcessView(APIView):
    """POST /api/clinic/samples/{id}/process/ — encola el pipeline FastAPI (SPEC-008 UC-S-006).

    RN-06: analista solo puede procesar sus propias muestras (403 NOT_OWNER).
    RN-07: si el FastAPI clínico está degradado, retorna 503 ML_DEGRADED sin
    romper el flujo (la muestra sigue existiendo, se puede reintentar).
    """

    def get_permissions(self):
        return [HasOpcion('sample.process')]

    def post(self, request, pk):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error

        force_reprocess = bool(request.data.get('force_reprocess', False))
        if sample.status == SampleStatus.PROCESSING:
            return Response({'code': 'ALREADY_PROCESSING', 'detail': 'La muestra ya está en procesamiento'}, status=status.HTTP_409_CONFLICT)

        try:
            result = pipeline_client.trigger_processing(str(sample.id), force_reprocess=force_reprocess)
        except MLDegradedError:
            return Response(
                {'code': 'ML_DEGRADED', 'detail': 'Pipeline de IA no disponible. Use el modo manual.', 'retry_after_seconds': 60},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        sample.status = SampleStatus.PROCESSING
        sample.save(update_fields=['status', 'updated_at'])
        return Response(
            {'sample_id': str(sample.id), 'task_id': result.get('task_id'), 'status': 'queued'},
            status=status.HTTP_202_ACCEPTED,
        )


class SampleStatusView(APIView):
    """GET /api/clinic/samples/{id}/status/ — estado del pipeline (SPEC-008 UC-S-007, polling).

    Mismo scoping que SampleProcessView (RN-06). Read-only: sin circuit
    breaker propio, delega en pipeline_client.get_status(). Usa la
    opción 'sample.view' (ver estado es parte de ver la muestra, no
    hay una opción RBAC dedicada para polling — ADR-0019 no la definió
    como acción separada).
    """

    def get_permissions(self):
        return [HasOpcion('sample.view')]

    def get(self, request, pk):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error

        try:
            result = pipeline_client.get_status(str(sample.id))
        except MLDegradedError:
            return Response(
                {'code': 'ML_DEGRADED', 'detail': 'Pipeline de IA no disponible.', 'retry_after_seconds': 60},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                'sample_id': str(sample.id),
                'status': result.get('status', sample.status),
                'progress': result.get('progress'),
                'chromosome_count': result.get('chromosome_count'),
                'confidence_avg': result.get('confidence_avg'),
            },
            status=status.HTTP_200_OK,
        )


class KaryotypeView(APIView):
    """GET /api/clinic/samples/{id}/karyotype/ — visor read-only (ADR-0021 P1).

    RN-06: mismo scope de propiedad que SampleDetailView (analista solo sus
    propias muestras → 403 NOT_OWNER; supervisor/admin cualquiera).
    404 NO_KARYOTYPE si la muestra aún no tiene cariotipo generado.
    """

    def get_permissions(self):
        return [HasOpcion('sample.view')]

    def get(self, request, pk):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error

        karyotype = getattr(sample, 'karyotype', None)
        if karyotype is None:
            return Response(
                {'code': 'NO_KARYOTYPE', 'detail': 'La muestra aún no tiene cariotipo generado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(KaryotypeSerializer(karyotype).data, status=status.HTTP_200_OK)
