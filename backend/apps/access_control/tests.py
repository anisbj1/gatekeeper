import datetime
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from django.contrib.auth.models import User
from apps.access_control.models import Device, Card, Schedule, AccessRule
from apps.access_control.services import AccessValidationService
from apps.security_logs.models import AccessLog

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
            day_of_week=1,  # Monday
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
