from django.urls import path
from .views import (
    login_view,
    dashboard_view,
    employees_view,
    cards_view,
    devices_view,
    logs_view,
    rules_view,
    face_enroll_view
)

app_name = 'frontend'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('', dashboard_view, name='dashboard-redirect'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('employees/', employees_view, name='employees'),
    path('cards/', cards_view, name='cards'),
    path('devices/', devices_view, name='devices'),
    path('logs/', logs_view, name='logs'),
    path('rules/', rules_view, name='rules'),
    path('enroll/', face_enroll_view, name='enroll'),
]
