from django.urls import path

from .views import SampleListCreateView

app_name = 'samples'

urlpatterns = [
    path('samples/', SampleListCreateView.as_view(), name='sample-list-create'),
]
