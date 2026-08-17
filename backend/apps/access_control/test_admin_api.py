from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.access_control.models import Device, Card, Schedule, AccessRule

class AdministrativeAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.super_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password123',
            first_name='Admin',
            last_name='User'
        )
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='password123',
            is_staff=True,
            first_name='Staff',
            last_name='User'
        )
        self.normal_user = User.objects.create_user(
            username='employee',
            email='employee@example.com',
            password='password123',
            is_staff=False,
            first_name='Normal',
            last_name='Employee'
        )

        # Seed dummy data
        self.device = Device.objects.create(device_id='esp32_test', name='Test Door')
        self.card = Card.objects.create(uid='E9B3A2C8', user=self.normal_user)
        self.schedule = Schedule.objects.create(
            name='Office Hours',
            monday=True, tuesday=True, wednesday=True, thursday=True, friday=True,
            start_time='09:00:00', end_time='17:00:00'
        )
        self.rule = AccessRule.objects.create(
            user=self.normal_user,
            device=self.device,
            schedule=self.schedule,
            is_active=True
        )

    def test_unauthenticated_requests_are_blocked(self):
        endpoints = [
            reverse('user-list'),
            reverse('card-list'),
            reverse('device-list'),
            reverse('schedule-list'),
            reverse('rule-list'),
            reverse('dashboard-stats'),
            reverse('auth-status')
        ]
        
        for url in endpoints:
            response = self.client.get(url)
            # DRF returns 403 Forbidden for unauthenticated users under session auth
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, f"Failed at {url}")

    def test_authenticated_non_staff_requests_are_blocked(self):
        self.client.force_authenticate(user=self.normal_user)
        
        endpoints = [
            reverse('user-list'),
            reverse('card-list'),
            reverse('device-list'),
            reverse('schedule-list'),
            reverse('rule-list'),
            reverse('dashboard-stats'),
            reverse('auth-status')
        ]
        
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, f"Failed at {url}")

    def test_authenticated_staff_requests_are_allowed(self):
        self.client.force_authenticate(user=self.staff_user)
        
        endpoints = [
            (reverse('user-list'), 3), # 3 users registered (admin, staff, employee)
            (reverse('card-list'), 1),
            (reverse('device-list'), 1),
            (reverse('schedule-list'), 1),
            (reverse('rule-list'), 1),
        ]
        
        for url, expected_count in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK, f"Failed at {url}")
            self.assertEqual(response.data['count'], expected_count, f"Count mismatch at {url}")

    def test_auth_login_endpoints(self):
        # 1. Test invalid login
        response = self.client.post(reverse('auth-login'), {
            'username': 'staff',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # 2. Test normal user login (staff restricted)
        response = self.client.post(reverse('auth-login'), {
            'username': 'employee',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Test successful staff login
        response = self.client.post(reverse('auth-login'), {
            'username': 'staff',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'staff')

    def test_dashboard_stats_endpoint(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(reverse('dashboard-stats'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify stats data structure
        self.assertEqual(response.data['employees_count'], 3)
        self.assertEqual(response.data['cards_count'], 1)
        self.assertEqual(response.data['devices_count'], 1)
