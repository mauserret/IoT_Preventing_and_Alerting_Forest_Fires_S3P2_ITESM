#define BLYNK_TEMPLATE_ID   ""
#define BLYNK_TEMPLATE_NAME ""
#define BLYNK_AUTH_TOKEN    ""
#define BLYNK_PRINT Serial

#include <WiFi.h>
#include <BlynkSimpleEsp32.h>
#include <PubSubClient.h>
#include <DHT.h>

#define DHTPIN    4
#define DHTTYPE   DHT22
#define MQ2_PIN   34   // ADC1, through the voltage divider
#define MQ135_PIN 35   // ADC1, through the voltage divider
#define MQ7_PIN   32   // ADC1, through the voltage divider
#define WARMUP_MS 180000UL

char ssid[] = "";
char pass[] = "";
const char* MQTT_HOST = "";   // Pi static IP, e.g. 192.168.137.236

// ---- timing -----------------------------------------------------------
const unsigned long SAMPLE_MS    = 5000UL;   // how often sensors are read (and events detected)
unsigned long sendMs             = 60000UL;  // normal publish interval; changeable over MQTT
const unsigned long FAST_HOLD_MS = 60000UL;  // stay in fast mode this long after an event
// ---- event detection (counts above the slow baseline) -------------------
const int   JUMP_MQ2   = 100;
const int   JUMP_MQ135 = 100;
const int   JUMP_MQ7   = 300;
const float EMA_ALPHA  = 0.02f;              // baseline follows slowly (~4 min at 5 s samples)

// Change the interval without reflashing, from the Pi:
//   mosquitto_pub -r -t forest/esp32-01/config -m 5     (seconds, 5..3600; -r = retained)
//   mosquitto_pub -r -n -t forest/esp32-01/config       (remove it)
const char* TOPIC_CFG = "forest/esp32-01/config";

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient mqtt(espClient);
BlynkTimer timer;

unsigned long lastSend = 0, fastUntil = 0;
float emaMq2 = -1, emaMq135 = -1, emaMq7 = -1;

int readAnalog(int pin) {
  long sum = 0;
  for (int i = 0; i < 16; i++) { sum += analogRead(pin); delay(2); }
  return sum / 16;
}

// "null" in JSON when the value is not a number
void addFloat(char* buf, size_t n, const char* key, float v) {
  size_t len = strlen(buf);
  if (isnan(v)) snprintf(buf + len, n - len, "\"%s\":null,", key);
  else          snprintf(buf + len, n - len, "\"%s\":%.2f,", key, v);
}

void onMqtt(char* topic, byte* payload, unsigned int len) {
  char buf[12];
  if (len > sizeof(buf) - 1) len = sizeof(buf) - 1;
  memcpy(buf, payload, len);
  buf[len] = 0;
  long s = atol(buf);
  if (s >= 5 && s <= 3600) {
    sendMs = (unsigned long)s * 1000UL;
    Serial.println("Send interval set to " + String(s) + " s");
  } else {
    Serial.println("Ignored config value: " + String(buf));
  }
}

bool ensureMqtt() {
  if (mqtt.connected()) return true;
  Serial.println("Connecting to MQTT...");
  if (mqtt.connect("esp32-01")) {
    mqtt.subscribe(TOPIC_CFG);   // must be redone after every reconnect
    return true;
  }
  Serial.println("MQTT failed, rc=" + String(mqtt.state()));
  return false;
}

void publishReading(float t, float h, int mq2, int mq135, int mq7, bool warm) {
  if (isnan(h) || isnan(t)) Serial.println("DHT read failed");
  else { Blynk.virtualWrite(V0, t); Blynk.virtualWrite(V1, h); }
  Blynk.virtualWrite(V2, mq2);
  Blynk.virtualWrite(V3, mq135);
  Blynk.virtualWrite(V4, mq7);

  char payload[220];
  snprintf(payload, sizeof(payload), "{\"device\":\"esp32-01\",");
  addFloat(payload, sizeof(payload), "temperature", t);
  addFloat(payload, sizeof(payload), "humidity", h);
  size_t len = strlen(payload);
  snprintf(payload + len, sizeof(payload) - len,
           "\"mq2\":%d,\"mq135\":%d,\"mq7\":%d,\"warm\":%d}",
           mq2, mq135, mq7, warm ? 1 : 0);

  if (ensureMqtt()) {
    mqtt.publish("forest/esp32-01/readings", payload);
    Serial.println(payload);
  }
}

void sample() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  int mq2   = readAnalog(MQ2_PIN);
  int mq135 = readAnalog(MQ135_PIN);
  int mq7   = readAnalog(MQ7_PIN);
  unsigned long now = millis();
  bool warm = now > WARMUP_MS;

  if (emaMq2 < 0) { emaMq2 = mq2; emaMq135 = mq135; emaMq7 = mq7; }

  // event = any gas well above its slow baseline (only after warm-up)
  bool event = warm && ((mq2   - emaMq2   > JUMP_MQ2)   ||
                        (mq135 - emaMq135 > JUMP_MQ135) ||
                        (mq7   - emaMq7   > JUMP_MQ7));

  if (event) {
    fastUntil = now + FAST_HOLD_MS;      // keeps extending while gas stays high
  } else {                               // baseline frozen during an event
    emaMq2   += EMA_ALPHA * (mq2   - emaMq2);
    emaMq135 += EMA_ALPHA * (mq135 - emaMq135);
    emaMq7   += EMA_ALPHA * (mq7   - emaMq7);
  }

  bool fast = (long)(fastUntil - now) > 0;
  bool due  = (lastSend == 0) || (now - lastSend >= sendMs);
  if (event || fast || due) {
    publishReading(t, h, mq2, mq135, mq7, warm);
    lastSend = now;
  }
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  analogReadResolution(12);                    // 0..4095
  analogSetPinAttenuation(MQ2_PIN, ADC_11db);
  analogSetPinAttenuation(MQ135_PIN, ADC_11db);
  analogSetPinAttenuation(MQ7_PIN, ADC_11db);
  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass);
  mqtt.setServer(MQTT_HOST, 1883);
  mqtt.setSocketTimeout(2);
  mqtt.setCallback(onMqtt);
  timer.setInterval(SAMPLE_MS, sample);
}

void loop() {
  Blynk.run();
  mqtt.loop();
  timer.run();
}
