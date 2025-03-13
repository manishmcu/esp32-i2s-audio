# ESP I2S Audio Setup  

### **1. Install ESP32FS Plugin**  
- Download ESP32FS: [GitHub Link](https://github.com/me-no-dev/arduino-esp32fs-plugin/releases)  
- Unzip and place `esp32fs.jar` inside:  
C:\Users\manis\Documents\Arduino\tools\ESP32FS\tool\esp32fs.jar

### **2. ESP32 I2S Connection**  
If your DAC module has only L, G, and B input pins, use the following connections:  

| DAC Module Pin | ESP32 Pin  |
|---------------|-----------|
| L (Data In)   | GPIO 22 (DOUT) |
| G (Ground)    | GND       |
| Power+        | 3.3V or 5V |
| B (Mute)      | Pull HIGH (if needed) |

### **3. Create a Voice Audio File**  
- Generate text-to-speech audio: [TTSMP3](https://ttsmp3.com/)  
- Convert to WAV format: [Audio Trimmer](https://audiotrimmer.com/online-wav-converter/)  
- Upload your file  
- Choose **44.1kHz, 16-bit PCM, Mono**  
- Convert and download  
- Rename file to **music.wav**  

### **4. Project Folder Structure**  
/Your_Project_Folder 
│── /data <-- SPIFFS file storage 

│ ├── music.wav <-- 16-bit PCM, Mono, ≤ 44.1kHz 

│── Your_Project.ino <-- Arduino code file


### **5. Important Notes**  
🚨 **Do NOT connect GPIO22 (Audio Pin) while uploading the code.**  

### **6. Upload Steps**  
✅ **1️⃣ Upload Your Code (Main Sketch)**  
- Click the **Upload (Arrow)** button in the Arduino IDE.  
- This uploads the ESP32 program to flash memory.  

✅ **2️⃣ Upload Audio File to SPIFFS**  
- Go to **Tools > ESP32 Sketch Data Upload**  
- This uploads `music.wav` to the ESP32’s SPIFFS storage.  

✅ **3️⃣ Reset and Play**  
- Press the **ESP32 Reset** button after both uploads are complete.  
- Open **Serial Monitor (115200 baud)** to check if playback starts.  
