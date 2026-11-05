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
#define WARMUP_MS 180000UL

char ssid[] = ""; 
char pass[] = "";
const char* MQTT_HOST = "";   // Pi's IP

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient mqtt(espClient);
BlynkTimer timer;

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

void sendData() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  int mq2   = readAnalog(MQ2_PIN);
  int mq135 = readAnalog(MQ135_PIN);

  if (isnan(h) || isnan(t)) Serial.println("DHT read failed");
  else { Blynk.virtualWrite(V0, t); Blynk.virtualWrite(V1, h); }
  Blynk.virtualWrite(V2, mq2);
  Blynk.virtualWrite(V3, mq135);

  char payload[200];
  snprintf(payload, sizeof(payload), "{\"device\":\"esp32-01\",");
  addFloat(payload, sizeof(payload), "temperature", t);
  addFloat(payload, sizeof(payload), "humidity", h);
  size_t len = strlen(payload);
  snprintf(payload + len, sizeof(payload) - len,
           "\"mq2\":%d,\"mq135\":%d,\"warm\":%d}",
           mq2, mq135, millis() > WARMUP_MS ? 1 : 0);

  if (!mqtt.connected()) {
    Serial.println("Connecting to MQTT...");
    mqtt.connect("esp32-01");
  }
  if (mqtt.connected()) {
    mqtt.publish("forest/esp32-01/readings", payload);
    Serial.println(payload);
  } else {
    Serial.println("MQTT failed, rc=" + String(mqtt.state()));
  }
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  analogReadResolution(12);                    // 0..4095
  analogSetPinAttenuation(MQ2_PIN, ADC_11db);
  analogSetPinAttenuation(MQ135_PIN, ADC_11db);
  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass);
  mqtt.setServer(MQTT_HOST, 1883);
  mqtt.setSocketTimeout(2);
  timer.setInterval(5000L, sendData);          // use 60000L once testing is done
}

void loop() {
  Blynk.run();
  mqtt.loop();
  timer.run();
}
