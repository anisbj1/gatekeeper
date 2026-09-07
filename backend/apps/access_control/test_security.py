import time
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.security_logs.models import AdminAuditLog
from apps.access_control.signals import create_predefined_groups
from axes.utils import reset as axes_reset
from axes.models import AccessAttempt


class SessionSecurityPolicyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staff_sec',
            password='password123',
            is_staff=True,
            is_active=True
        )

    def test_session_active_within_idle_window_stays_valid(self):
        # 1. Login
        self.client.force_login(self.staff_user)

        # Set session last_activity to 2 minutes ago (within 5min window)
        now_ts = time.time()
        session = self.client.session
        session['_session_created_at'] = now_ts - 120
        session['_session_last_activity'] = now_ts - 120
        session.save()

        # 2. Access dashboard
        response = self.client.get(reverse('frontend:dashboard'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 3. Verify session was updated to fresh timestamp
        updated_session = self.client.session
        self.assertGreater(updated_session['_session_last_activity'], now_ts - 10)

    def test_session_expires_after_5_minutes_of_inactivity(self):
        self.client.force_login(self.staff_user)

        # Simulate 6 minutes (360s) of inactivity
        now_ts = time.time()
        session = self.client.session
        session['_session_created_at'] = now_ts - 400
        session['_session_last_activity'] = now_ts - 360
        session.save()

        # 1. HTML request redirects to login
        response = self.client.get(reverse('frontend:dashboard'))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn('/login/', response.url)

        # 2. Verify audit log was created for inactivity timeout
        log = AdminAuditLog.objects.filter(target_user='staff_sec', event_type='SESSION_EXPIRED').first()
        self.assertIsNotNone(log)
        self.assertIn('inactivity', log.details.lower())

    def test_session_expires_after_24_hours_maximum_lifetime(self):
        self.client.force_login(self.staff_user)

        # Simulate active within last minute, but session created 25 hours ago (> 86400s)
        now_ts = time.time()
        session = self.client.session
        session['_session_created_at'] = now_ts - (25 * 3600)
        session['_session_last_activity'] = now_ts - 30
        session.save()

        response = self.client.get(reverse('frontend:dashboard'))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn('/login/', response.url)

        log = AdminAuditLog.objects.filter(target_user='staff_sec', event_type='SESSION_EXPIRED').first()
        self.assertIsNotNone(log)
        self.assertIn('maximum allowed lifetime', log.details.lower())


class AccountLockUnlockTests(TestCase):
    def setUp(self):
        self.api_client = APIClient()
        self.super_user = User.objects.create_superuser(
            username='admin_boss',
            password='password123',
            is_staff=True,
            is_active=True
        )
        self.target_user = User.objects.create_user(
            username='target_employee',
            password='password123',
            is_staff=True,
            is_active=True
        )

    def test_super_admin_can_lock_and_unlock_account(self):
        self.api_client.force_authenticate(user=self.super_user)

        # 1. Lock account
        lock_url = reverse('user-lock', kwargs={'pk': self.target_user.pk})
        response = self.api_client.post(lock_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.is_active)

        # Verify audit log
        log = AdminAuditLog.objects.filter(target_user='target_employee', event_type='ACCOUNT_LOCKED').first()
        self.assertIsNotNone(log)

        # 2. Attempt login on locked account
        self.api_client.force_authenticate(user=None)
        login_res = self.api_client.post(reverse('auth-login'), {
            'username': 'target_employee',
            'password': 'password123'
        })
        self.assertEqual(login_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('disabled', login_res.data['error'].lower())

        # 3. Unlock account
        self.api_client.force_authenticate(user=self.super_user)
        unlock_url = reverse('user-unlock', kwargs={'pk': self.target_user.pk})
        unlock_res = self.api_client.post(unlock_url)
        self.assertEqual(unlock_res.status_code, status.HTTP_200_OK)

        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.is_active)

        # Verify unlock audit log
        unlock_log = AdminAuditLog.objects.filter(target_user='target_employee', event_type='ACCOUNT_UNLOCKED').first()
        self.assertIsNotNone(unlock_log)

    def test_locked_user_active_session_is_terminated_immediately(self):
        client = Client()
        client.force_login(self.target_user)

        # Admin locks user
        self.target_user.is_active = False
        self.target_user.save()

        # Next request by user must be immediately rejected and session killed
        res = client.get(reverse('frontend:dashboard'))
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)
        self.assertIn('/login/', res.url)


class BruteForceProtectionTests(TestCase):
    def setUp(self):
        axes_reset()
        self.api_client = APIClient()
        self.super_user = User.objects.create_superuser(
            username='admin_bf',
            password='password123',
            is_staff=True,
            is_active=True
        )

    def tearDown(self):
        axes_reset()

    def test_ip_blocking_after_failed_login_attempts(self):
        # 5 failed login attempts from IP 192.168.1.100
        for i in range(5):
            res = self.api_client.post(
                reverse('auth-login'),
                {'username': 'admin_bf', 'password': 'wrongpassword'},
                REMOTE_ADDR='192.168.1.100'
            )
            self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_429_TOO_MANY_REQUESTS])

        # 6th attempt must be blocked by IP with 429 Too Many Requests
        blocked_res = self.api_client.post(
            reverse('auth-login'),
            {'username': 'admin_bf', 'password': 'password123'},
            REMOTE_ADDR='192.168.1.100'
        )
        self.assertEqual(blocked_res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # 7th Super Admin unblocks IP
        self.api_client.force_authenticate(user=self.super_user)
        unblock_res = self.api_client.post(
            reverse('security-unblock-ip'),
            {'ip_address': '192.168.1.100'}
        )
        self.assertEqual(unblock_res.status_code, status.HTTP_200_OK)

        # Now login should succeed from that IP
        self.api_client.force_authenticate(user=None)
        login_res = self.api_client.post(
            reverse('auth-login'),
            {'username': 'admin_bf', 'password': 'password123'},
            REMOTE_ADDR='192.168.1.100'
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)


class PrivilegeLevelsAndPermissionsTests(TestCase):
    def setUp(self):
        create_predefined_groups(sender=None)
        self.api_client = APIClient()
        self.client = Client()

        # Super Admin
        self.super_user = User.objects.create_superuser(
            username='root_admin',
            password='password123',
            is_staff=True,
            is_active=True
        )

        # Operational Admin
        self.op_admin = User.objects.create_user(
            username='op_operator',
            password='password123',
            is_staff=True,
            is_active=True
        )
        op_group = Group.objects.get(name='Operational Admin')
        self.op_admin.groups.add(op_group)

        # Standard User
        self.standard_user = User.objects.create_user(
            username='plain_user',
            password='password123',
            is_staff=False,
            is_active=True
        )

    def test_operational_admin_cannot_access_django_admin(self):
        self.client.force_login(self.op_admin)
        res = self.client.get('/admin/')
        # Should be redirected to admin login or forbidden since only is_superuser is allowed
        self.assertIn(res.status_code, [status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN])

    def test_super_admin_can_access_django_admin(self):
        self.client.force_login(self.super_user)
        res = self.client.get('/admin/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_operational_admin_cannot_lock_accounts_via_api(self):
        self.api_client.force_authenticate(user=self.op_admin)
        lock_url = reverse('user-lock', kwargs={'pk': self.standard_user.pk})
        response = self.api_client.post(lock_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_operational_admin_cannot_unblock_ips(self):
        self.api_client.force_authenticate(user=self.op_admin)
        res = self.api_client.post(reverse('security-unblock-ip'), {'ip_address': '127.0.0.1'})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_operational_admin_can_read_users_and_access_frontoffice(self):
        self.client.force_login(self.op_admin)
        res = self.client.get(reverse('frontend:dashboard'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.api_client.force_authenticate(user=self.op_admin)
        users_res = self.api_client.get(reverse('user-list'))
        self.assertEqual(users_res.status_code, status.HTTP_200_OK)

