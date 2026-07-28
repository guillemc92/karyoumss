from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditReview, Chromosome, Sample, SampleStatus
from .permissions import CanRegisterSample, HasOpcion, IsOwnerOrStaff
from .pipeline_client import MLDegradedError, pipeline_client
from .serializers import (
    AuditEventSerializer,
    AuditReviewSerializer,
    ChromosomeSerializer,
    KaryotypeSerializer,
    SampleCreateSerializer,
    SampleListItemSerializer,
    SampleReadSerializer,
    SampleRegisterSerializer,
    SampleUpdateSerializer,
)
from .admin_client import MfaServiceError
from .services import (
    AuditIncompleteError,
    CaseBlockedError,
    CaseLockedError,
    ChnDuplicateError,
    CrossKaryotypeError,
    InvalidClassError,
    InvalidDecisionError,
    JoinSelfError,
    MfaInvalidError,
    MfaLockedError,
    MfaNotEnrolledError,
    NotAuditableError,
    NotOrangeError,
    NotSignableError,
    SameClassError,
    SegregationError,
    XaiRequiredError,
    audit_summary,
    decide_audit,
    generate_narrative,
    join_chromosomes,
    mark_anomaly,
    reclassify_chromosome,
    reprocess_sample,
    resolve_chromosome,
    resolve_cross,
    sample_registration_service,
    select_audit_sample,
    sign_report,
    split_chromosome,
    validate_case,
    view_xai,
)


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


