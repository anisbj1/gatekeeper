# Project Rules & AI Agent Orchestration (AGENTS.md)

Welcome to the IoT Smart Access Control workspace. This file establishes the core rules, coding styles, and coordination processes that all developer agents must adhere to when interacting with this repository.

---

## 1. Project Context
*   **Target hardware:** ESP32 (Main controller with ST7735 screen, MFRC522 RFID reader) & ESP32-CAM (Camera node).
*   **Target backend:** Django REST Framework with SQLite.
*   **Simulation environment:** Wokwi.
*   **Build system:** PlatformIO.

---

## 2. Global AI Collaboration Rules
1.  **Contract-Driven Development:** Any changes to the API payload, endpoint parameters, or JSON formats must be updated and approved first in `docs/api_specs.yaml` before changing backend or firmware code.
2.  **No Unverified Hardware Configurations:** If an agent updates a GPIO assignment in firmware, it **must** verify that the pin mapping matches `docs/physical_wiring.md` and is updated in `simulation/diagram.json` and `simulation/diagram_cam.json`.
3.  **Strict Modularization:** Do not write unified, monolithic files. Keep firmware drivers separate from main loop code, and keep Django apps modular.
4.  **No Silent Overwrites:** Before overwriting or renaming configuration files (`platformio.ini`, `manage.py`, `wokwi.toml`), agents must review current dependencies to prevent breaking setups.

---

## 3. Specialized Skill Registry

*   **`iot_firmware`**: Responsible for firmware under `firmware/`. Focuses on C++, non-blocking asynchronous loops, hardware interrupts, and low-level SPI communication.
*   **`django_backend`**: Responsible for backend under `backend/`. Focuses on REST APIs, SQLite models, security logs, and camera gateways.
*   **`wokwi_simulation`**: Responsible for configuring components, connections, and coordinates in `simulation/diagram.json` and `simulation/diagram_cam.json`.
*   **`system_integrator`**: Validates the end-to-end functionality, checks code compliance against specifications, and manages testing scripts in `scripts/`.
