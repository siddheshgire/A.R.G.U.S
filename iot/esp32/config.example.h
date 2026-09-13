/**
 * A.R.G.U.S. — ESP32 Smart POS Terminal Configuration Template
 * 
 * IMPORTANT: Copy this file to 'config.h' and fill in local credentials.
 * NEVER commit 'config.h' with real credentials to source control.
 */

#ifndef ARGUS_CONFIG_H
#define ARGUS_CONFIG_H

// Wi-Fi Access Point Credentials
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// A.R.G.U.S. Backend Gateway Endpoint
// Local Development / Testbed: "http://192.168.1.100:8000" (or host machine LAN IP)
// Production / Untrusted Network: "https://argus-gateway.yourdomain.com"
// NOTE: Device credentials must be transmitted only over TLS/HTTPS when communicating
// across an untrusted or production network.
const char* ARGUS_API_BASE_URL = "http://192.168.1.100:8000";

// Terminal Hardware Identity & Authentication Credential
const char* DEVICE_CODE = "ESP32-TERM-001";
const char* DEVICE_API_KEY = "YOUR_PROVISIONED_DEVICE_KEY";

// Terminal Hardware & Firmware Information
const char* FIRMWARE_VERSION = "v1.2.0-esp32";
const int HEARTBEAT_INTERVAL_MS = 30000; // 30 seconds

// Hardware Pin Definitions (Optional OLED / Status LEDs)
#define PIN_LED_GREEN 18  // Approved Transaction Indicator
#define PIN_LED_YELLOW 19 // Operational Review Indicator
#define PIN_LED_RED 21    // Blocked / Tamper Indicator
#define PIN_TAMPER_SWITCH 4 // Chassis Tamper Switch (Pull-up)

#endif // ARGUS_CONFIG_H
