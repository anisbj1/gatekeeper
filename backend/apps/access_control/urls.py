from django.urls import path
from .views import AccessVerifyView

urlpatterns = [
    path('access/verify/', AccessVerifyView.as_view(), name='access-verify'),
]
