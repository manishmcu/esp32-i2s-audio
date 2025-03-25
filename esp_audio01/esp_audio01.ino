#include "SPIFFS.h"  // Using SPIFFS
#include "AudioOutputI2S.h"
#include "AudioGeneratorWAV.h"
#include "AudioFileSourceSPIFFS.h"

AudioGeneratorWAV *wav;
AudioFileSourceSPIFFS *file;
AudioOutputI2S *out;

void setup() {
    Serial.begin(115200);
    delay(1000);  // Short delay for stable startup
    Serial.println("Initializing SPIFFS...");
    
    if (!SPIFFS.begin(true)) {  
        Serial.println("SPIFFS Mount Failed!");
        return;
    }

    Serial.println("SPIFFS Mounted Successfully!");

    // Open WAV file
    file = new AudioFileSourceSPIFFS("/music.wav");
    
    // Configure I2S output with higher bit depth
    out = new AudioOutputI2S();
    out->SetPinout(25, 26, 22);  // BCK = 25, WS (LRCLK) = 26, DOUT = 22 (adjust if needed)
    out->SetGain();  // Set volume (0.0 to 1.0)

    wav = new AudioGeneratorWAV();
    
    if (wav->begin(file, out)) {
        Serial.println("Playback started...");
    } else {
        Serial.println("Failed to start WAV playback!");
    }
}

void loop() {
    if (wav->isRunning()) {
        wav->loop();
    } else {
        wav->stop();
        Serial.println("Playback finished!");
        while (1);
    }
}
