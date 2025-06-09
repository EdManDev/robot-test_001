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