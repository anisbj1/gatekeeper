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
    print("Seeding SQLite local database for V2...")
    print("============================================")
    
    # 1. Create standard active user
    user, created = User.objects.get_or_create(username='anis')
    if created:
        user.set_password('password')
        user.first_name = 'Anis'
        user.last_name = 'Stage'
        user.save()
        print("Created User: 'anis'")
    else:
        print("User 'anis' already exists.")
        
    # 2. Create device 'esp32_01'
    device, created = Device.objects.get_or_create(
        device_id='esp32_01',
        defaults={'name': 'Main Lab Entrance', 'is_active': True}
    )
    if created:
        print(f"Registered Device: '{device.device_id}'")
    else:
        print(f"Device '{device.device_id}' already registered.")
        
    # 3. Create active card with UID 'E9B3A2C8' (Standard mock scan UID)
    card1, created = Card.objects.get_or_create(
        uid='E9B3A2C8',
        defaults={'user': user, 'is_active': True}
    )
    if created:
        print(f"Registered Card: '{card1.uid}' assigned to '{user.username}'")
    else:
        print(f"Card '{card1.uid}' already active.")
        
    # 4. Create inactive card with UID 'B8C7D6F5' (For access rejection verification)
    card2, created = Card.objects.get_or_create(
        uid='B8C7D6F5',
        defaults={'user': user, 'is_active': False}
    )
    if created:
        print(f"Registered Blocked Card: '{card2.uid}' assigned to '{user.username}'")
    else:
        print(f"Blocked Card '{card2.uid}' already exists.")

    # 5. Create Workday schedules (Monday to Friday, 9:00 AM - 5:00 PM)
    print("Seeding schedules and access rules for 'anis'...")
    workdays_schedules = []
    for day_num, day_name in [(1, 'Monday'), (2, 'Tuesday'), (3, 'Wednesday'), (4, 'Thursday'), (5, 'Friday')]:
        sched, created_sched = Schedule.objects.get_or_create(
            name=f"Workday 9-5 ({day_name})",
            day_of_week=day_num,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(17, 0)
        )
        workdays_schedules.append(sched)
        
        # Link card1 to device for each workday schedule
        rule, created_rule = AccessRule.objects.get_or_create(
            card=card1,
            device=device,
            schedule=sched,
            defaults={'is_active': True}
        )
        if created_rule:
            print(f"  Created active rule for '{card1.uid}' on {day_name}")

    # 6. Create a guest visitor user with valid July 2026 date range and 24/7 access
    visitor_user, created_vis = User.objects.get_or_create(username='visitor')
    if created_vis:
        visitor_user.set_password('password')
        visitor_user.first_name = 'Visitor'
        visitor_user.last_name = 'Guest'
        visitor_user.save()
        print("Created User: 'visitor'")
        
    visitor_card, created_vis_card = Card.objects.get_or_create(
        uid='C1D2E3F4',
        defaults={'user': visitor_user, 'is_active': True}
    )
    if created_vis_card:
        print(f"Registered Visitor Card: '{visitor_card.uid}' assigned to '{visitor_user.username}'")
        
    vis_rule, created_vis_rule = AccessRule.objects.get_or_create(
        card=visitor_card,
        device=device,
        schedule=None,
        start_date=datetime.date(2026, 7, 1),
        end_date=datetime.date(2026, 7, 31),
        defaults={'is_active': True}
    )
    if created_vis_rule:
        print(f"  Created visitor rule for '{visitor_card.uid}' (Valid: July 1 to July 31, 2026)")

    # 7. Create an expired guest visitor
    expired_user, created_exp = User.objects.get_or_create(username='expired_guest')
    if created_exp:
        expired_user.set_password('password')
        expired_user.first_name = 'Expired'
        expired_user.last_name = 'Guest'
        expired_user.save()
        print("Created User: 'expired_guest'")
        
    expired_card, created_exp_card = Card.objects.get_or_create(
        uid='F5E4D3C2',
        defaults={'user': expired_user, 'is_active': True}
    )
    if created_exp_card:
        print(f"Registered Expired Visitor Card: '{expired_card.uid}' assigned to '{expired_user.username}'")
        
    exp_rule, created_exp_rule = AccessRule.objects.get_or_create(
        card=expired_card,
        device=device,
        schedule=None,
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 30),
        defaults={'is_active': True}
    )
    if created_exp_rule:
        print(f"  Created expired rule for '{expired_card.uid}' (Expired: June 30, 2026)")

    print("\nSeeding finished successfully.")

if __name__ == '__main__':
    seed()

