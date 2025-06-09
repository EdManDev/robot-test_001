# Safe Raspberry Pi Robot Car Controller

## Features
- ROS 2 Humble Compatibility
- L298N Motor Driver Integration
- Web Interface Control (Port 8080)
- Hardware Watchdog Safety System
- Auto-Stop Mechanism (2s timeout)
- Emergency Stop Functionality
- PWM Speed Control (70% default)
- IP Auto-Detection
- Mobile-Friendly Web UI

## Prerequisites
- Raspberry Pi 4B with Ubuntu 22.04
- ROS 2 Humble installation
- Python 3.8+
- L298N Motor Driver
- Motor Power Supply (7-12V)

## Installation
```bash
sudo apt install python3-pip
pip install rclpy RPi.GPIO
git clone [your-repository-url]
cd Raspberry/
chmod +x index.py
```

## Usage
```bash
./index.py
```
Access web interface at: http://[PI_IP]:8080

## Safety Mechanisms
1. Software Watchdog (2s timeout)
2. Hardware Watchdog (GPIO 7)
3. Emergency Stop Web Endpoint
4. Auto-cleanup on shutdown
5. Connection monitoring

## GPIO Configuration (BCM)
| Function        | GPIO | Physical Pin |
|-----------------|------|--------------|
| Motor A Dir 1   | 23   | 16           |
| Motor A Dir 2   | 24   | 18           |
| Motor B Dir 1   | 25   | 22           |
| Motor B Dir 2   | 8    | 24           |
| Motor A Enable  | 18   | 12           |
| Motor B Enable  | 12   | 32           |
| Hardware Watchdog| 7    | 26           |

## API Overview
- ROS 2 Topics:
  - /cmd_vel (Twist messages)
  - /robot_command (String messages)
  - /robot_status (Status updates)

- HTTP Endpoints:
  - /control?cmd=[command]
  - /emergency_stop
  - /status

## Web Interface Features
- Real-time status monitoring
- Touch-friendly controls
- Speed slider (0-100%)
- Keyboard controls (WASD/Arrows)
- Connection health checks
- Automatic emergency stop on disconnect

Physical Pin    GPIO (BCM)    L298N Pin    Wire Color Suggestion
──────────────────────────────────────────────────────────────
Pin 16          GPIO 23   →   IN1         Red (Motor A Dir 1)
Pin 18          GPIO 24   →   IN2         Orange (Motor A Dir 2)  
Pin 22          GPIO 25   →   IN3         Yellow (Motor B Dir 1)
Pin 24          GPIO 8    →   IN4         Green (Motor B Dir 2)
Pin 12          GPIO 18   →   ENA         Blue (Motor A Enable)
Pin 32          GPIO 12   →   ENB         Purple (Motor B Enable)
Pin 2           5V        →   VCC         Red (Power)
Pin 6           GND       →   GND         Black (Ground)


.   3.3V  [1] [2]  5V      ← Pin 2 (5V to L298N VCC)
          [3] [4]  5V
          [5] [6]  GND     ← Pin 6 (GND to L298N GND)
          [7] [8]
     GND  [9] [10]
         [11] [12] GPIO18  ← Pin 12 (ENA - Motor A Enable)
         [13] [14] GND
         [15] [16] GPIO23  ← Pin 16 (IN1 - Motor A Dir 1)
         [17] [18] GPIO24  ← Pin 18 (IN2 - Motor A Dir 2)
         [19] [20] GND
         [21] [22] GPIO25  ← Pin 22 (IN3 - Motor B Dir 1)
   GPIO8 [23] [24] GPIO8   ← Pin 24 (IN4 - Motor B Dir 2)
         [25] [26]
         [27] [28]
         [29] [30] GND
         [31] [32] GPIO12  ← Pin 32 (ENB - Motor B Enable)