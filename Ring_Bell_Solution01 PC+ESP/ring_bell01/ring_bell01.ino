#include <WiFi.h>
#include <HTTPClient.h>

// WiFi credentials
const char* ssid = "Digitaiken";
const char* password = "Welcome@123";

// Robot IP and Point ID
const char* robot_ip = "192.168.1.22";
const char* point_id = "B";

// Server URL
String serverUrl = "http://" + String(robot_ip) + ":5000/status";

// LED pin
const int ledPin = 23;

void setup() {
    Serial.begin(115200);
    pinMode(ledPin, OUTPUT);
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi");
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nConnected to WiFi");
}

void loop() {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(serverUrl);
        int httpResponseCode = http.GET();
        
        if (httpResponseCode == 200) {
            String payload = http.getString();
            Serial.println("Response: " + payload);
            
            // Parse JSON manually
            if (payload.indexOf("\"arrive_stat\":\"near\"") >= 0 && payload.indexOf("\"point_id\":\"" + String(point_id) + "\"") >= 0) {
                Serial.println("Near B - Blinking LED");
                for (int i = 0; i < 5; i++) { // Blink 5 times before rechecking
                    digitalWrite(ledPin, HIGH);
                    delay(200);
                    digitalWrite(ledPin, LOW);
                    delay(200);
                }
            } else if (payload.indexOf("\"arrive_stat\":\"arrived\"") >= 0 && payload.indexOf("\"point_id\":\"" + String(point_id) + "\"") >= 0) {
                Serial.println("Arrived - LED ON");
                digitalWrite(ledPin, HIGH);
            } else {
                Serial.println("No match - LED OFF");
                digitalWrite(ledPin, LOW);
            }
        } else {
            Serial.print("Error on HTTP request: ");
            Serial.println(httpResponseCode);
        }
        http.end();
    } else {
        Serial.println("WiFi Disconnected");
    }
    delay(1000); // Check every second
}
