# IoT Smart Access Control - V2 (Access Control)

This repository hosts V2 of the Smart Access Control System, integrating an ESP32 node simulating in Wokwi and a Django REST Backend with **rule-based access control**.

---

## 1. Project Architecture

The system is designed around a **clean separation of concerns**:
*   **ESP32 Controller (I/O Layer):** A stateless physical device. It polls the MFRC522 RFID reader, prints status updates to the ILI9341 screen, and makes REST HTTP requests. It contains no access rules, schedules, or user details.
*   **Django REST Framework (API Layer):** Exposes `/api/v1/access/verify/` validating incoming JSON payloads.
*   **Django Backend (Decision Layer):** Contains the SQLite database and executes business logic via service layers (`AccessValidationService` and `AuditLoggingService`).
*   **Access Control Module:** Configurable rules linking cards/users to devices with schedule and date window constraints.

---

## 2. Key Architecture Design Rules

1.  **Strict I/O Decoupling:** The ESP32 acts only as a remote terminal. Django evaluates all access decisions and returns simple command actions (`unlock` or `keep_locked`).
2.  **Card UID Normalization:** RFID card UIDs are automatically normalized (spaces and colons stripped, capitalized) inside the `Card` data model's `save()` method. This prevents mismatches (e.g. database storing `11:22:33:44` while ESP32 scans `11223344`).
3.  **Python 3.14 Compatibility:** Uses **Django 6.0.7** to prevent `AttributeError: 'super' object has no attribute 'dicts'` crashes that occur in older Django versions due to stricter `super()` proxy behavior in Python 3.14.
4.  **Decoupled Configuration:** Wi-Fi credentials and API URLs are declared in `config.h` to allow seamless swapping between local Wokwi simulation and hardware deployment.

---

## 3. Directory Layout

```text
projet/
├── .agents/                          # Custom AI rules & configurations
│   └── AGENTS.md                     # Global coordination rules for AI skills
├── docs/                             # Architecture and API specs
│   ├── architecture.md               # Visual sequence and block diagrams
│   └── api_specs.yaml                # OpenAPI REST API definitions
├── simulation/                       # Wokwi simulator config and schema
│   ├── wokwi.toml                    # Relative paths to PlatformIO build binaries
│   └── diagram.json                  # Schematic wiring (ESP32 + MFRC522 + ILI9341 Screen)
├── firmware/                         # Embedded C++ Firmware
│   └── controller/
│       ├── platformio.ini            # PlatformIO dependencies (Adafruit GFX, ILI9341, MFRC522)
│       ├── include/                  # Pin configurations (pins.h) and network settings (config.h)
│       └── src/main.cpp              # Non-blocking main state machine
├── backend/                          # Django REST Server
│   ├── requirements.txt              # Python packages (Django 6.0.7, DRF, pillow)
│   ├── manage.py                     # Entry point admin CLI script
│   ├── core/                         # Global URL router and settings configuration
│   └── apps/                         # Modular Django applications
│       ├── access_control/           # Device, Card, Schedule, AccessRule models & validation
│       │   ├── models.py             # Data models with UID normalization & validation
│       │   ├── services.py           # AccessValidationService (core decision engine)
│       │   ├── admin.py              # Admin configuration for all models
│       │   ├── tests.py              # 10 test cases covering all access scenarios
│       │   └── migrations/           # Database schema migrations
│       └── security_logs/            # Audit history logs
└── scripts/                          # Seeder and utility helpers
    └── seed_db.py                    # SQLite database seeder
```

---

## 3. V2 Features - Access Control Module

### New Data Models
- **Schedule:** Define time-based access windows (day of week + start/end time)
- **AccessRule:** Link cards/users to devices with optional schedule and date constraints

### Validation Logic
The `AccessValidationService` evaluates scans through a 5-step pipeline:
1. **Device Check** - Is the device registered and active?
2. **Card Check** - Is the card active and is the user active?
3. **Access Rule Lookup** - Are there any rules for this card/user + device?
4. **Date Window** - Is the current date within the rule's validity period?
5. **Schedule Check** - Does the current day/time match the schedule?

### Key Features
- **UID Normalization:** Automatic stripping of colons/spaces, uppercasing
- **24/7 Access:** Null schedule grants round-the-clock access
- **Multiple Rules:** System evaluates all rules; grants access if ANY rule is valid
- **Priority Handling:** Inactive devices are checked first, before card/user validation
- **Audit Logging:** Every scan attempt (authorized or denied) is logged with user details

### Documentation
- [Access Control Module Docs](docs/access_control.md) - Full specification, models, API, tests
- [Architecture Diagrams](docs/architecture.md) - Visual sequence and block diagrams
- [API Specifications](docs/api_specs.yaml) - OpenAPI REST API definitions

---

## 4. Run & Verify Instructions

### A. Run the Django REST Backend
1.  Initialize your python environment:
    ```bash
    python -m venv venv
    # Windows:
    .\venv\Scripts\Activate.ps1
    # Linux/Mac:
    source venv/bin/activate
    ```
2.  Install dependencies:
    ```bash
    pip install -r backend/requirements.txt
    ```
3.  Prepare migrations and SQLite database:
    ```bash
    python backend/manage.py makemigrations access_control security_logs
    python backend/manage.py migrate
    ```
4.  Create your Django Administrator account (Superuser):
    ```bash
    python backend/manage.py createsuperuser
    ```
5.  Seed test devices, users, and card badges:
    ```bash
    python scripts/seed_db.py
    ```
6.  Start Django (listening on all interfaces so Wokwi can connect):
    ```bash
    python backend/manage.py runserver 0.0.0.0:8000
    ```

### B. Access the Admin Panel
*   Navigate to: `http://127.0.0.1:8000/admin/`
*   Log in using your superuser credentials.
*   You can manage devices, cards, and view access audit logs in real time.

### C. Compile the Firmware (ESP32)
In a new terminal window:
1.  Activate your virtual environment (`.\venv\Scripts\Activate.ps1`).
2.  Compile the firmware using PlatformIO:
    ```bash
    .\venv\Scripts\pio.exe run -d firmware/controller
    ```

### D. Run the Simulation (Wokwi GUI)
1.  Open `simulation/diagram.json` in VS Code.
2.  Press `F1`, choose **Wokwi: Start Simulator**.
3.  Click the green **Play** button in the Wokwi panel.
4.  Switch the active terminal to **`Wokwi Terminal`** (using the terminal dropdown in the bottom right of VS Code) to view connection logs.
5.  Select **Green Card** (UID: `11:22:33:44`) or **Blue Card** (UID: `01:02:03:04`) and click **`TAP`** to simulate scanning.
6.  The display will change colors (Green for access granted, Red for denied), and the event will populate in the Django Admin audit log list.

### E. Run Tests
```bash
python backend/manage.py test access_control
```
Tests cover: no access rule, authorized card/user rules, date exceeded (past/future), schedule restricted (day/time), 24/7 access, multiple rules, and device inactive priority.
