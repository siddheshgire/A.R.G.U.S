/**
 * ==============================================================================
 * A.R.G.U.S. — Smart IoT Transaction Terminal Firmware
 * ==============================================================================
 * Hardware: Espressif ESP32-WROOM-32 / ESP32-S3
 * Role: Edge Ingestion Terminal (Smart POS / Payment Point)
 * 
 * IMPORTANT ARCHITECTURAL PRINCIPLE:
 * The ESP32 is strictly an INGESTION DEVICE. It does NOT run ML/DL models
 * (XGBoost, Deep Autoencoder, Isolation Forest, Logistic Regression) or the
 * Risk Engine. All inference and scoring are performed centrally by the
 * A.R.G.U.S. FastAPI Gateway.
 * 
 * Security Note:
 * In production deployments, TLS/HTTPS (WiFiClientSecure) must be used to ensure
 * transport layer confidentiality and integrity of credentials and transactions.
 * For local testbeds, HTTP is supported.
 * ==============================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Load device configuration.
// If 'config.h' does not exist, rename 'config.example.h' to 'config.h'.
#if __has_include("config.h")
  #include "config.h"
#else
  #include "config.example.h"
#endif

// Global Runtime State
unsigned long lastHeartbeatTime = 0;
unsigned long transactionSequence = 1000;
bool isTampered = false;

// ==============================================================================
// 1. HARDWARE & NETWORK INITIALIZATION
// ==============================================================================

void setupHardwarePins() {
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_TAMPER_SWITCH, INPUT_PULLUP);

  // Initial LED self-test
  digitalWrite(PIN_LED_GREEN, HIGH);
  digitalWrite(PIN_LED_YELLOW, HIGH);
  digitalWrite(PIN_LED_RED, HIGH);
  delay(500);
  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_YELLOW, LOW);
  digitalWrite(PIN_LED_RED, LOW);
}

void connectToWiFi() {
  Serial.println();
  Serial.print("[WiFi] Connecting to SSID: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("[WiFi] Connected successfully!");
    Serial.print("[WiFi] Assigned IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("[WiFi] Gateway RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println();
    Serial.println("[WiFi] Connection timeout. Operating in offline diagnostic mode.");
  }
}

// ==============================================================================
// 2. TELEMETRY & HEARTBEAT
// ==============================================================================

void sendHeartbeat() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[Heartbeat] Skipped: Wi-Fi disconnected.");
    return;
  }

  HTTPClient http;
  String url = String(ARGUS_API_BASE_URL) + "/api/v1/iot/heartbeat";
  http.begin(url);

  // Set Security Headers
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Code", DEVICE_CODE);
  http.addHeader("X-Device-API-Key", DEVICE_API_KEY);

  // Read hardware tamper switch
  isTampered = (digitalRead(PIN_TAMPER_SWITCH) == LOW);

  // Build JSON Telemetry Payload
  StaticJsonDocument<256> doc;
  doc["device_code"] = DEVICE_CODE;
  doc["firmware_version"] = FIRMWARE_VERSION;
  doc["device_status"] = isTampered ? "TAMPERED" : "ONLINE";
  doc["network_status"] = "CONNECTED";
  doc["temperature"] = temperatureRead(); // ESP32 built-in thermal sensor
  doc["tamper_flag"] = isTampered;
  doc["uptime_seconds"] = millis() / 1000;

  String requestBody;
  serializeJson(doc, requestBody);

  int httpResponseCode = http.POST(requestBody);
  if (httpResponseCode == 200) {
    String responseString = http.getString();
    Serial.print("[Heartbeat] Acknowledged: ");
    Serial.println(responseString);
  } else {
    Serial.print("[Heartbeat] Error: HTTP ");
    Serial.println(httpResponseCode);
  }

  http.end();
}

// ==============================================================================
// 3. TRANSACTION TRANSMISSION & VERDICT DISPLAY
// ==============================================================================

void sendTransaction(
  int step,
  const char* type,
  float amount,
  const char* nameOrig,
  const char* nameDest,
  float oldbalanceOrg,
  float newbalanceOrig,
  float oldbalanceDest,
  float newbalanceDest
) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[Transaction] Failed: Network offline.");
    digitalWrite(PIN_LED_RED, HIGH);
    return;
  }

  HTTPClient http;
  String url = String(ARGUS_API_BASE_URL) + "/api/v1/iot/transactions";
  http.begin(url);

  // Set Security Headers
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Code", DEVICE_CODE);
  http.addHeader("X-Device-API-Key", DEVICE_API_KEY);

  // Generate Unique Client Sequence ID (Idempotency / Duplicate Defense)
  transactionSequence++;
  String clientTxId = String(DEVICE_CODE) + "-TX-" + String(transactionSequence);

  // Construct Ingress JSON Payload (strictly no isFraud target labels)
  StaticJsonDocument<512> doc;
  doc["client_tx_id"] = clientTxId;
  doc["step"] = step;
  doc["type"] = type;
  doc["amount"] = amount;
  doc["name_orig"] = nameOrig;
  doc["name_dest"] = nameDest;
  doc["oldbalance_org"] = oldbalanceOrg;
  doc["newbalance_orig"] = newbalanceOrig;
  doc["oldbalance_dest"] = oldbalanceDest;
  doc["newbalance_dest"] = newbalanceDest;

  // Lightweight device metadata
  doc["device_status"] = "ONLINE";
  doc["network_status"] = "CONNECTED";
  doc["firmware_version"] = FIRMWARE_VERSION;
  doc["uptime_seconds"] = millis() / 1000;

  String requestBody;
  serializeJson(doc, requestBody);

  Serial.println("\n--------------------------------------------------");
  Serial.print("[Terminal] Transmitting Transaction: ");
  Serial.println(clientTxId);
  Serial.print("[Terminal] Type: ");
  Serial.print(type);
  Serial.print(" | Amount: $");
  Serial.println(amount, 2);

  int httpCode = http.POST(requestBody);

  if (httpCode == 200) {
    String responseString = http.getString();
    StaticJsonDocument<512> resDoc;
    DeserializationError error = deserializeJson(resDoc, responseString);

    if (!error) {
      const char* decision = resDoc["decision"];
      float riskScore = resDoc["risk_score"];
      const char* terminalMsg = resDoc["terminal_message"];
      const char* txId = resDoc["transaction_id"];

      Serial.println("[Terminal] >>> ASSESSMENT RECEIVED <<<");
      Serial.print("  Decision:       ");
      Serial.println(decision);
      Serial.print("  Risk Score:     ");
      Serial.print(riskScore, 2);
      Serial.println(" / 100.0");
      Serial.print("  Terminal LCD:   [ ");
      Serial.print(terminalMsg);
      Serial.println(" ]");
      Serial.print("  System Tx ID:   ");
      Serial.println(txId);

      // Actuate Physical Status LEDs
      if (strcmp(decision, "APPROVE") == 0) {
        digitalWrite(PIN_LED_GREEN, HIGH);
        digitalWrite(PIN_LED_YELLOW, LOW);
        digitalWrite(PIN_LED_RED, LOW);
      } else if (strcmp(decision, "REVIEW") == 0) {
        digitalWrite(PIN_LED_GREEN, LOW);
        digitalWrite(PIN_LED_YELLOW, HIGH);
        digitalWrite(PIN_LED_RED, LOW);
      } else { // BLOCK
        digitalWrite(PIN_LED_GREEN, LOW);
        digitalWrite(PIN_LED_YELLOW, LOW);
        digitalWrite(PIN_LED_RED, HIGH);
      }
    } else {
      Serial.println("[Terminal] JSON Deserialization error.");
    }
  } else if (httpCode == 409) {
    Serial.println("[Terminal] Conflict: Duplicate transaction sequence rejected.");
    digitalWrite(PIN_LED_YELLOW, HIGH);
  } else if (httpCode == 422) {
    Serial.println("[Terminal] Rejected: Non-modeled transaction type not supported for ML scoring.");
    digitalWrite(PIN_LED_YELLOW, HIGH);
  } else {
    Serial.print("[Terminal] Request Failed with HTTP: ");
    Serial.println(httpCode);
    digitalWrite(PIN_LED_RED, HIGH);
  }

  Serial.println("--------------------------------------------------");
  http.end();
}

// ==============================================================================
// 4. MAIN SETUP & EVENT LOOP
// ==============================================================================

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("==================================================");
  Serial.println("A.R.G.U.S. Smart Transaction Terminal Starting...");
  Serial.print("Device Code:      ");
  Serial.println(DEVICE_CODE);
  Serial.print("Firmware Build:   ");
  Serial.println(FIRMWARE_VERSION);
  Serial.println("==================================================");

  setupHardwarePins();
  connectToWiFi();

  // Send initial startup heartbeat
  sendHeartbeat();
}

void loop() {
  unsigned long currentMillis = millis();

  // 1. Periodic Telemetry Heartbeat
  if (currentMillis - lastHeartbeatTime >= HEARTBEAT_INTERVAL_MS) {
    lastHeartbeatTime = currentMillis;
    sendHeartbeat();
  }

  // 2. Interactive Serial Command Demonstration
  // Press '1' to send Legitimate TRANSFER (Expected: APPROVE)
  // Press '2' to send Suspicious Liquidation (Expected: BLOCK)
  // Press '3' to send Unsupported PAYMENT (Expected: HTTP 422)
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == '1') {
      Serial.println("\n[Action] Sending Legitimate TRANSFER transaction...");
      sendTransaction(
        150, "TRANSFER", 450.00,
        "C1029384756", "M9876543210",
        5000.00, 4550.00, 1000.00, 1450.00
      );
    } else if (cmd == '2') {
      Serial.println("\n[Action] Sending Suspicious Account Liquidation...");
      sendTransaction(
        654, "CASH_OUT", 399045.08,
        "C1122334455", "M5566778899",
        10399045.08, 10000000.00, 0.00, 0.00
      );
    } else if (cmd == '3') {
      Serial.println("\n[Action] Sending Non-modeled PAYMENT transaction...");
      sendTransaction(
        200, "PAYMENT", 15.50,
        "C9988776655", "M1122334455",
        200.00, 184.50, 0.00, 0.00
      );
    }
  }

  delay(100);
}
