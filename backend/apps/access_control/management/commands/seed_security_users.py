from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from apps.access_control.signals import create_predefined_groups

class Command(BaseCommand):
    help = 'Seeds standard testing users for Security, RBAC and Session testing'

    def handle(self, *args, **options):
        # 1. Ensure predefined groups exist
        create_predefined_groups(sender=None)

        # 2. Create or update Super Admin
        super_admin, _ = User.objects.get_or_create(username='superadmin')
        super_admin.set_password('Admin@123456')
        super_admin.is_staff = True
        super_admin.is_superuser = True
        super_admin.is_active = True
        super_admin.first_name = 'Super'
        super_admin.last_name = 'Administrator'
        super_admin.email = 'superadmin@iotaccess.local'
        super_admin.save()

        # 3. Create or update Operational Admin
        op_admin, _ = User.objects.get_or_create(username='operator')
        op_admin.set_password('Operator@123456')
        op_admin.is_staff = True
        op_admin.is_superuser = False
        op_admin.is_active = True
        op_admin.first_name = 'Operational'
        op_admin.last_name = 'Operator'
        op_admin.email = 'operator@iotaccess.local'
        op_admin.save()
        op_group = Group.objects.get(name='Operational Admin')
        op_admin.groups.set([op_group])

        # 4. Create or update Standard Employee
        employee, _ = User.objects.get_or_create(username='employee')
        employee.set_password('Employee@123456')
        employee.is_staff = False
        employee.is_superuser = False
        employee.is_active = True
        employee.first_name = 'Standard'
        employee.last_name = 'Employee'
        employee.email = 'employee@iotaccess.local'
        employee.save()

        self.stdout.write(self.style.SUCCESS('Successfully seeded security test accounts:'))
        self.stdout.write('  1. Super Admin: username="superadmin", password="Admin@123456"')
        self.stdout.write('  2. Operational Admin: username="operator", password="Operator@123456"')
        self.stdout.write('  3. Standard Employee: username="employee", password="Employee@123456"')
