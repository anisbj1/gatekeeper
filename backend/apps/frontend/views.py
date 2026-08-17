from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User

def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('frontend:dashboard')
    return render(request, 'frontend/login.html')

@staff_member_required(login_url='frontend:login')
def dashboard_view(request):
    return render(request, 'frontend/dashboard.html')

@staff_member_required(login_url='frontend:login')
def employees_view(request):
    return render(request, 'frontend/employees.html')

@staff_member_required(login_url='frontend:login')
def cards_view(request):
    users = User.objects.all().order_by('username')
    return render(request, 'frontend/cards.html', {'users': users})

@staff_member_required(login_url='frontend:login')
def devices_view(request):
    return render(request, 'frontend/devices.html')

@staff_member_required(login_url='frontend:login')
def logs_view(request):
    return render(request, 'frontend/logs.html')

@staff_member_required(login_url='frontend:login')
def rules_view(request):
    from apps.access_control.models import Device, Card, Schedule
    users = User.objects.all().order_by('username')
    cards = Card.objects.all().order_by('uid')
    devices = Device.objects.filter(is_active=True).order_by('device_id')
    schedules = Schedule.objects.all().order_by('name')
    
    return render(request, 'frontend/rules.html', {
        'users': users,
        'cards': cards,
        'devices': devices,
        'schedules': schedules
    })

@staff_member_required(login_url='frontend:login')
def face_enroll_view(request):
    users = User.objects.all().order_by('username')
    return render(request, 'frontend/face_enroll.html', {'users': users})
