from django.db.models.signals import post_migrate
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

def create_predefined_groups(sender, **kwargs):
    """
    Automatically creates the predefined groups 'Security Operator' and 'HR Manager'
    and assigns their respective permissions upon migration.
    """
    # Clean up old generic and CNOC groups
    Group.objects.filter(name__in=[
        'Security Operator', 'HR Manager',
        'CNOC Supervisor', 'CNOC Technician', 'CNOC Security Officer'
    ]).delete()

    roles = {
        'TT Security Auditor': [
            # security_logs
            ('view_accesslog', 'security_logs', 'accesslog'),
            # admin
            ('view_logentry', 'admin', 'logentry'),
            # access_control
            ('view_device', 'access_control', 'device'),
            ('view_card', 'access_control', 'card'),
            ('view_schedule', 'access_control', 'schedule'),
            ('view_accessrule', 'access_control', 'accessrule'),
            # auth (User)
            ('view_user', 'auth', 'user'),
        ],
        'TT HR Specialist': [
            # access_control
            ('view_device', 'access_control', 'device'),
            ('view_card', 'access_control', 'card'),
            ('add_card', 'access_control', 'card'),
            ('change_card', 'access_control', 'card'),
            ('delete_card', 'access_control', 'card'),
            ('view_schedule', 'access_control', 'schedule'),
            ('view_accessrule', 'access_control', 'accessrule'),
            # auth (User)
            ('view_user', 'auth', 'user'),
            ('add_user', 'auth', 'user'),
            ('change_user', 'auth', 'user'),
            ('delete_user', 'auth', 'user'),
        ],
        'TT Technical Operator': [
            # access_control
            ('view_device', 'access_control', 'device'),
            ('add_device', 'access_control', 'device'),
            ('change_device', 'access_control', 'device'),
            ('delete_device', 'access_control', 'device'),
            ('view_schedule', 'access_control', 'schedule'),
            ('add_schedule', 'access_control', 'schedule'),
            ('change_schedule', 'access_control', 'schedule'),
            ('delete_schedule', 'access_control', 'schedule'),
            ('view_accessrule', 'access_control', 'accessrule'),
            ('add_accessrule', 'access_control', 'accessrule'),
            ('change_accessrule', 'access_control', 'accessrule'),
            ('delete_accessrule', 'access_control', 'accessrule'),
            ('view_card', 'access_control', 'card'),
            # auth (User)
            ('view_user', 'auth', 'user'),
        ]
    }

    for role_name, permissions in roles.items():
        group, created = Group.objects.get_or_create(name=role_name)
        
        perms_to_add = []
        for codename, app_label, model_name in permissions:
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model_name)
                perm = Permission.objects.get(codename=codename, content_type=ct)
                perms_to_add.append(perm)
            except (ContentType.DoesNotExist, Permission.DoesNotExist):
                # Safeguard in case certain permissions do not exist yet during testing or initial migrations
                pass
        
        # Sync the permissions for the group
        group.permissions.set(perms_to_add)


