#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <ArduinoJson.h>
#include "pins.h"
#include "config.h"

// Networking configuration loaded from config.h
const char* ssid = WIFI_SSID;
const char* password = WIFI_PASS;
const char* backend_url = BACKEND_URL;
const char* device_id = DEVICE_ID;

// Peripheral Drivers
MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);
Adafruit_ILI9341 tft = Adafruit_ILI9341(TFT_CS, TFT_DC, TFT_RST);

// State tracking
enum SystemState { STATE_CONNECTING, STATE_IDLE, STATE_VERIFYING, STATE_RESULT };
SystemState currentState = STATE_CONNECTING;
unsigned long stateTimer = 0;

// Displays UI screen messages
void drawScreen(const char* header, const char* body, uint16_t bgColor, uint16_t textColor) {
    tft.fillScreen(bgColor);
    tft.setCursor(10, 50);
    tft.setTextColor(textColor);
    tft.setTextSize(3);
    tft.println(header);
    tft.setTextSize(2);
    tft.setCursor(10, 120);
    tft.println(body);
}

void setup() {
    Serial.begin(115200);
    SPI.begin();
    
    // Peripherals init
    rfid.PCD_Init();
    tft.begin();
    tft.setRotation(1); // Landscape view
    
    drawScreen("SYSTEM START", "Connecting Wi-Fi...", ILI9341_BLACK, ILI9341_WHITE);
    
    WiFi.begin(ssid, password);
}

void handleVerification(String cardUid) {
    currentState = STATE_VERIFYING;
    drawScreen("CHECKING...", "Verifying UID...", ILI9341_BLUE, ILI9341_WHITE);
    
    if (WiFi.status() != WL_CONNECTED) {
        drawScreen("OFFLINE", "Wi-Fi Disconnected", ILI9341_RED, ILI9341_WHITE);
        stateTimer = millis();
        currentState = STATE_RESULT;
        return;
    }

    WiFiClientSecure client;
    client.setInsecure(); // Skip TLS certificate validation for prototype/sim testing

    HTTPClient http;
    http.begin(client, backend_url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Token", DEVICE_SECRET_TOKEN);
    
    StaticJsonDocument<200> reqDoc;
    reqDoc["card_uid"] = cardUid;
    reqDoc["device_id"] = device_id;
    
    String requestPayload;
    serializeJson(reqDoc, requestPayload);
    
    int httpResponseCode = http.POST(requestPayload);
    
    if (httpResponseCode > 0) {
        String responsePayload = http.getString();
        StaticJsonDocument<300> resDoc;
        DeserializationError error = deserializeJson(resDoc, responsePayload);
        
        if (!error) {
            bool authorized = resDoc["authorized"] | false;
            const char* msg = resDoc["message"] | "Error";
            
            if (authorized) {
                drawScreen("ACCESS GRANTED", msg, ILI9341_GREEN, ILI9341_BLACK);
            } else {
                drawScreen("ACCESS DENIED", msg, ILI9341_RED, ILI9341_WHITE);
            }
        } else {
            drawScreen("ERROR", "JSON parsing failed", ILI9341_MAROON, ILI9341_WHITE);
        }
    } else {
        drawScreen("ERROR", "API connection failed", ILI9341_MAROON, ILI9341_WHITE);
    }
    
    http.end();
    stateTimer = millis();
    currentState = STATE_RESULT;
}

void loop() {
    switch (currentState) {
        case STATE_CONNECTING:
            if (WiFi.status() == WL_CONNECTED) {
                Serial.println("Wi-Fi Connected.");
                drawScreen("READY", "Scan your RFID tag", ILI9341_BLACK, ILI9341_GREEN);
                currentState = STATE_IDLE;
            }
            break;
            
        case STATE_IDLE:
            // Check for new RFID card scans
            if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
                String cardUid = "";
                for (byte i = 0; i < rfid.uid.size; i++) {
                    cardUid += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
                    cardUid += String(rfid.uid.uidByte[i], HEX);
                }
                cardUid.toUpperCase();
                
                Serial.print("RFID Scan UID: ");
                Serial.println(cardUid);
                
                handleVerification(cardUid);
                
                rfid.PICC_HaltA();
                rfid.PCD_StopCrypto1();
            }
            break;
            
        case STATE_RESULT:
            // Wait 3 seconds before returning to idle screen
            if (millis() - stateTimer >= 3000) {
                drawScreen("READY", "Scan your RFID tag", ILI9341_BLACK, ILI9341_GREEN);
                currentState = STATE_IDLE;
            }
            break;
            
        default:
            break;
    }
    delay(50); // Small loop delay
}
