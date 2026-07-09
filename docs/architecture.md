# System Architecture Overview

This document describes the high-level architecture of the Smart IoT Access Control System.

## Architecture Topology
The system consists of two physical nodes communicating with a central Django backend over local Wi-Fi:

1.  **ESP32 Main Controller:**
    *   **Peripherals:** MFRC522 (RFID Reader), ST7735 (TFT Color Display), Relay/Solenoid Valve (Door latch controller).
    *   **Function:** Reads RFID cards, queries backend API, updates display UI, opens/locks the door.
2.  **ESP32-CAM Node:**
    *   **Peripherals:** Camera sensor, external PSRAM.
    *   **Function:** Snaps face pictures when access is triggered, posts pictures to the django backend.
3.  **Django REST Backend:**
    *   **Function:** Hosts the REST API for access verification, stores user records and access logs in SQLite, handles static file storage for uploaded camera snapshots.

## Diagram
```text
 +---------------------+            +--------------------+
 | ESP32 Controller    |            | ESP32-CAM Node     |
 | (RFID + TFT Screen) |            | (Face Snapshots)   |
 +----------+----------+            +---------+----------+
            |                                 |
            | HTTP POST (Verify UID)          | HTTP POST (Image upload)
            +----------------+----------------+
                             |
                             v
                 +-----------+-----------+
                 | Django REST Framework |
                 | (SQLite DB Logs)      |
                 +-----------------------+
```
