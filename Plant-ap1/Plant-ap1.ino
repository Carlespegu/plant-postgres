/*
  Plant Station ESP32 -> Render FastAPI
  - DHT11: temp + air humidity
  - LDR: analog light (raw)
  - Soil moisture: analog -> % (calibration)
  - Rain LM393: digital (0/1) + label
  Sends POST JSON to: https://<service>.onrender.com/api/v1/readings
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <DHT.h>

// ===== WiFi =====
const char* WIFI_SSID = "MiFibra-9687";
const char* WIFI_PASS = "h447xhrL";
// ==============================
// API
// ==============================
const char* API_URL = "https://plant-postgres-1.onrender.com/api/v1/readings";
const char* API_KEY = "plant_station_secret";
const char* DEVICE_ID = "esp32-plant-01";

// Header name used by the FastAPI app (adapt if your backend uses a different header)
const char* API_KEY_HEADER = "X-API-Key";

// ==============================
// PINS
// ==============================
#define PIN_DHT   4
#define PIN_SOIL  34
#define PIN_LDR   35
#define PIN_RAIN  27

// ==============================
// DHT
// ==============================
#define DHTTYPE DHT11
DHT dht(PIN_DHT, DHTTYPE);

// ==============================
// CONFIGURACIÓ
// ==============================

// Ajusta aquests valors segons calibratge real
int SOIL_RAW_DRY = 4095;   // lectura amb terra seca / sonda a l'aire
int SOIL_RAW_WET = 2000;   // lectura amb terra molt humida o aigua

// Si el sensor LM393 dona LOW quan està mullat
bool RAIN_ACTIVE_LOW = true;

// Interval d'enviament
unsigned long SEND_INTERVAL_MS = 300000; // 30 segons

unsigned long lastSend = 0;

// ==============================
// FUNCIONS AUXILIARS
// ==============================

int clampInt(int value, int minValue, int maxValue) {
  if (value < minValue) return minValue;
  if (value > maxValue) return maxValue;
  return value;
}

int mapSoilRawToPercent(int raw) {
  long denominator = (long)SOIL_RAW_DRY - (long)SOIL_RAW_WET;
  if (denominator == 0) return 0;

  long numerator = (long)SOIL_RAW_DRY - (long)raw;
  long percent = (numerator * 100L) / denominator;

  return clampInt((int)percent, 0, 100);
}

int readRainDigital() {
  int raw = digitalRead(PIN_RAIN);

  if (RAIN_ACTIVE_LOW) {
    return (raw == LOW) ? 1 : 0;   // 1 = rain, 0 = dry
  } else {
    return (raw == HIGH) ? 1 : 0;
  }
}

const char* rainApiValue(int rainWet) {
  return (rainWet == 1) ? "rain" : "dry";
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print("Connecting to WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long startAttempt = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 20000) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi connection FAILED");
  }
}

String buildJson(
  float tempC,
  float humAir,
  int ldrRaw,
  int soilPercent,
  int rainWet,
  int rssi
) {
  String json = "{";
  json += "\"deviceId\":\"" + String(DEVICE_ID) + "\",";
  json += "\"tempC\":" + String(tempC, 1) + ",";
  json += "\"humAir\":" + String(humAir, 0) + ",";
  json += "\"ldrRaw\":" + String(ldrRaw) + ",";
  json += "\"soilPercent\":" + String(soilPercent) + ",";
  json += "\"rain\":\"" + String(rainApiValue(rainWet)) + "\",";
  json += "\"rssi\":" + String(rssi);
  json += "}";

  return json;
}

bool postJsonToApi(const String& json) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("POST skipped: WiFi not connected");
    return false;
  }

  WiFiClientSecure client;
  client.setInsecure(); // per MVP, sense validar certificat

  HTTPClient http;
  http.setTimeout(15000);

  if (!http.begin(client, API_URL)) {
    Serial.println("HTTP begin failed");
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Api-Key", API_KEY);

  int httpCode = http.POST((uint8_t*)json.c_str(), json.length());

  Serial.print("POST ");
  Serial.print(API_URL);
  Serial.print(" -> HTTP ");
  Serial.println(httpCode);

  String response = http.getString();
  if (response.length() > 0) {
    Serial.println("Response:");
    Serial.println(response);
  }

  http.end();

  return (httpCode == 200 || httpCode == 201);
}

// ==============================
// SETUP
// ==============================

void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(PIN_SOIL, INPUT);
  pinMode(PIN_LDR, INPUT);
  pinMode(PIN_RAIN, INPUT);

  dht.begin();
  delay(2000); // important per estabilitzar el DHT

  connectWiFi();

  Serial.println("Plant Station ready.");
}

// ==============================
// LOOP
// ==============================

void loop() {
  connectWiFi();

  float t = dht.readTemperature();
  float h = dht.readHumidity();

  bool dhtOk = !(isnan(t) || isnan(h));

  int soilRaw = analogRead(PIN_SOIL);
  int ldrRaw = analogRead(PIN_LDR);
  int soilPercent = mapSoilRawToPercent(soilRaw);
  int rainWet = readRainDigital();
  int rssi = WiFi.RSSI();

  Serial.println("---- Reading ----");

  if (dhtOk) {
    Serial.print("Temp: ");
    Serial.print(t);
    Serial.print(" C | Hum air: ");
    Serial.print(h);
    Serial.println(" %");
  } else {
    Serial.println("DHT read failed (NaN).");
    t = -1;
    h = -1;
  }

  Serial.print("Soil raw: ");
  Serial.print(soilRaw);
  Serial.print(" | Soil %: ");
  Serial.println(soilPercent);

  Serial.print("LDR raw: ");
  Serial.println(ldrRaw);

  Serial.print("Rain: ");
  Serial.print(rainWet);
  Serial.print(" (");
  Serial.print(rainApiValue(rainWet));
  Serial.println(")");

  Serial.print("RSSI: ");
  Serial.println(rssi);

  unsigned long now = millis();

  if (now - lastSend >= SEND_INTERVAL_MS) {
    lastSend = now;

    String json = buildJson(
      t,
      h,
      ldrRaw,
      soilPercent,
      rainWet,
      rssi
    );

    Serial.println("JSON:");
    Serial.println(json);

    bool ok = postJsonToApi(json);

    if (!ok) {
      Serial.println("POST failed. Will retry next cycle.");
    } else {
      Serial.println("POST OK");
    }
  }

  delay(2000);
}