#define BLYNK_TEMPLATE_ID   ""
#define BLYNK_TEMPLATE_NAME ""
#define BLYNK_AUTH_TOKEN    ""
#define BLYNK_PRINT Serial

#include <WiFi.h>
#include <BlynkSimpleEsp32.h>
#include <PubSubClient.h>
#include <DHT.h>

#define DHTPIN 4
#define DHTTYPE DHT22

char ssid[] = ""; // Network name
char pass[] = ""; // Network password
const char* MQTT_HOST = ";   // Pi's IP

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient mqtt(espClient);
BlynkTimer timer;

void sendData() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t)) { Serial.println("DHT read failed"); return; }

  Blynk.virtualWrite(V0, t);
  Blynk.virtualWrite(V1, h);

  if (!mqtt.connected()) {
    Serial.println("Connecting to MQTT...");
    mqtt.connect("esp32-01");
  }
  if (mqtt.connected()) {
    char payload[96];
    snprintf(payload, sizeof(payload),
             "{\"device\":\"esp32-01\",\"temperature\":%.2f,\"humidity\":%.2f}", t, h);
    mqtt.publish("forest/esp32-01/readings", payload);
    Serial.println(payload);
  } else {
    Serial.println("MQTT failed, rc=" + String(mqtt.state()));
  }
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass);
  mqtt.setServer(MQTT_HOST, 1883);
  mqtt.setSocketTimeout(2);   // give up quickly if the broker is unreachable
  timer.setInterval(5000L, sendData);   // AM2302 needs >= 2 s between reads
}

void loop() {
  Blynk.run();
  mqtt.loop();
  timer.run();
}
