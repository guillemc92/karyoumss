from django.urls import path

from .views import SampleDetailView, SampleListCreateView, SampleRegisterView

app_name = 'samples'

urlpatterns = [
    path('samples/register/', SampleRegisterView.as_view(), name='sample-register'),
    path('samples/', SampleListCreateView.as_view(), name='sample-list-create'),
    path('samples/<uuid:pk>/', SampleDetailView.as_view(), name='sample-detail'),
]
