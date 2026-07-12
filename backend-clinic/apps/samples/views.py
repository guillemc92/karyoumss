from rest_framework import generics, permissions

from .models import Sample
from .serializers import SampleCreateSerializer, SampleListItemSerializer


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
