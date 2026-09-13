# A.R.G.U.S. — ESP32 Smart POS Terminal Firmware Guide

## Overview
This directory contains the edge firmware for the **A.R.G.U.S. Smart Transaction Terminal**, implemented on Espressif ESP32 hardware. 

The terminal serves as a physical **edge transaction-source device** (Smart POS / payment terminal). It captures financial transaction details, attaches hardware telemetry (uptime, SoC temperature, tamper flag), securely transmits data to the A.R.G.U.S. FastAPI Gateway, and displays the multi-model fraud risk verdict on local LEDs / serial terminal.

---

## Architectural Principle & Ingestion Boundary

```
+------------------------------------+
|     ESP32 Edge POS Terminal        |
|  - Strictly Ingestion & Telemetry  |
|  - NO ML/DL Models on Microchip    |
+------------------------------------+
                 |
                 | HTTP / HTTPS (TLS)
                 | Headers: X-Device-Code, X-Device-API-Key
                 v
+------------------------------------+
|      A.R.G.U.S. Gateway API        |
|  - Cryptographic Device Auth       |
|  - 18-Feature Extraction Pipeline  |
|  - 4 ML/DL Model Inference         |
|  - Ensemble Risk Engine Scoring    |
|  - PostgreSQL 3NF Persistence      |
+------------------------------------+
```

> [!IMPORTANT]
> **No Edge Machine Learning**: The ESP32 does **NOT** run XGBoost, Logistic Regression, Isolation Forest, or the Deep Autoencoder. All model inference and risk scoring are performed centrally on the FastAPI server.

---

## Hardware Requirements & Wiring

1. **Microcontroller**: ESP32-WROOM-32, ESP32-S3, or compatible module.
2. **Status Actuators (Optional)**:
   - **Green LED (GPIO 18)**: Approved Transaction (`APPROVE`).
   - **Yellow LED (GPIO 19)**: Operational Review (`REVIEW`) / Warning.
   - **Red LED (GPIO 21)**: Blocked Transaction (`BLOCK`) / Tamper Alert.
3. **Chassis Tamper Switch (GPIO 4)**:
   - Push switch connected to GND with internal pull-up (`INPUT_PULLUP`).
   - Depressing/releasing the switch triggers `tamper_flag = true`.

---

## Software Dependencies & Libraries

Install the following via Arduino Library Manager or PlatformIO:
- **ArduinoJson** (Version 6.x or 7.x) by Benoit Blanchon.
- **WiFi** and **HTTPClient** (Built-in with Espressif ESP32 Arduino Core).

---

## Configuration & Flashing Instructions

1. **Create Local Config**:
   Copy [`config.example.h`](file:///c:/PRO/PBL%20SY/iot/esp32/config.example.h) to `config.h`:
   ```bash
   cp iot/esp32/config.example.h iot/esp32/config.h
   ```
2. **Edit `config.h`**:
   - Set `WIFI_SSID` and `WIFI_PASSWORD`.
   - Set `ARGUS_API_BASE_URL` to the host machine's IP (e.g. `http://192.168.1.50:8000`).
   - Set `DEVICE_CODE` (e.g. `ESP32-TERM-001`).
   - Set `DEVICE_API_KEY` to the provisioned credential.
3. **Compile & Upload**:
   - Open [`argus_esp32.ino`](file:///c:/PRO/PBL%20SY/iot/esp32/argus_esp32.ino) in Arduino IDE.
   - Select Board: `ESP32 Dev Module`.
   - Upload baud rate: `921600`.
   - Flash to device.
4. **Serial Monitor**:
   - Open Serial Monitor at **115200 baud**.
   - Watch boot sequence, Wi-Fi connection, and heartbeat synchronization.
   - Send `1`, `2`, or `3` via Serial Monitor to trigger test transactions.

---

## Transport Security Disclosure

- **Local Development / Testbed**: Plain HTTP over private LAN or localhost is supported for convenient bench prototyping.
- **Production Deployment**: Device credentials must be transmitted exclusively over **TLS/HTTPS** (`WiFiClientSecure` with root CA pinning) when communicating across untrusted or public networks.
