from django.urls import path

from .views import (
    KaryotypeView,
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
]
