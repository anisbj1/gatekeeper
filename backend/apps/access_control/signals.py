from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from apps.security_logs.services import AdminAuditService

def get_client_ip(request):
    if not request:
        return '127.0.0.1'
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or '127.0.0.1'


def create_predefined_groups(sender, **kwargs):
    """
    Automatically creates the predefined groups 'Operational Admin', 'TT Security Auditor',
    'TT HR Specialist', and 'TT Technical Operator', assigning their respective permissions upon migration.
    """
    roles = {
        'Operational Admin': [
            # security_logs
            ('view_accesslog', 'security_logs', 'accesslog'),
            # access_control
            ('view_device', 'access_control', 'device'),
            ('view_card', 'access_control', 'card'),
            ('add_card', 'access_control', 'card'),
            ('change_card', 'access_control', 'card'),
            ('delete_card', 'access_control', 'card'),
            ('view_schedule', 'access_control', 'schedule'),
            ('add_schedule', 'access_control', 'schedule'),
            ('change_schedule', 'access_control', 'schedule'),
            ('delete_schedule', 'access_control', 'schedule'),
            ('view_accessrule', 'access_control', 'accessrule'),
            ('add_accessrule', 'access_control', 'accessrule'),
            ('change_accessrule', 'access_control', 'accessrule'),
            ('delete_accessrule', 'access_control', 'accessrule'),
            # auth (User view only for operational admins)
            ('view_user', 'auth', 'user'),
        ],
        'TT Security Auditor': [
            ('view_accesslog', 'security_logs', 'accesslog'),
            ('view_adminauditlog', 'security_logs', 'adminauditlog'),
            ('view_logentry', 'admin', 'logentry'),
            ('view_device', 'access_control', 'device'),
            ('view_card', 'access_control', 'card'),
            ('view_schedule', 'access_control', 'schedule'),
            ('view_accessrule', 'access_control', 'accessrule'),
            ('view_user', 'auth', 'user'),
        ],

        'TT HR Specialist': [
            ('view_device', 'access_control', 'device'),
            ('view_card', 'access_control', 'card'),
            ('add_card', 'access_control', 'card'),
            ('change_card', 'access_control', 'card'),
            ('delete_card', 'access_control', 'card'),
            ('view_schedule', 'access_control', 'schedule'),
            ('view_accessrule', 'access_control', 'accessrule'),
            ('view_user', 'auth', 'user'),
            ('add_user', 'auth', 'user'),
            ('change_user', 'auth', 'user'),
            ('delete_user', 'auth', 'user'),
        ],
        'TT Technical Operator': [
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


# Security Audit Signals
@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    AdminAuditService.log_event(
        event_type='LOGIN_SUCCESS',
        actor=user.username,
        target_user=user.username,
        ip_address=get_client_ip(request),
        details=f"User '{user.username}' successfully authenticated."
    )


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    username = user.username if user else 'Anonymous'
    AdminAuditService.log_event(
        event_type='LOGOUT',
        actor=username,
        target_user=username,
        ip_address=get_client_ip(request),
        details=f"User '{username}' logged out."
    )


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    attempted_username = credentials.get('username') or 'Unknown'
    AdminAuditService.log_event(
        event_type='LOGIN_FAILED',
        actor='Anonymous',
        target_user=attempted_username,
        ip_address=get_client_ip(request),
        details=f"Failed login attempt for username '{attempted_username}'."
    )


# Axes lockout signal
try:
    from axes.signals import user_locked_out

    @receiver(user_locked_out)
    def on_user_locked_out(sender, request, username, ip_address, **kwargs):
        AdminAuditService.log_event(
            event_type='IP_BLOCKED',
            actor='AxesSecurity',
            target_user=username or 'N/A',
            ip_address=ip_address,
            details=f"IP address '{ip_address}' blocked due to exceeding failed login attempts limit."
        )
except ImportError:
    pass



