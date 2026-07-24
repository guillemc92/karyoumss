from django.urls import path

from .views import (
    AuditTrailView,
    CaseValidateView,
    ChromosomeAnomalyView,
    ChromosomeCrossView,
    ChromosomeJoinView,
    ChromosomeReclassifyView,
    ChromosomeResolveView,
    ChromosomeSplitView,
    ChromosomeXaiView,
    KaryotypeView,
    PipelineHealthView,
    SampleDetailView,
    SampleListCreateView,
    SampleProcessView,
    SampleRegisterView,
    SampleStatusView,
)

app_name = 'samples'

urlpatterns = [
    path('samples/register/', SampleRegisterView.as_view(), name='sample-register'),
    path('samples/', SampleListCreateView.as_view(), name='sample-list-create'),
    path('samples/<uuid:pk>/', SampleDetailView.as_view(), name='sample-detail'),
    path('samples/<uuid:pk>/process/', SampleProcessView.as_view(), name='sample-process'),
    path('samples/<uuid:pk>/status/', SampleStatusView.as_view(), name='sample-status'),
    # Cariotipo (ADR-0021 P1) — visor read-only con semaforización.
    path('samples/<uuid:pk>/karyotype/', KaryotypeView.as_view(), name='sample-karyotype'),

    # Cariotipo P2 (ADR-0021 P2, ADR-0022) — XAI + resolución + gating + audit.
    path('samples/<uuid:pk>/chromosomes/<uuid:cid>/xai/', ChromosomeXaiView.as_view(), name='chromosome-xai'),
    path('samples/<uuid:pk>/chromosomes/<uuid:cid>/resolve/', ChromosomeResolveView.as_view(), name='chromosome-resolve'),
    path('samples/<uuid:pk>/chromosomes/<uuid:cid>/anomaly/', ChromosomeAnomalyView.as_view(), name='chromosome-anomaly'),
    path('samples/<uuid:pk>/validate/', CaseValidateView.as_view(), name='sample-validate'),
    path('samples/<uuid:pk>/audit/', AuditTrailView.as_view(), name='sample-audit'),

    # Cariotipo P3 (ADR-0021 P3, DD-KARYO-003) — corrección manual.
    path('samples/<uuid:pk>/chromosomes/<uuid:cid>/reclassify/', ChromosomeReclassifyView.as_view(), name='chromosome-reclassify'),
    path('samples/<uuid:pk>/chromosomes/<uuid:cid>/split/', ChromosomeSplitView.as_view(), name='chromosome-split'),
    path('samples/<uuid:pk>/chromosomes/<uuid:cid>/join/', ChromosomeJoinView.as_view(), name='chromosome-join'),
    path('samples/<uuid:pk>/chromosomes/<uuid:cid>/cross/', ChromosomeCrossView.as_view(), name='chromosome-cross'),

    # Cariotipo P4 (ADR-0021 P4, DD-KARYO-004) — salud del pipeline (modo degradado).
    path('pipeline/health/', PipelineHealthView.as_view(), name='pipeline-health'),
]