def _request_mode(request) -> str:
    """FSD-UC-007 §7: el frontend marca las acciones hechas en modo degradado
    (sin IA) con el header `X-Biomed-Mode`. Es un estado del sistema
    (cross-cutting), por eso va en header y no en el body de cada endpoint."""
    return 'degradado' if request.META.get('HTTP_X_BIOMED_MODE') == 'degradado' else 'auto'


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

        if sample.status == SampleStatus.PROCESSING:
            return Response({'code': 'ALREADY_PROCESSING', 'detail': 'La muestra ya está en procesamiento'}, status=status.HTTP_409_CONFLICT)

        # Flujo real (DD-ML-002): segmenta la imagen con backend-ml e ingesta el
        # cariotipo de forma síncrona (baseline). RN-07: 503 si backend-ml cae.
        try:
            karyotype = reprocess_sample(sample)
        except MLDegradedError:
            return Response(
                {'code': 'ML_DEGRADED', 'detail': 'Pipeline de IA no disponible. Use el modo manual.', 'retry_after_seconds': 60},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        sample.status = SampleStatus.READY
        sample.save(update_fields=['status', 'updated_at'])
        return Response(
            {'sample_id': str(sample.id), 'status': sample.status, 'chromosome_count': karyotype.chromosomes.count()},
            status=status.HTTP_200_OK,
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

        # Estado local (DD-ML-002): el procesamiento es síncrono en registro/
        # process, así que el estado ya está persistido; no se consulta backend-ml.
        karyotype = getattr(sample, 'karyotype', None)
        return Response(
            {
                'sample_id': str(sample.id),
                'status': sample.status,
                'progress': 1 if sample.status == SampleStatus.READY else 0,
                'chromosome_count': karyotype.chromosomes.count() if karyotype else 0,
                'confidence_avg': None,
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


def _get_owned_chromosome_or_error(sample, chromosome_id):
    """Busca el cromosoma dentro del cariotipo de la muestra (scope ya validado
    por _get_owned_sample_or_none). Devuelve (chromosome, None) o (None, 404)."""
    karyotype = getattr(sample, 'karyotype', None)
    if karyotype is None:
        return None, Response(
            {'code': 'NO_KARYOTYPE', 'detail': 'La muestra no tiene cariotipo.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        chromo = Chromosome.objects.get(id=chromosome_id, karyotype=karyotype)
    except Chromosome.DoesNotExist:
        return None, Response(
            {'code': 'CHROMOSOME_NOT_FOUND', 'detail': 'Cromosoma no encontrado en este cariotipo.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    return chromo, None


class ChromosomeXaiView(APIView):
    """POST /samples/{id}/chromosomes/{cid}/xai/ — XAI Grad-CAM (ADR-0021 P2).

    Registra XAI_VIEWED (BR-004) y marca el cromosoma como visto. El heatmap
    real lo produce el microservicio de inferencia (ADR-0007); acá mock.
    """

    def get_permissions(self):
        return [HasOpcion('sample.view')]

    def post(self, request, pk, cid):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error
        chromo, error = _get_owned_chromosome_or_error(sample, cid)
        if error:
            return error
        result = view_xai(sample, chromo, request.user, mode=_request_mode(request))
        return Response(result, status=status.HTTP_200_OK)


class ChromosomeResolveView(APIView):
    """POST /samples/{id}/chromosomes/{cid}/resolve/ — resolver naranja (P2).

    Exige XAI previo (BR-004): 409 XAI_REQUIRED si no. 400 NOT_ORANGE si el
    cromosoma no es naranja.
    """

    def get_permissions(self):
        return [HasOpcion('sample.edit')]

    def post(self, request, pk, cid):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error
        chromo, error = _get_owned_chromosome_or_error(sample, cid)
        if error:
            return error
        try:
            chromo = resolve_chromosome(sample, chromo, request.user, mode=_request_mode(request))
        except XaiRequiredError as e:
            return Response({'code': 'XAI_REQUIRED', 'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        except NotOrangeError as e:
            return Response({'code': 'NOT_ORANGE', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ChromosomeSerializer(chromo).data, status=status.HTTP_200_OK)


class ChromosomeAnomalyView(APIView):
    """POST /samples/{id}/chromosomes/{cid}/anomaly/ — marcar anomalía (M) (P2)."""

    def get_permissions(self):
        return [HasOpcion('sample.edit')]

    def post(self, request, pk, cid):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error
        chromo, error = _get_owned_chromosome_or_error(sample, cid)
        if error:
            return error
        chromo = mark_anomaly(sample, chromo, request.user, mode=_request_mode(request))
        return Response(ChromosomeSerializer(chromo).data, status=status.HTTP_200_OK)


class ChromosomeReclassifyView(APIView):
    """POST /samples/{id}/chromosomes/{cid}/reclassify/ — corregir clase (P3).

    Body: {"target_class": "7"}. Override manual del analista (BR-003): marca
    RESOLVED. 400 INVALID_CLASS / 400 SAME_CLASS / 409 CASE_LOCKED.
    """

    def get_permissions(self):
        return [HasOpcion('sample.edit')]

    def post(self, request, pk, cid):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error
        chromo, error = _get_owned_chromosome_or_error(sample, cid)
        if error:
            return error
        try:
            chromo = reclassify_chromosome(sample, chromo, request.data.get('target_class'), request.user, mode=_request_mode(request))
        except CaseLockedError as e:
            return Response({'code': 'CASE_LOCKED', 'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        except InvalidClassError as e:
            return Response({'code': 'INVALID_CLASS', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except SameClassError as e:
            return Response({'code': 'SAME_CLASS', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ChromosomeSerializer(chromo).data, status=status.HTTP_200_OK)


class ChromosomeSplitView(APIView):
    """POST /samples/{id}/chromosomes/{cid}/split/ — separar (touching) (P3)."""

    def get_permissions(self):
        return [HasOpcion('sample.edit')]

    def post(self, request, pk, cid):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error
        chromo, error = _get_owned_chromosome_or_error(sample, cid)
        if error:
            return error
        try:
            created = split_chromosome(sample, chromo, request.user, mode=_request_mode(request))
        except CaseLockedError as e:
            return Response({'code': 'CASE_LOCKED', 'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(ChromosomeSerializer(created).data, status=status.HTTP_201_CREATED)


class ChromosomeJoinView(APIView):
    """POST /samples/{id}/chromosomes/{cid}/join/ — unir fragmentos (P3).

    Body: {"other_id": "<uuid>"}. `cid` es el que se conserva; `other_id` el
    absorbido (queda inactivo). 400 JOIN_SELF / 409 CASE_LOCKED.
    """

    def get_permissions(self):
        return [HasOpcion('sample.edit')]

    def post(self, request, pk, cid):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error
        keep, error = _get_owned_chromosome_or_error(sample, cid)
        if error:
            return error
        absorbed, error = _get_owned_chromosome_or_error(sample, request.data.get('other_id'))
        if error:
            return error
        try:
            keep = join_chromosomes(sample, keep, absorbed, request.user, mode=_request_mode(request))
        except CaseLockedError as e:
            return Response({'code': 'CASE_LOCKED', 'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        except JoinSelfError as e:
            return Response({'code': 'JOIN_SELF', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except CrossKaryotypeError as e:
            return Response({'code': 'CROSS_KARYOTYPE', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ChromosomeSerializer(keep).data, status=status.HTTP_200_OK)


class ChromosomeCrossView(APIView):
    """POST /samples/{id}/chromosomes/{cid}/cross/ — resolver cruce (P3)."""

    def get_permissions(self):
        return [HasOpcion('sample.edit')]

    def post(self, request, pk, cid):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error
        chromo, error = _get_owned_chromosome_or_error(sample, cid)
        if error:
            return error
        try:
            chromo = resolve_cross(sample, chromo, request.user, mode=_request_mode(request))
        except CaseLockedError as e:
            return Response({'code': 'CASE_LOCKED', 'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(ChromosomeSerializer(chromo).data, status=status.HTTP_200_OK)


class CaseValidateView(APIView):
    """POST /samples/{id}/validate/ — transición a ANALYST_VALIDATED (FSD-UC-004).

    Rechaza 409 CASE_BLOCKED si hay naranjas sin resolver (RN-01).
    """

    def get_permissions(self):
        return [HasOpcion('sample.edit')]

    def post(self, request, pk):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error
        try:
            sample = validate_case(sample, request.user, mode=_request_mode(request))
        except CaseBlockedError as e:
            return Response({'code': 'CASE_BLOCKED', 'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        return Response({'sample_id': str(sample.id), 'status': sample.status}, status=status.HTTP_200_OK)


class AuditTrailView(APIView):
    """GET /samples/{id}/audit/ — bitácora append-only del caso (ADR-0022)."""

    def get_permissions(self):
        return [HasOpcion('sample.view')]

    def get(self, request, pk):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error
        events = sample.audit_events.all()
        return Response(AuditEventSerializer(events, many=True).data, status=status.HTTP_200_OK)


class AuditReviewListView(APIView):
    """GET /samples/{id}/audit-review/ — selección del 5% del Supervisor (ADR-0023 S1).

    Crea la selección determinista al primer acceso (idempotente). Permiso
    `case.audit` (Supervisor/Admin; el Analista NO lo tiene, segregación RN-06).
    """

    def get_permissions(self):
        return [HasOpcion('case.audit')]

    def get(self, request, pk):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error
        reviews = select_audit_sample(sample)
        return Response(
            {'reviews': AuditReviewSerializer(reviews, many=True).data, 'summary': audit_summary(sample)},
            status=status.HTTP_200_OK,
        )


class AuditDecideView(APIView):
    """POST /samples/{id}/audit-review/{cid}/decide/ — decisión del Supervisor (S1).

    Body: {"decision": "CONFIRMED"|"REJECTED", "comment": "..."}. Emite
    AUDIT_DECISION. 409 NOT_AUDITABLE si el caso no está ANALYST_VALIDATED.
    """

    def get_permissions(self):
        return [HasOpcion('case.audit')]

    def post(self, request, pk, cid):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error
        try:
            review = sample.audit_reviews.get(chromosome_id=cid)
        except AuditReview.DoesNotExist:
            return Response({'code': 'REVIEW_NOT_FOUND', 'detail': 'Cromosoma no está en la auditoría del 5%'}, status=status.HTTP_404_NOT_FOUND)
        try:
            review = decide_audit(sample, review, request.user, request.data.get('decision'), request.data.get('comment', ''))
        except NotAuditableError as e:
            return Response({'code': 'NOT_AUDITABLE', 'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        except InvalidDecisionError as e:
            return Response({'code': 'INVALID_DECISION', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AuditReviewSerializer(review).data, status=status.HTTP_200_OK)


class CaseSignView(APIView):
    """POST /samples/{id}/sign/ — firma MFA del Supervisor (ADR-0023 S2).

    Body: {"mfa_code": "123456"}. Verificación TOTP delegada a backend-admin.
    Errores: 409 NOT_SIGNABLE / 403 SEGREGATION_VIOLATION / 409 AUDIT_INCOMPLETE /
    423 MFA_LOCKED / 401 MFA_INVALID / 400 MFA_NOT_ENROLLED / 503 MFA_SERVICE.
    """

    def get_permissions(self):
        return [HasOpcion('case.sign')]

    def post(self, request, pk):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error
        try:
            sample = sign_report(sample, request.user, request.data.get('mfa_code', ''))
        except NotSignableError as e:
            return Response({'code': 'NOT_SIGNABLE', 'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        except SegregationError as e:
            return Response({'code': 'SEGREGATION_VIOLATION', 'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except AuditIncompleteError as e:
            return Response({'code': 'AUDIT_INCOMPLETE', 'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        except MfaLockedError as e:
            return Response({'code': 'MFA_LOCKED', 'detail': str(e)}, status=status.HTTP_423_LOCKED)
        except MfaNotEnrolledError as e:
            return Response({'code': 'MFA_NOT_ENROLLED', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except MfaInvalidError as e:
            return Response({'code': 'MFA_INVALID', 'detail': str(e)}, status=status.HTTP_401_UNAUTHORIZED)
        except MfaServiceError:
            return Response(
                {'code': 'MFA_SERVICE', 'detail': 'Servicio de MFA no disponible. Reintente.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {'sample_id': str(sample.id), 'status': sample.status, 'signed_at': sample.signed_at},
            status=status.HTTP_200_OK,
        )


class PipelineHealthView(APIView):
    """GET /api/clinic/pipeline/health/ — disponibilidad del pipeline de IA (P4).

    FSD-UC-007 §8: el visor consulta cada 30s para entrar/salir del modo
    degradado. Chequeo barato del circuit breaker (sin llamada de red).
    """

    def get_permissions(self):
        return [HasOpcion('sample.view')]

    def get(self, request):
        available = not pipeline_client._circuit_open()
        return Response(
            {'available': available, 'mode': 'auto' if available else 'degradado'},
            status=status.HTTP_200_OK,
        )


class CaseNarrativeView(APIView):
    """POST /samples/{id}/narrative/ — genera el borrador narrativo (ADR-0024).

    Body opcional: {"iscn": "47,XY,+21"}. Si no viene, se deriva del conteo de
    cromosomas activos del caso.

    El LLM **solo redacta**: el ISCN es un dato de entrada calculado por la
    función determinística (ADR-0023 D4), nunca por el modelo. La respuesta es un
    BORRADOR (`is_draft: true`) que el Supervisor debe revisar antes de que llegue
    al informe firmado.

    Nunca falla por el LLM: si el servicio no responde o el texto no supera la
    validación, devuelve 200 con `generated: false` y el motivo — la narrativa no
    puede bloquear la emisión del informe (RN-07).
    """

    def get_permissions(self):
        return [HasOpcion('case.sign')]

    def post(self, request, pk):
        sample, error = _get_owned_sample_or_none(pk, request.user)
        if error:
            return error

        iscn = (request.data.get('iscn') or '').strip()
        if not iscn:
            counts = {}
            karyotype = getattr(sample, 'karyotype', None)
            if karyotype:
                for chromo in karyotype.chromosomes.filter(is_active=True):
                    if chromo.predicted_class:
                        counts[chromo.predicted_class] = counts.get(chromo.predicted_class, 0) + 1
            total = sum(counts.values())
            iscn = f'{total},{"XY" if counts.get("Y") else "XX"}' if total else ''

        result = generate_narrative(
            sample, request.user, iscn,
            mode=request.headers.get('X-Biomed-Mode', 'auto'),
        )
        sample.refresh_from_db()
        return Response({
            'generated': result['generated'],
            'reason': result['reason'],
            'iscn_input': iscn,
            'narrative_draft': sample.narrative_draft,
            'model': sample.narrative_model,
            'generated_at': sample.narrative_generated_at,
            'is_draft': True,   # ADR-0024 D3: requiere revisión humana
        }, status=status.HTTP_200_OK)
