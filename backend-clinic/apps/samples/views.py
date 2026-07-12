from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Sample
from .permissions import CanRegisterSample
from .serializers import SampleCreateSerializer, SampleListItemSerializer, SampleRegisterSerializer
from .services import ChnDuplicateError, sample_registration_service


class SampleListCreateView(generics.ListCreateAPIView):
    """GET /api/clinic/samples/  POST /api/clinic/samples/

    RN-06: analista ve solo sus propias muestras; staff (supervisor/admin) ve todas.
    Vertical slice: sin filtros de status/chn/fecha todavía (T13 completo los agrega).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Sample.objects.filter(is_active=True)
        user = self.request.user
        if not user.is_staff:
            qs = qs.filter(analyst=user)
        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SampleCreateSerializer
        return SampleListItemSerializer

    def perform_create(self, serializer):
        serializer.save(analyst=self.request.user)


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
