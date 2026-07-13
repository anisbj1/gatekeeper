import datetime
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from django.contrib.auth.models import User, Group
from apps.access_control.models import Device, Card, Schedule, AccessRule
from apps.access_control.services import AccessValidationService
from apps.security_logs.models import AccessLog
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.exceptions import ValidationError
from apps.access_control.serializers import AccessVerifySerializer

class AccessControlTests(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(username='testuser', password='password')
        self.user.first_name = "Test"
        self.user.last_name = "User"
        self.user.save()

        # Create device
        self.device = Device.objects.create(device_id='esp32_test', name='Test Entrance', is_active=True)

        # Create card
        self.card = Card.objects.create(uid='A1B2C3D4', user=self.user, is_active=True)

        # Create a standard weekday schedule (Monday 9:00 - 17:00)
        self.mon_schedule = Schedule.objects.create(
            name="Monday 9 to 5",
            monday=True,
            start_time=datetime.time(9, 0, 0),
            end_time=datetime.time(17, 0, 0)
        )

    def test_validate_scan_no_access_rule(self):
        # No rules exist for this card/device
        result = AccessValidationService.validate_scan('A1B2C3D4', 'esp32_test')
        self.assertFalse(result['authorized'])
        self.assertEqual(result['message'], 'No Access Rule')
        self.assertEqual(result['action'], 'keep_locked')
        
        # Verify log is created
        log = AccessLog.objects.latest('id')
        self.assertFalse(log.authorized)
        self.assertEqual(log.user_details, 'No Access Rule (testuser)')

    @patch('django.utils.timezone.now')
    def test_validate_scan_authorized_card_rule(self, mock_now):
        # Mock time: Monday July 6, 2026 10:00 AM UTC
        mock_now.return_value = datetime.datetime(2026, 7, 6, 10, 0, 0, tzinfo=datetime.timezone.utc)

        # Create rule mapped to Card
        AccessRule.objects.create(
            card=self.card,
            device=self.device,
            schedule=self.mon_schedule,
            is_active=True
        )

        result = AccessValidationService.validate_scan('A1B2C3D4', 'esp32_test')
        self.assertTrue(result['authorized'])
        self.assertEqual(result['message'], 'Welcome, Test User')
        self.assertEqual(result['action'], 'unlock')

        log = AccessLog.objects.latest('id')
        self.assertTrue(log.authorized)
        self.assertEqual(log.user_details, 'Test User')

    @patch('django.utils.timezone.now')
    def test_validate_scan_authorized_user_rule(self, mock_now):
        # Mock time: Monday July 6, 2026 10:00 AM UTC
        mock_now.return_value = datetime.datetime(2026, 7, 6, 10, 0, 0, tzinfo=datetime.timezone.utc)

        # Create rule mapped to User
        AccessRule.objects.create(
            user=self.user,
            device=self.device,
            schedule=self.mon_schedule,
            is_active=True
        )

        result = AccessValidationService.validate_scan('A1B2C3D4', 'esp32_test')
        self.assertTrue(result['authorized'])
        self.assertEqual(result['message'], 'Welcome, Test User')

    @patch('django.utils.timezone.now')
    def test_validate_scan_date_exceeded_past(self, mock_now):
        # Mock time: Monday July 6, 2026
        mock_now.return_value = datetime.datetime(2026, 7, 6, 10, 0, 0, tzinfo=datetime.timezone.utc)

        # Validity window starts in the future (starts Friday July 10)
        AccessRule.objects.create(
            card=self.card,
            device=self.device,
            start_date=datetime.date(2026, 7, 10),
            is_active=True
        )

        result = AccessValidationService.validate_scan('A1B2C3D4', 'esp32_test')
        self.assertFalse(result['authorized'])
        self.assertEqual(result['message'], 'Date Exceeded')

        log = AccessLog.objects.latest('id')
        self.assertEqual(log.user_details, 'Date Exceeded (testuser)')

    @patch('django.utils.timezone.now')
    def test_validate_scan_date_exceeded_future(self, mock_now):
        # Mock time: Monday July 6, 2026
        mock_now.return_value = datetime.datetime(2026, 7, 6, 10, 0, 0, tzinfo=datetime.timezone.utc)

        # Validity window ended in the past (ended Sunday July 5)
        AccessRule.objects.create(
            card=self.card,
            device=self.device,
            end_date=datetime.date(2026, 7, 5),
            is_active=True
        )

        result = AccessValidationService.validate_scan('A1B2C3D4', 'esp32_test')
        self.assertFalse(result['authorized'])
        self.assertEqual(result['message'], 'Date Exceeded')

    @patch('django.utils.timezone.now')
    def test_validate_scan_schedule_restricted_day(self, mock_now):
        # Mock time: Tuesday July 7, 2026 10:00 AM UTC (Schedule is Monday only)
        mock_now.return_value = datetime.datetime(2026, 7, 7, 10, 0, 0, tzinfo=datetime.timezone.utc)

        # Rule with Monday schedule
        AccessRule.objects.create(
            card=self.card,
            device=self.device,
            schedule=self.mon_schedule,
            is_active=True
        )

        result = AccessValidationService.validate_scan('A1B2C3D4', 'esp32_test')
        self.assertFalse(result['authorized'])
        self.assertEqual(result['message'], 'Schedule Restricted')

        log = AccessLog.objects.latest('id')
        self.assertEqual(log.user_details, 'Schedule Restricted (testuser)')

    @patch('django.utils.timezone.now')
    def test_validate_scan_schedule_restricted_time(self, mock_now):
        # Mock time: Monday July 6, 2026 6:00 PM UTC (Schedule is 9:00 - 17:00)
        mock_now.return_value = datetime.datetime(2026, 7, 6, 18, 0, 0, tzinfo=datetime.timezone.utc)

        # Rule with Monday schedule
        AccessRule.objects.create(
            card=self.card,
            device=self.device,
            schedule=self.mon_schedule,
            is_active=True
        )

        result = AccessValidationService.validate_scan('A1B2C3D4', 'esp32_test')
        self.assertFalse(result['authorized'])
        self.assertEqual(result['message'], 'Schedule Restricted')

    @patch('django.utils.timezone.now')
    def test_validate_scan_unrestricted_schedule_24_7(self, mock_now):
        # Mock time: Sunday July 5, 2026 11:30 PM UTC
        mock_now.return_value = datetime.datetime(2026, 7, 5, 23, 30, 0, tzinfo=datetime.timezone.utc)

        # Rule with null schedule (24/7 access)
        AccessRule.objects.create(
            card=self.card,
            device=self.device,
            schedule=None,
            is_active=True
        )

        result = AccessValidationService.validate_scan('A1B2C3D4', 'esp32_test')
        self.assertTrue(result['authorized'])
        self.assertEqual(result['message'], 'Welcome, Test User')

    @patch('django.utils.timezone.now')
    def test_validate_scan_multiple_rules_one_valid(self, mock_now):
        # Mock time: Monday July 6, 2026 10:00 AM UTC
        mock_now.return_value = datetime.datetime(2026, 7, 6, 10, 0, 0, tzinfo=datetime.timezone.utc)

        # Create two rules:
        # Rule 1: Expired date window (start and end in past)
        AccessRule.objects.create(
            card=self.card,
            device=self.device,
            start_date=datetime.date(2026, 7, 1),
            end_date=datetime.date(2026, 7, 5),
            schedule=None,
            is_active=True
        )
        # Rule 2: Active date window and Monday schedule
        AccessRule.objects.create(
            card=self.card,
            device=self.device,
            start_date=datetime.date(2026, 7, 6),
            schedule=self.mon_schedule,
            is_active=True
        )

        result = AccessValidationService.validate_scan('A1B2C3D4', 'esp32_test')
        self.assertTrue(result['authorized'])
        self.assertEqual(result['message'], 'Welcome, Test User')

    def test_validate_scan_device_inactive_priority(self):
        # Make device inactive
        self.device.is_active = False
        self.device.save()

        # Create valid 24/7 rule
        AccessRule.objects.create(
            card=self.card,
            device=self.device,
            schedule=None,
            is_active=True
        )

        result = AccessValidationService.validate_scan('A1B2C3D4', 'esp32_test')
        self.assertFalse(result['authorized'])
        self.assertEqual(result['message'], 'Device Inactive')


class AccessVerifyAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser', password='password')
        self.user.first_name = "Api"
        self.user.last_name = "User"
        self.user.save()

        # Create device with known token
        self.device = Device.objects.create(
            device_id='esp32_api_test', 
            name='API Entrance', 
            api_token='super_secret_token_123',
            is_active=True
        )

        # Create card
        self.card = Card.objects.create(uid='B2C3D4E5', user=self.user, is_active=True)

        # Create a rule mapped to Card (24/7)
        AccessRule.objects.create(
            card=self.card,
            device=self.device,
            schedule=None,
            is_active=True
        )

    def test_api_verify_authorized_with_correct_token(self):
        url = '/api/v1/access/verify/'
        data = {
            'card_uid': 'B2C3D4E5',
            'device_id': 'esp32_api_test'
        }
        # Add correct token to header
        self.client.credentials(HTTP_X_DEVICE_TOKEN='super_secret_token_123')
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authorized'])
        self.assertEqual(response.data['action'], 'unlock')

    def test_api_verify_missing_token_rejected(self):
        url = '/api/v1/access/verify/'
        data = {
            'card_uid': 'B2C3D4E5',
            'device_id': 'esp32_api_test'
        }
        # No credentials set
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify attempt is logged correctly
        log = AccessLog.objects.latest('id')
        self.assertFalse(log.authorized)
        self.assertEqual(log.device_id, 'esp32_api_test')
        self.assertEqual(log.card_uid, 'B2C3D4E5')
        self.assertEqual(log.user_details, 'Missing Device Token')

    def test_api_verify_incorrect_token_rejected(self):
        url = '/api/v1/access/verify/'
        data = {
            'card_uid': 'B2C3D4E5',
            'device_id': 'esp32_api_test'
        }
        # Add incorrect token to header
        self.client.credentials(HTTP_X_DEVICE_TOKEN='wrong_token')
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify attempt is logged correctly
        log = AccessLog.objects.latest('id')
        self.assertFalse(log.authorized)
        self.assertEqual(log.device_id, 'esp32_api_test')
        self.assertEqual(log.card_uid, 'B2C3D4E5')
        self.assertEqual(log.user_details, 'Invalid Device Token')

    def test_api_verify_unknown_device_rejected(self):
        url = '/api/v1/access/verify/'
        data = {
            'card_uid': 'B2C3D4E5',
            'device_id': 'unknown_device_id'
        }
        # Token header present
        self.client.credentials(HTTP_X_DEVICE_TOKEN='super_secret_token_123')
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify attempt is logged correctly
        log = AccessLog.objects.latest('id')
        self.assertFalse(log.authorized)
        self.assertEqual(log.device_id, 'unknown_device_id')
        self.assertEqual(log.card_uid, 'B2C3D4E5')
        self.assertEqual(log.user_details, 'Unknown Device')


class AccessControlValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='validation_user', password='password')

    def test_device_id_validation(self):
        # Valid device_ids
        d1 = Device(device_id='esp32_01', name='Main Entrance')
        d1.full_clean()  # Should not raise
        d2 = Device(device_id='esp32-cam-02', name='Side Entrance')
        d2.full_clean()  # Should not raise

        # Invalid device_ids
        with self.assertRaises(ValidationError):
            Device(device_id='esp32 main', name='Invalid Device').full_clean()
        with self.assertRaises(ValidationError):
            Device(device_id='esp32@main', name='Invalid Device').full_clean()
        with self.assertRaises(ValidationError):
            Device(device_id='', name='Invalid Device').full_clean()

    def test_device_name_validation(self):
        # Whitespace-only name should fail
        with self.assertRaises(ValidationError):
            Device(device_id='esp32_ok', name='   ').full_clean()

    def test_card_uid_validation_and_standardization(self):
        # Valid formats
        c1 = Card(uid='A1B2C3D4', user=self.user)
        c1.full_clean()
        self.assertEqual(c1.uid, 'A1B2C3D4')

        # Clean/standardize colons and lowercase
        c2 = Card(uid='a1:b2:c3:d4', user=self.user)
        c2.full_clean()
        self.assertEqual(c2.uid, 'A1B2C3D4')

        # Clean/standardize spaces
        c3 = Card(uid='a1 b2 c3 d4', user=self.user)
        c3.full_clean()
        self.assertEqual(c3.uid, 'A1B2C3D4')

        # Invalid characters (G is not hex)
        with self.assertRaises(ValidationError):
            Card(uid='A1B2C3D4G5', user=self.user).full_clean()

        # Invalid lengths (too short: 4 chars / 2 bytes)
        with self.assertRaises(ValidationError):
            Card(uid='A1B2', user=self.user).full_clean()

        # Invalid lengths (too long: 36 chars)
        with self.assertRaises(ValidationError):
            Card(uid='A' * 36, user=self.user).full_clean()

    def test_schedule_validation(self):
        # Valid schedule
        s1 = Schedule(
            name='Weekday Mornings',
            monday=True,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(12, 0)
        )
        s1.full_clean()  # Should not raise

        # End time before start time
        with self.assertRaises(ValidationError):
            Schedule(
                name='Invalid Time',
                monday=True,
                start_time=datetime.time(12, 0),
                end_time=datetime.time(9, 0)
            ).full_clean()

        # End time equal to start time
        with self.assertRaises(ValidationError):
            Schedule(
                name='Invalid Time',
                monday=True,
                start_time=datetime.time(9, 0),
                end_time=datetime.time(9, 0)
            ).full_clean()

        # No days checked
        with self.assertRaises(ValidationError):
            Schedule(
                name='No Days',
                start_time=datetime.time(9, 0),
                end_time=datetime.time(12, 0)
            ).full_clean()

        # Whitespace-only name
        with self.assertRaises(ValidationError):
            Schedule(
                name='   ',
                monday=True,
                start_time=datetime.time(9, 0),
                end_time=datetime.time(12, 0)
            ).full_clean()

    def test_access_rule_validation(self):
        device = Device.objects.create(device_id='esp32_rule_test', name='Rule Test Entrance')
        card = Card.objects.create(uid='E5D4C3B2', user=self.user)
        
        # Valid rule
        r1 = AccessRule(
            card=card,
            device=device,
            start_date=datetime.date(2026, 7, 1),
            end_date=datetime.date(2026, 7, 31)
        )
        r1.full_clean()  # Should not raise

        # End date before start date
        with self.assertRaises(ValidationError):
            AccessRule(
                card=card,
                device=device,
                start_date=datetime.date(2026, 7, 31),
                end_date=datetime.date(2026, 7, 1)
            ).full_clean()


