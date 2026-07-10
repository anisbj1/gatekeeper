# Access Control Module - V2 Documentation

## Overview

The Access Control module implements a rule-based authorization system for IoT devices. It evaluates RFID card scans against configurable access rules, schedules, and date windows to grant or deny entry.

---

## Data Models

### Device

Represents an ESP32 controller node.

| Field       | Type         | Description                        |
|-------------|--------------|------------------------------------|
| `device_id` | CharField    | Unique identifier (e.g. `esp32_01`) |
| `name`      | CharField    | Human-readable name                |
| `is_active` | BooleanField | Whether the device is operational  |

### Card

RFID card badge linked to a Django User.

| Field       | Type         | Description                        |
|-------------|--------------|------------------------------------|
| `uid`       | CharField    | Normalized UID (uppercase, no separators) |
| `user`      | ForeignKey   | Associated Django User             |
| `is_active` | BooleanField | Whether the card is blocked        |

**UID Normalization:** On `save()`, colons and spaces are stripped and the UID is uppercased to prevent mismatches between ESP32 scans and database records.

### Schedule

Time-based access window for a specific day.

| Field         | Type       | Description                          |
|---------------|------------|--------------------------------------|
| `name`        | CharField  | Label (e.g. "Workday 9-5")          |
| `day_of_week` | IntegerField | 1=Monday through 7=Sunday         |
| `start_time`  | TimeField  | Window open time                     |
| `end_time`    | TimeField  | Window close time                    |

### AccessRule

Core authorization rule linking a card/user to a device with optional constraints.

| Field       | Type         | Description                          |
|-------------|--------------|--------------------------------------|
| `card`      | ForeignKey   | Specific card (nullable)             |
| `user`      | ForeignKey   | Specific user (nullable)             |
| `device`    | ForeignKey   | Target device (required)             |
| `schedule`  | ForeignKey   | Time constraint (null = 24/7 access) |
| `start_date`| DateField    | Validity window start (nullable)     |
| `end_date`  | DateField    | Validity window end (nullable)       |
| `is_active` | BooleanField | Whether the rule is enforced         |

**Constraint:** Each rule must link to either a `card` OR a `user`, never both and never neither.

---

## Validation Flow

When an ESP32 sends a scan request to `POST /api/v1/access/verify/`, the `AccessValidationService.validate_scan()` method executes:

```
1. Device Check
   └─ Device exists and is_active?
       ├─ NO → log + return "Device Inactive" / "Unknown Device"
       └─ YES ↓

2. Card Check
   └─ Card exists, is_active, and user.is_active?
       ├─ NO → log + return "Card Blocked" / "User Inactive" / "Access Denied"
       └─ YES ↓

3. Access Rule Lookup
   └─ Any active rules for this card/user + device?
       ├─ NO → log + return "No Access Rule"
       └─ YES ↓

4. Per-Rule Evaluation (loop)
   ├─ Date Window Check
   │   └─ current_date within [start_date, end_date]?
   │       ├─ NO → skip rule
   │       └─ YES ↓
   ├─ Schedule Check
   │   └─ current_day matches schedule.day_of_week AND current_time within [start_time, end_time]?
   │       ├─ NO → mark schedule_restricted, skip rule
   │       └─ YES ↓
   └─ AUTHORIZED → log + return "unlock"

5. No Valid Rule Found
   └─ log + return "Schedule Restricted" or "Date Exceeded"
```

---

## API Endpoint

### POST `/api/v1/access/verify/`

**Request Body:**
```json
{
  "card_uid": "E9B3A2C8",
  "device_id": "esp32_01"
}
```

**Success Response (200):**
```json
{
  "authorized": true,
  "message": "Welcome, Anis Stage",
  "action": "unlock"
}
```

**Denial Response (200):**
```json
{
  "authorized": false,
  "message": "Schedule Restricted",
  "action": "keep_locked"
}
```

---

## Test Coverage

The test suite (`backend/apps/access_control/tests.py`) covers:

| Test Case                              | Scenario                                    |
|----------------------------------------|---------------------------------------------|
| `test_validate_scan_no_access_rule`    | Card exists but no rules → denied           |
| `test_validate_scan_authorized_card_rule` | Rule linked to card, within schedule → granted |
| `test_validate_scan_authorized_user_rule` | Rule linked to user, within schedule → granted |
| `test_validate_scan_date_exceeded_past` | Rule start_date in future → denied          |
| `test_validate_scan_date_exceeded_future` | Rule end_date in past → denied             |
| `test_validate_scan_schedule_restricted_day` | Wrong day of week → denied             |
| `test_validate_scan_schedule_restricted_time` | Outside time window → denied           |
| `test_validate_scan_unrestricted_schedule_24_7` | Null schedule → granted (24/7)      |
| `test_validate_scan_multiple_rules_one_valid` | One expired rule, one valid → granted  |
| `test_validate_scan_device_inactive_priority` | Inactive device → denied (priority)    |

Run tests:
```bash
python backend/manage.py test access_control
```

---

## Seed Data

The seeder (`scripts/seed_db.py`) creates:

| User            | Card UID   | Device     | Rule Type                     |
|-----------------|------------|------------|-------------------------------|
| `anis`          | `E9B3A2C8` | `esp32_01` | Mon-Fri 9:00-17:00            |
| `anis`          | `B8C7D6F5` | `esp32_01` | Blocked card (is_active=False)|
| `visitor`       | `C1D2E3F4` | `esp32_01` | 24/7, valid July 1-31, 2026   |
| `expired_guest` | `F5E4D3C2` | `esp32_01` | 24/7, expired June 30, 2026   |

---

## Django Admin

All models are registered with custom `ModelAdmin` classes for easy management:

- **Device:** Filter by active status, search by device_id/name
- **Card:** Filter by active status, search by UID/username
- **Schedule:** Filter by day_of_week, search by name
- **AccessRule:** Filter by active/device/schedule, search by user/card/device

Access the admin at: `http://127.0.0.1:8000/admin/`
