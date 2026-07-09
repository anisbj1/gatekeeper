# IoT Smart Access Control - Prototype V1

This repository hosts the prototype V1 of the Smart Access Control System, integrating an ESP32 node simulating in Wokwi and a Django REST Backend.

---

## 1. Project Architecture

The system is designed around a **clean separation of concerns**:
*   **ESP32 Controller (I/O Layer):** A stateless physical device. It polls the MFRC522 RFID reader, prints status updates to the ILI9341 screen, and makes REST HTTP requests. It contains no access rules, schedules, or user details.
*   **Django REST Framework (API Layer):** Exposes `/api/v1/access/verify/` validating incoming JSON payloads.
*   **Django Backend (Decision Layer):** Contains the SQLite database and executes business logic via service layers (`AccessValidationService` and `AuditLoggingService`).

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
│       ├── access_control/           # Device and Card database models & validation views
│       └── security_logs/            # Audit history logs
└── scripts/                          # Seeder and utility helpers
    └── seed_db.py                    # SQLite database seeder
```

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