class AccessVerifySerializerTests(TestCase):
    def test_serializer_validation_success(self):
        data = {
            'card_uid': 'a1:b2:c3:d4',
            'device_id': 'esp32_01'
        }
        serializer = AccessVerifySerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['card_uid'], 'A1B2C3D4')
        self.assertEqual(serializer.validated_data['device_id'], 'esp32_01')

    def test_serializer_validation_invalid_device(self):
        data = {
            'card_uid': 'a1:b2:c3:d4',
            'device_id': 'esp32 01'  # Invalid space
        }
        serializer = AccessVerifySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('device_id', serializer.errors)

    def test_serializer_validation_invalid_card(self):
        data = {
            'card_uid': 'a1:b2:c3:g4',  # Invalid hex char
            'device_id': 'esp32_01'
        }
        serializer = AccessVerifySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('card_uid', serializer.errors)


class AccessControlRBACTests(TestCase):
    def test_predefined_groups_created(self):
        self.assertTrue(Group.objects.filter(name='TT Security Auditor').exists())
        self.assertTrue(Group.objects.filter(name='TT HR Specialist').exists())
        self.assertTrue(Group.objects.filter(name='TT Technical Operator').exists())

    def test_tt_security_auditor_permissions(self):
        group = Group.objects.get(name='TT Security Auditor')
        permissions = group.permissions.all()
        codenames = {perm.codename for perm in permissions}

        # TT Security Auditor should have view permissions on all models/logs
        self.assertIn('view_accesslog', codenames)
        self.assertIn('view_logentry', codenames)
        self.assertIn('view_device', codenames)
        self.assertIn('view_card', codenames)
        self.assertIn('view_schedule', codenames)
        self.assertIn('view_accessrule', codenames)
        self.assertIn('view_user', codenames)

        # TT Security Auditor should not have any add, change, or delete permissions
        for codename in codenames:
            self.assertFalse(codename.startswith('add_'))
            self.assertFalse(codename.startswith('change_'))
            self.assertFalse(codename.startswith('delete_'))

    def test_tt_hr_specialist_permissions(self):
        group = Group.objects.get(name='TT HR Specialist')
        permissions = group.permissions.all()
        codenames = {perm.codename for perm in permissions}

        # TT HR Specialist should have full permissions on cards and users
        self.assertIn('add_card', codenames)
        self.assertIn('change_card', codenames)
        self.assertIn('delete_card', codenames)
        self.assertIn('view_card', codenames)

        self.assertIn('add_user', codenames)
        self.assertIn('change_user', codenames)
        self.assertIn('delete_user', codenames)
        self.assertIn('view_user', codenames)

        # TT HR Specialist should have view-only access to devices, schedules, access rules
        self.assertIn('view_device', codenames)
        self.assertNotIn('add_device', codenames)
        self.assertNotIn('change_device', codenames)
        self.assertNotIn('delete_device', codenames)

        self.assertIn('view_schedule', codenames)
        self.assertNotIn('add_schedule', codenames)
        self.assertNotIn('change_schedule', codenames)
        self.assertNotIn('delete_schedule', codenames)

        self.assertIn('view_accessrule', codenames)
        self.assertNotIn('add_accessrule', codenames)
        self.assertNotIn('change_accessrule', codenames)
        self.assertNotIn('delete_accessrule', codenames)

    def test_tt_technical_operator_permissions(self):
        group = Group.objects.get(name='TT Technical Operator')
        permissions = group.permissions.all()
        codenames = {perm.codename for perm in permissions}

        # TT Technical Operator should have full config rights on devices, schedules, and access rules
        self.assertIn('add_device', codenames)
        self.assertIn('change_device', codenames)
        self.assertIn('delete_device', codenames)
        self.assertIn('view_device', codenames)

        self.assertIn('add_schedule', codenames)
        self.assertIn('change_schedule', codenames)
        self.assertIn('delete_schedule', codenames)
        self.assertIn('view_schedule', codenames)

        self.assertIn('add_accessrule', codenames)
        self.assertIn('change_accessrule', codenames)
        self.assertIn('delete_accessrule', codenames)
        self.assertIn('view_accessrule', codenames)

        # TT Technical Operator should have view-only access to cards and users (no add/change/delete)
        self.assertIn('view_card', codenames)
        self.assertNotIn('add_card', codenames)
        self.assertNotIn('change_card', codenames)
        self.assertNotIn('delete_card', codenames)

        self.assertIn('view_user', codenames)
        self.assertNotIn('add_user', codenames)
        self.assertNotIn('change_user', codenames)
        self.assertNotIn('delete_user', codenames)

        # TT Technical Operator should not see access logs or admin activity log entries
        self.assertNotIn('view_accesslog', codenames)
        self.assertNotIn('view_logentry', codenames)




