#ifndef CONFIG_H
#define CONFIG_H

// ==========================================
// ENVIRONMENT SELECTION
// ==========================================
// Uncomment the line below to build for Wokwi simulation
#define USE_WOKWI_SIMULATION

#ifdef USE_WOKWI_SIMULATION
    // Wokwi Virtual Wi-Fi Settings
    #define WIFI_SSID     "Wokwi-GUEST"
    #define WIFI_PASS     ""
    // host.wokwi.internal resolves to your local PC within Wokwi VS Code extension
    #define BACKEND_URL   "https://host.wokwi.internal:8000/api/v1/access/verify/"
#else
    // Physical Hardware Wi-Fi Settings (Edit these for your home/office network)
    #define WIFI_SSID     "YOUR_REAL_WIFI_SSID"
    #define WIFI_PASS     "YOUR_REAL_WIFI_PASSWORD"
    // Replace with your computer's local IP address (e.g. 192.168.1.15)
    #define BACKEND_URL   "https://192.168.1.X:8000/api/v1/access/verify/"
#endif

// IoT Device Configuration
#define DEVICE_ID            "esp32_01"
// Demo token only — generate a unique per-device secret before deployment
#define DEVICE_SECRET_TOKEN  "dev_secret_token_esp32_01"

#endif // CONFIG_H
