#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <IRremote.hpp>
#include <PubSubClient.h>
#include <SPI.h>
#include <ArduinoJson.h>
#include <MFRC522.h>

#define RST_PIN 14
#define SS_PIN 10

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define IR_RECEIVER_PIN 4

WiFiClient espClient;
PubSubClient client(espClient);
unsigned long lastMsg = 0;
#define MSG_BUFFER_SIZE (50)
char msg[MSG_BUFFER_SIZE];
int value = 0;

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
MFRC522 mfrc522(SS_PIN, RST_PIN);

char ssid[] = "Vukašin's iPhone";
char pass[] = "nemozcrnje";
char mqtt_server[] = "192.168.56.1"; //ipconfig in cmd -> wlan ipv4
char device_id[] ="b71420d0-0e9a-45a8-b668-0d9a6ffacba4";
String tag_pin = "22827021";
String pin_input = "";
String tag_input = "";
bool locked = true;
bool initialized=false;


IRrecv irrecv(IR_RECEIVER_PIN);
decode_results results;

void setup() {

  Serial.begin(9600);
  while (!Serial) {}


  wifiConnection();
  client.setServer(mqtt_server, 1883);
  client.setCallback(messageCallback);
  
  IrReceiver.begin(IR_RECEIVER_PIN, 0);

  SPI.begin();
  mfrc522.PCD_Init();
  delay(4);
  mfrc522.PCD_DumpVersionToSerial();

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {  // Address 0x3D for 128x64
    Serial.println(F("SSD1306 allocation failed"));
    for (;;)
      ;
  }
  delay(2000);
  
  displayText("Initializing..");
}

void loop() {
  if (initialized == false && client.connected()){  
    getLockState();
    initialized = true;
  }
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  if (locked){
    tag_input = scanTagID();
    while (tag_input!="") {
          sendTagInput(tag_input);
          pin_input = "";
          tag_input = scanTagID();
    }
  }
  if (IrReceiver.decode()) {
    IrReceiver.resume();
    if (!(IrReceiver.decodedIRData.flags & IRDATA_FLAGS_IS_REPEAT)) {
      String character = decodeSignal(IrReceiver.decodedIRData.command);
      if(locked){
        if (character == "DEL"){
        pin_input = pin_input.substring(0, pin_input.length()-1);
        }
        else if(character == "-1"){}
        else if(character == "OK"){
          sendPinInput(pin_input);
          pin_input = "";
        }
        else{
          if(pin_input.length()<4){
            pin_input += character;
          }
        }
      }
      else{
        if(character=="#"){
          lockLock();
        }
        else if(character=="*"){
          sendCapture();
        }
      }
      
      if(pin_input==""){
        if(locked){
          displayText("Locked");
        }
        else{
          displayText("Unlocked");
        }
      }
      else{
        displayText(pin_input);
      }
      

    }
  }
}

String scanTagID() {
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return "";
  }
  if (!mfrc522.PICC_ReadCardSerial()) {
    return "";
  }
  tag_input = "";
  for (uint8_t i = 0; i < 4; i++) {
    tag_input.concat(String(mfrc522.uid.uidByte[i], HEX));
  }
  tag_input.toUpperCase();
  mfrc522.PICC_HaltA();
  Serial.println(tag_input);
  return tag_input;
}

void wifiConnection() {
  Serial.print("Attempting to connect to SSID: ");
  Serial.println(ssid);

  WiFi.useStaticBuffers(true);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("Connected to WiFi");
}

void sendPinInput(String pinInput) {
  JsonDocument doc;
  doc["action"] = "pinUnlock";
  doc["pin"] = pinInput;
  doc["device_id"] = device_id;
  String msg = "";
  serializeJson(doc, msg);
  Serial.println(msg);
  client.publish("FromLock", msg.c_str());
}

void sendTagInput(String tagInput) {
  JsonDocument doc;
  doc["action"] = "tagUnlock";
  doc["tag"] = tagInput;
  doc["device_id"] = device_id;
  String msg = "";
  serializeJson(doc, msg);
  Serial.println(msg);
  client.publish("FromLock", msg.c_str());
}

void getLockState() {
  JsonDocument doc;
  doc["action"] = "getState";
  doc["device_id"] = device_id;
  String msg = "";
  serializeJson(doc, msg);
  Serial.println(msg);
  client.publish("FromLock", msg.c_str());
}

void lockLock() {
  JsonDocument doc;
  doc["action"] = "lockLock";
  doc["device_id"] = device_id;
  String msg = "";
  serializeJson(doc, msg);
  Serial.println(msg);
  client.publish("FromLock", msg.c_str());
}

void sendCapture() {
  JsonDocument doc;
  doc["action"] = "capture";
  String msg = "";
  serializeJson(doc, msg);
  Serial.println(msg);
  client.publish("FromLock", msg.c_str());
}

void messageCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  JsonDocument doc;
  deserializeJson(doc, payload);
  if (!doc["locked"].isNull()) {
      locked = doc["locked"] == true;
      Serial.println(locked);
      if (!locked) {
        displayText("Unlocked");
      } else {
        displayText("Locked");
      }
    }
  pin_input = "";
}
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP82667Client-";
    clientId += String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      client.subscribe("ToLock");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void displayText(String text) {
  display.clearDisplay();

  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.setCursor(10, 1);
  display.println(text);
  display.display();
}


String decodeSignal(uint16_t signal) {
  switch (signal) {
    case 0x45:
      return "1";
      break;
    case 0x46:
      return "2";
      break;
    case 0x47:
      return "3";
      break;
    case 0x44:
      return "4";
      break;
    case 0x40:
      return "5";
      break;
    case 0x43:
      return "6";
      break;
    case 0x7:
      return "7";
      break;
    case 0x15:
      return "8";
      break;
    case 0x9:
      return "9";
      break;
    case 0x19:
      return "0";
      break;
    case 0xD:
      return "#";
      break;
    case 0x16:
      return "*";
      break;
    case 0x8:
      return "DEL";
      break;
    case 0x1C:
      return "OK";
      break;
    default:
      return "-1";
      break;
  }
}
