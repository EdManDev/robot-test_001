# ESP32-CAM Robot Car

Smart Robot Car Kit ESP32 Camera Starter Kit with Tutorial Compatible with Arduino IDE

L298N dual H-Bridge motor driver


```bash
    sudo dmesg | grep ch341
```
OR
```bash
    sudo dmesg | grep ttyUSB
```

A WiFi-controlled robot car with live camera streaming built using ESP32-CAM module. Control the robot remotely through a web interface while viewing real-time camera feed.

## Features

- 🎥 **Live Camera Streaming** - Real-time MJPEG video stream
- 🎮 **Web-based Control** - Control robot through any web browser
- 📱 **Mobile Compatible** - Works on smartphones and tablets
- 🔧 **Simple Controls** - Forward, Backward, Left, Right, Stop
- 📡 **WiFi Connectivity** - Remote control over local network
- 🔧 **Static IP Configuration** - Predictable network addressing

## Hardware Requirements

### Main Components
- **ESP32-CAM** (AI Thinker model)
- **Motor Driver Board** (L298N)
- **2x DC Motors** (for robot car chassis)
- **Robot Car Chassis** with wheels
- **Jumper Wires**
- **Power Supply** (7-12V for motors, 5V for ESP32-CAM)

### Pin Configuration

| ESP32-CAM Pin | Motor Driver Pin | Function |
|---------------|-----------------|----------|
| GPIO 12       | IN1             | Motor 1 Control |
| GPIO 13       | IN2             | Motor 1 Control |
| GPIO 14       | IN3             | Motor 2 Control |
| GPIO 15       | IN4             | Motor 2 Control |

## Wiring Diagram

```
ESP32-CAM          L298N Motor Driver
---------          ------------------
GPIO 12     -->    IN1
GPIO 13     -->    IN2
GPIO 14     -->    IN3
GPIO 15     -->    IN4
GND         -->    GND
5V          -->    5V

Motor Driver       DC Motors
------------       ---------
OUT1        -->    Left Motor +
OUT2        -->    Left Motor -
OUT3        -->    Right Motor +
OUT4        -->    Right Motor -
```

## Software Setup

### Prerequisites
- Arduino IDE (1.8.19 or later)
- ESP32 Board Package
- Required Libraries (auto-installed with ESP32 package):
  - WiFi
  - esp_camera
  - WebServer

### Installation Steps

1. **Install ESP32 Board Package**
   ```
   File > Preferences > Additional Board Manager URLs:
   https://dl.espressif.com/dl/package_esp32_index.json
   ```

2. **Select Board**
   ```
   Tools > Board > ESP32 Arduino > AI Thinker ESP32-CAM
   ```

3. **Configure Upload Settings**
   ```
   Tools > Partition Scheme > Huge APP (3MB No OTA/1MB SPIFFS)
   Tools > Port > /dev/ttyUSB0 (or your port)
   ```

4. **Upload Code**
   - Connect ESP32-CAM to computer via USB-TTL adapter
   - Press and hold BOOT button on ESP32-CAM
   - Click Upload in Arduino IDE
   - Release BOOT button when upload starts

### Linux Permission Fix (if needed)
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Set port permissions (temporary)
sudo chmod 666 /dev/ttyUSB0

# Log out and log back in for group changes to take effect
```

## Configuration

### WiFi Settings
Update these lines in the code with your network details:
```cpp
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";
const IPAddress local_IP(192, 168, 8, 200);  // Change if needed
const IPAddress gateway(192, 168, 8, 1);     // Your router IP
```

### Motor Direction
If motors run in wrong direction, swap the motor control pins in code:
```cpp
// Example: If left turn goes right, swap IN1 and IN2
void turnLeft() {
  digitalWrite(IN1, HIGH);  // Change LOW to HIGH
  digitalWrite(IN2, LOW);   // Change HIGH to LOW
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}
```

## Usage

1. **Power On**
   - Connect power to ESP32-CAM and motor driver
   - Wait for WiFi connection (check Serial Monitor)

2. **Access Web Interface**
   - Open browser and go to: `http://192.168.8.200`
   - You should see the control interface with camera feed

3. **Control Robot**
   - **Forward** - Move robot forward
   - **Backward** - Move robot backward  
   - **Left** - Turn robot left
   - **Right** - Turn robot right
   - **Stop** - Stop all motors

## Network Access Points

- **Main Control Interface**: `http://192.168.8.200/` (Port 80)
- **Camera Stream Only**: `http://192.168.8.200:81/stream` (Port 81)

## Troubleshooting

### Upload Issues
- **Permission Denied**: Run `sudo chmod 666 /dev/ttyUSB0`
- **Port Not Found**: Check `ls /dev/ttyUSB*` or try `/dev/ttyACM0`
- **Upload Failed**: Hold BOOT button during upload

### Connection Issues
- **WiFi Not Connecting**: Check SSID/password
- **Can't Access Web**: Verify IP address in Serial Monitor
- **Static IP Conflicts**: Change `local_IP` to unused address

### Camera Issues
- **No Video**: Check camera ribbon cable connection
- **Poor Quality**: Adjust `jpeg_quality` (lower = better quality)
- **Slow Streaming**: Reduce `frame_size` to `FRAMESIZE_QVGA`

### Motor Issues
- **Motors Don't Move**: Check power supply and wiring
- **Wrong Direction**: Swap motor wires or modify code
- **Weak Movement**: Ensure adequate power supply (7-12V for motors)

## Customization

### Adjust Camera Settings
```cpp
config.frame_size = FRAMESIZE_VGA;    // Higher resolution
config.jpeg_quality = 5;              // Better quality (1-63, lower = better)
config.fb_count = 2;                  // Buffer frames
```

### Add Speed Control
```cpp
// Add PWM for speed control
int motorSpeed = 200;  // 0-255
analogWrite(IN1, motorSpeed);
```

### Add Sensors
```cpp
// Example: Add ultrasonic sensor for obstacle avoidance
#define TRIG_PIN 2
#define ECHO_PIN 4
```

## Performance Notes

- **Range**: Depends on WiFi signal strength
- **Latency**: ~100-500ms depending on network
- **Battery Life**: Varies with motors and usage
- **Streaming Quality**: QVGA @ ~10 FPS typical

## License

This project is open source and available under the MIT License.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support

For issues and questions:
- Check the troubleshooting section above
- Review ESP32-CAM documentation
- Check Arduino IDE error messages
- Verify hardware connections

---

**Enjoy your ESP32-CAM Robot Car! 🚗📷**
