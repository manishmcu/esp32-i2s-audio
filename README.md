# ESP32 Audio Playback with MAX98357A and SPIFFS

## 1. Install ESP32FS Plugin
Download the ESP32FS plugin from:
👉 [ESP32FS GitHub Releases](https://github.com/me-no-dev/arduino-esp32fs-plugin/releases)

Unzip and place `esp32fs.jar` in the following directory:
```
C:\Users\manis\Documents\Arduino\tools\ESP32FS\tool\esp32fs.jar
```

## 2. Use Compatible Arduino IDE
Use **Arduino IDE version 1.8.19 or lower** to ensure compatibility.

## 3. ESP32 I2S Wiring with MAX98357A

| MAX98357A | ESP32  |
|-----------|--------|
| Vin       | 3.3V or 5V |
| GND       | GND    |
| LRC (LRCLK) | GPIO 25 *(check code)* |
| BCLK (Bit Clk) | GPIO 26 *(check code)* |
| DIN (Data In) | GPIO 22 |
| SD (Shutdown) | *(Not used)* |

## 4. Prepare Your Audio File
### 4.1 Create a Voice Audio File
Use [TTSMP3](https://ttsmp3.com/) to generate a voice file and download it.

### 4.2 Convert to WAV Format
Use [AudioTrimmer](https://audiotrimmer.com/online-wav-converter/) to convert the file:
- Upload your audio file.
- Choose **44.1kHz, 16-bit PCM, Mono**.
- Convert and download.
- Rename as `music.wav`.

## 5. Organize Project Files
Structure your project directory as follows:
```
/Your_Project_Folder
│── /data               <-- SPIFFS file storage folder
│   ├── music.wav       <-- Audio file (16-bit PCM, Mono, ≤ 44.1kHz)
│── Your_Project.ino    <-- Arduino code file
```

## 6. Uploading to ESP32
🚨 **Don't connect GPIO22 (Audio Pin) while uploading the code!**

### Step 1️⃣: Upload Your Main Sketch
Click the **Upload (Arrow)** button in the Arduino IDE to flash the ESP32 program.

### Step 2️⃣: Upload Audio File to SPIFFS
Go to **Tools > ESP32 Sketch Data Upload** in Arduino IDE.

### Step 3️⃣: Reset and Play
- Press the **ESP32 Reset button** after both uploads are complete.
- Open **Serial Monitor (115200 baud)** to check playback status.

🎶 Your ESP32 is now set up for audio playback using MAX98357A and SPIFFS! 🎶

