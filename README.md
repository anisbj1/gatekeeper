# IoT Smart Access Control

Smart door access control — **ESP32 nodes at the gate, Django REST doing the thinking.**

Card scans (**MFRC522 RFID**) and face snapshots (**ESP32-CAM**) get forwarded to the backend, which runs the card through a rule engine and answers with a single command: `unlock` or `keep_locked`. The firmware stays a stateless terminal — no business logic on the silicon.

## Architecture

```text
 ESP32 Controller       ESP32-CAM
 (RFID + TFT UI)        (face snap)
       │                      │
       └────────┬─────────────┘
                │ HTTP /api/v1/access/verify/
                ▼
        Django REST Backend
        rule engine · SQLite · audit logs
```

## Features

- **Rule-based access control** — device → card → user → schedule → date window
- **24/7 & multi-rule support** — access granted if any rule passes
- **Face recognition** — enrollment + verification (FaceNet · PyTorch · OpenCV)
- **Full audit trail** — every scan, authorized or not, logged with details
- **Web dashboard** — light/dark UI for devices, cards, rules, logs
- **Brute-force protection** — API token auth + login throttling
- **Wokwi simulation** — run the whole loop without real hardware

## Stack

| Layer      | Tech                                                        |
| ---------- | ----------------------------------------------------------- |
| Firmware   | C++ · PlatformIO · ESP32 · MFRC522 · ILI9341 · ArduinoJson  |
| Backend    | Django 6 · Django REST Framework · SQLite · FaceNet · OpenCV |
| Simulation | Wokwi                                                       |

## Quickstart

```bash
# backend
pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py createsuperuser
python scripts/seed_db.py
python backend/manage.py runserver 0.0.0.0:8000
```

Firmware (simulated, no hardware):

1. Open `simulation/diagram.json` in VS Code → `F1` → **Wokwi: Start Simulator**
2. Compile: `pio run -d firmware/controller` (PlatformIO)
3. Tap the Green (UID `11:22:33:44`) or Blue (UID `01:02:03:04`) card — screen goes green/red, event lands in the audit log

## Tests

```bash
python backend/manage.py test access_control
```

## Docs

- [Architecture](docs/architecture.md) · [Access control rules](docs/access_control.md)
- [API spec](docs/api_specs.yaml) · [Security protocol](docs/security_protocol.md) · [Wiring](docs/physical_wiring.md)