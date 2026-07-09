#ifndef PINS_H
#define PINS_H

// Pinouts matching simulation/diagram.json

#define RFID_SS_PIN   5
#define RFID_RST_PIN  22

#define TFT_CS        15
#define TFT_DC        2
#define TFT_RST       4

// Standard SPI:
// SCK  -> GPIO 18 (Shared)
// MOSI -> GPIO 23 (Shared)
// MISO -> GPIO 19 (RFID only)

#endif // PINS_H
