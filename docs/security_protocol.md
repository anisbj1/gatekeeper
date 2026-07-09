# Security & Authentication Handshake Protocol

This document details how requests are signed, authenticated, and secured.

---

## 1. Authentication Handshake Flow

Below is the step-by-step logic used to verify access requests:

```mermaid
sequenceDiagram
    participant U as RFID Card
    participant HW as ESP32 Controller
    participant CAM as ESP32-CAM
    participant BE as Django API

    U->>HW: Scans Card UID
    HW->>BE: POST /verify/ {uid, dev_id} with API-Key Header
    BE->>BE: Validates Card in DB
    alt Access Authorized
        BE-->>HW: Returns 200 {status: "authorized", action: "unlock", trigger_camera: true}
        HW->>HW: Triggers Relay (Unlock)
        HW->>HW: Updates Screen to "Welcome"
        BE->>CAM: (Websocket/HTTP Trigger) Capture Event
        CAM->>BE: POST /upload/ {multipart image data}
    else Access Denied
        BE-->>HW: Returns 403 {status: "rejected", action: "keep_locked"}
        HW->>HW: Updates Screen to "Access Denied"
    end
```

---

## 2. API Security

*   **ESP32 Request Authorization:** Every request from the ESP32 must include a custom request header:
    `X-Device-Token: <SECRET_ESP32_TOKEN>`
*   **Django Validation:** The backend checks the device token against registered IoT devices in Django configuration settings.
*   **Replay Protection (Future):** Introduce UNIX timestamps in requests to prevent replay attacks on the local network.
