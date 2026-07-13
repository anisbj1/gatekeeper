from django.test import TestCase, RequestFactory
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from apps.security_logs.admin import LogEntryAdmin

class LogEntryAdminTests(TestCase):
    def setUp(self):
        self.site = admin.AdminSite()
        self.admin_instance = LogEntryAdmin(LogEntry, self.site)
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            username='admin', 
            email='admin@example.com', 
            password='password'
        )

    def test_log_entry_is_registered(self):
        self.assertIn(LogEntry, admin.site._registry)
        self.assertIsInstance(admin.site._registry[LogEntry], LogEntryAdmin)

    def test_permissions_are_strictly_readonly(self):
        request = self.factory.get('/')
        request.user = self.superuser

        # Verify that add, change, and delete permissions return False even for a superuser
        self.assertFalse(self.admin_instance.has_add_permission(request))
        self.assertFalse(self.admin_instance.has_change_permission(request))
        self.assertFalse(self.admin_instance.has_delete_permission(request))

    def test_list_display_layout(self):
        expected_list_display = ('action_time', 'user', 'action_type', 'object_repr', 'change_message')
        self.assertEqual(self.admin_instance.list_display, expected_list_display)

    def test_search_fields(self):
        expected_search_fields = ('user__username', 'object_repr', 'change_message')
        self.assertEqual(self.admin_instance.search_fields, expected_search_fields)

    def test_list_filter(self):
        expected_list_filter = ('action_time', 'action_flag')
        self.assertEqual(self.admin_instance.list_filter, expected_list_filter)

    def test_action_type_labeling(self):
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(User)
        
        # Test addition flag
        entry_add = LogEntry(
            user=self.superuser,
            content_type=content_type,
            object_id=str(self.superuser.pk),
            object_repr=repr(self.superuser),
            action_flag=1, # ADDITION
            change_message="Added user"
        )
        self.assertEqual(self.admin_instance.action_type(entry_add), "Addition")

        # Test change flag
        entry_change = LogEntry(
            user=self.superuser,
            content_type=content_type,
            object_id=str(self.superuser.pk),
            object_repr=repr(self.superuser),
            action_flag=2, # CHANGE
            change_message="Changed user name"
        )
        self.assertEqual(self.admin_instance.action_type(entry_change), "Change")

        # Test deletion flag
        entry_delete = LogEntry(
            user=self.superuser,
            content_type=content_type,
            object_id=str(self.superuser.pk),
            object_repr=repr(self.superuser),
            action_flag=3, # DELETION
            change_message="Deleted user"
        )
        self.assertEqual(self.admin_instance.action_type(entry_delete), "Deletion")

        # Test unknown flag
        entry_unknown = LogEntry(
            user=self.superuser,
            content_type=content_type,
            object_id=str(self.superuser.pk),
            object_repr=repr(self.superuser),
            action_flag=99,
            change_message="Some other action"
        )
        self.assertEqual(self.admin_instance.action_type(entry_unknown), "Unknown")
