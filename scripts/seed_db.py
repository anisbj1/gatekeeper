#!/usr/bin/env python3
import os
import sys
import django

# Add backend to python path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend'))
sys.path.append(backend_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from apps.access_control.models import Device, Card

def seed():
    print("============================================")
    print("Seeding SQLite local database for V1...")
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

    print("\nSeeding finished successfully.")

if __name__ == '__main__':
    seed()
