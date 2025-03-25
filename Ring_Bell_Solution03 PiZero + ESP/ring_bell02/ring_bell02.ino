#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "SPIFFS.h"
#include "AudioOutputI2S.h"
#include "AudioGeneratorWAV.h"
#include "AudioFileSourceSPIFFS.h"

// WiFi Credentials
const char* ssid = "Digitaiken";
const char* password = "Welcome@123";
const char* serverURL = "http://pizerow001.local:5000/robot_status";
const char* targetPoint = "Point1";

// Audio objects
AudioGeneratorWAV *wav;
AudioFileSourceSPIFFS *file;
AudioOutputI2S *out;

void setup() {
    Serial.begin(115200);
    WiFi.begin(ssid, password);
    
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        Serial.print(".");
        delay(500);
    }
    Serial.println("\nConnected!");

    // Initialize SPIFFS for audio file
    if (!SPIFFS.begin(true)) {
        Serial.println("SPIFFS Mount Failed!");
        return;
    }
    Serial.println("SPIFFS Mounted Successfully!");

    // Set up I2S audio output
    out = new AudioOutputI2S();
    out->SetPinout(25, 26, 22);  // Adjust if needed
    out->SetGain(0.8);  // Volume (0.0 to 1.0)
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi Disconnected! Attempting to reconnect...");
        WiFi.disconnect();
        WiFi.reconnect();
        delay(5000);
        return;
    }
    
    HTTPClient http;
    http.begin(serverURL);
    int httpResponseCode = http.GET();

    if (httpResponseCode == 200) {
        String response = http.getString();
        Serial.println("Response received: " + response);
        checkArrival(response);
    } else {
        Serial.printf("HTTP GET request failed, error: %d\n", httpResponseCode);
    }
    http.end();
    delay(3000);  // Fetch JSON every 3 seconds
}

void checkArrival(String jsonString) {
    StaticJsonDocument<1024> doc;
    
    DeserializationError error = deserializeJson(doc, jsonString);
    if (error) {
        Serial.println("JSON Parsing Error! Response was:");
        Serial.println(jsonString);  // Print the response
        return;
    }
    
    // Proceed if parsing was successful
    for (JsonPair kv : doc.as<JsonObject>()) {
        const char* robot_ip = kv.key().c_str();
        JsonObject robotData = kv.value().as<JsonObject>();

        const char* arrive_stat = robotData["arrive_stat"];
        const char* point_id = robotData["point_id"];
        const char* robot_sn = robotData["robot_sn"];

        if (arrive_stat && point_id && robot_sn) {
            if (strcmp(arrive_stat, "arrived") == 0 && strcmp(point_id, targetPoint) == 0) {
                Serial.printf("Robot %s arrived at %s\n", robot_sn, point_id);
                playAudio();
            }
        } else {
            Serial.println("Invalid JSON structure!");
        }
    }
}

void playAudio() {
    file = new AudioFileSourceSPIFFS("/music.wav");
    wav = new AudioGeneratorWAV();
    
    if (wav->begin(file, out)) {
        Serial.println("Playing audio...");
        while (wav->isRunning()) {
            wav->loop();
        }
        wav->stop();
        delete wav;
        delete file;
        Serial.println("Playback finished!");
    } else {
        Serial.println("Failed to start WAV playback!");
    }
}
