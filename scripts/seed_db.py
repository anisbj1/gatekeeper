#!/usr/bin/env python3
import os
import sys
import django
import datetime

# Add backend to python path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend'))
sys.path.append(backend_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from apps.access_control.models import Device, Card, Schedule, AccessRule

def seed():
    print("============================================")
    print("Seeding SQLite local database for Demo...")
    print("============================================")
    
    # 1. Clean previous data
    print("Cleaning database tables...")
    AccessRule.objects.all().delete()
    Schedule.objects.all().delete()
    Card.objects.all().delete()
    User.objects.filter(username__in=['anis', 'anis1', 'anis2', 'anis3', 'anis4', 'visitor', 'expired_guest']).delete()
    
    # 2. Create device 'esp32_01'
    device, created = Device.objects.get_or_create(
        device_id='esp32_01',
        defaults={'name': 'Main Lab Entrance', 'is_active': True}
    )
    print(f"Registered Device: '{device.device_id}'")
        
    # 3. Create reusable schedules
    # Schedule A: Workdays 24h (Mon-Fri, whole day)
    sched_workdays_24h = Schedule.objects.create(
        name="Workdays 24h",
        monday=True, tuesday=True, wednesday=True, thursday=True, friday=True,
        saturday=False, sunday=False,
        start_time=datetime.time(0, 0, 0),
        end_time=datetime.time(23, 59, 59)
    )
    print("Created schedule: 'Workdays 24h'")

    # Schedule B: Workdays 9-5 (Mon-Fri, 9:00 AM - 5:00 PM)
    sched_workdays_9_5 = Schedule.objects.create(
        name="Workdays 9-5",
        monday=True, tuesday=True, wednesday=True, thursday=True, friday=True,
        saturday=False, sunday=False,
        start_time=datetime.time(9, 0, 0),
        end_time=datetime.time(17, 0, 0)
    )
    print("Created schedule: 'Workdays 9-5'")

    # 4. User 1: anis1 (ACCESS GRANTED)
    user1 = User.objects.create_user(username='anis1', password='password')
    user1.first_name = "Anis"
    user1.last_name = "One"
    user1.save()
    card1 = Card.objects.create(uid='E9B3A2C8', user=user1, is_active=True)
    AccessRule.objects.create(
        card=card1,
        device=device,
        schedule=sched_workdays_24h,
        start_date=datetime.date(2026, 7, 1),
        end_date=datetime.date(2026, 7, 31),
        is_active=True
    )
    print(f"Created anis1 (UID: {card1.uid}) -> Authorized (Workdays 24h in July 2026)")

    # 5. User 2: anis2 (REJECTED: No Access Rule)
    user2 = User.objects.create_user(username='anis2', password='password')
    user2.first_name = "Anis"
    user2.last_name = "Two"
    user2.save()
    card2 = Card.objects.create(uid='A2B2C2D2', user=user2, is_active=True)
    # No access rules linked
    print(f"Created anis2 (UID: {card2.uid}) -> Rejected: No Access Rule")

    # 6. User 3: anis3 (REJECTED: Date Exceeded)
    user3 = User.objects.create_user(username='anis3', password='password')
    user3.first_name = "Anis"
    user3.last_name = "Three"
    user3.save()
    card3 = Card.objects.create(uid='A3B3C3D3', user=user3, is_active=True)
    AccessRule.objects.create(
        card=card3,
        device=device,
        schedule=sched_workdays_24h,
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 30), # Expired relative to July 2026
        is_active=True
    )
    print(f"Created anis3 (UID: {card3.uid}) -> Rejected: Date Exceeded (Expired in June)")

    # 7. User 4: anis4 (REJECTED: Schedule Restricted - Scan at 04:59 early morning is outside 9-5)
    user4 = User.objects.create_user(username='anis4', password='password')
    user4.first_name = "Anis"
    user4.last_name = "Four"
    user4.save()
    card4 = Card.objects.create(uid='A4B4C4D4', user=user4, is_active=True)
    AccessRule.objects.create(
        card=card4,
        device=device,
        schedule=sched_workdays_9_5,
        start_date=datetime.date(2026, 7, 1),
        end_date=datetime.date(2026, 7, 31),
        is_active=True
    )
    print(f"Created anis4 (UID: {card4.uid}) -> Rejected: Schedule Restricted (Workdays 9-5 in July)")

    print("\nDatabase seeding finished successfully.")

if __name__ == '__main__':
    seed()
