# Physical Pinout & GPIO Configurations

This document establishes the hardware pin mappings for both ESP32 boards.

---

## 1. ESP32 Main Controller (RFID & TFT Screen)

The main ESP32 uses SPI to interface with both the RFID reader (MFRC522) and the TFT display (ST7735). 

> [!WARNING]
> Ensure CS (Chip Select) pins are separate to prevent collisions on the SPI bus.

| Peripheral | Peripheral Pin | ESP32 GPIO | Notes |
|:---|:---|:---|:---|
| **MFRC522** | SDA (SS/CS) | GPIO 5 | Chip Select RFID |
| | SCK | GPIO 18 | SPI Clock (Shared) |
| | MOSI | GPIO 23 | SPI MOSI (Shared) |
| | MISO | GPIO 19 | SPI MISO (Shared) |
| | IRQ | N/C | Not Connected |
| | GND | GND | Common ground |
| | RST | GPIO 22 | Reset Pin |
| | 3.3V | 3.3V | Power Supply (RFID is 3.3V only!) |
| **ST7735** | CS | GPIO 15 | Chip Select Display |
| | SCL (SCK) | GPIO 18 | SPI Clock (Shared) |
| | SDA (MOSI) | GPIO 23 | SPI MOSI (Shared) |
| | RES (RST) | GPIO 4 | Reset Pin |
| | DC (A0) | GPIO 2 | Data/Command |
| | BL (LED) | 3.3V or GPIO | Backlight control |
| **Relay** | Signal | GPIO 12 | Active High (Triggers Solenoid Latch) |

---

## 2. ESP32-CAM Node

The camera requires dedicated high-frequency pins. Avoid using them for general purposes.

*   **Camera Pins:** Standard OmniVision OV2640 pinout mapping (default AI-Thinker configuration).
*   **Debug/Serial:** GPIO 1 (TX) and GPIO 3 (RX) for flash updates and logging.
*   **External Latch Signal / Trigger:** GPIO 13 or GPIO 12 can be configured as inputs to receive hardware trigger pulses directly if offline operation is desired.
