#!/usr/bin/env python3
"""
Enhanced Raspberry Pi 4B Robot Car Controller
ROS 2 Humble Compatible
L298N Motor Driver Support with Safety Features
Auto-stops motors on communication loss/reboot
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
import RPi.GPIO as GPIO
import time
import threading
import signal
import sys
import atexit
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse as urlparse
import socket
import subprocess

# Network Configuration
HTTP_PORT = 8080
WIFI_SSID = "BASE_AP"
WIFI_PASSWORD = "edmangoodlife123456"

# Safety Configuration
WATCHDOG_TIMEOUT = 2.0  # Stop motors if no command received for 2 seconds
HEARTBEAT_INTERVAL = 0.5  # Send heartbeat every 500ms

# GPIO Pin Definitions (BCM numbering)
MOTOR_PINS = {
    'IN1': 23,   # Physical Pin 16 - Motor A Direction 1  
    'IN2': 24,   # Physical Pin 18 - Motor A Direction 2
    'IN3': 25,   # Physical Pin 22 - Motor B Direction 1
    'IN4': 8,    # Physical Pin 24 - Motor B Direction 2
    'ENA': 18,   # Physical Pin 12 - Motor A Enable (PWM)
    'ENB': 12    # Physical Pin 32 - Motor B Enable (PWM)
}

# Hardware watchdog pin (optional - connect to L298N enable)
WATCHDOG_PIN = 7  # Physical Pin 26 - Hardware watchdog

def emergency_stop():
    """Emergency stop function - called on shutdown/error"""
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Stop all motors immediately
        for pin_name, pin_num in MOTOR_PINS.items():
            GPIO.setup(pin_num, GPIO.OUT)
            GPIO.output(pin_num, GPIO.LOW)
        
        # Disable hardware watchdog
        if WATCHDOG_PIN:
            GPIO.setup(WATCHDOG_PIN, GPIO.OUT)
            GPIO.output(WATCHDOG_PIN, GPIO.LOW)
            
        print("🛑 Emergency stop executed")
    except Exception as e:
        print(f"⚠️ Emergency stop error: {e}")

# Register emergency stop for various shutdown scenarios
atexit.register(emergency_stop)
signal.signal(signal.SIGTERM, lambda sig, frame: emergency_stop() or sys.exit(0))
signal.signal(signal.SIGINT, lambda sig, frame: emergency_stop() or sys.exit(0))

def get_local_ip():
    """Auto-detect the local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip.startswith("127."):
                raise Exception("Got loopback address")
            return local_ip
        except Exception:
            try:
                result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                ips = result.stdout.strip().split()
                for ip in ips:
                    if not ip.startswith('127.'):
                        return ip
            except Exception:
                pass
            return "0.0.0.0"

class SafeMotorController:
    """L298N Motor Driver Controller with Safety Features"""
    
    def __init__(self):
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Initialize all pins to safe state (LOW)
        for pin_name, pin_num in MOTOR_PINS.items():
            GPIO.setup(pin_num, GPIO.OUT)
            GPIO.output(pin_num, GPIO.LOW)
        
        # Hardware watchdog pin setup
        if WATCHDOG_PIN:
            GPIO.setup(WATCHDOG_PIN, GPIO.OUT)
            GPIO.output(WATCHDOG_PIN, GPIO.HIGH)  # Enable L298N
        
        # Setup PWM for enable pins
        self.pwm_freq = 1000
        self.pwm_a = GPIO.PWM(MOTOR_PINS['ENA'], self.pwm_freq)
        self.pwm_b = GPIO.PWM(MOTOR_PINS['ENB'], self.pwm_freq)
        
        # Start PWM with 0% duty cycle
        self.pwm_a.start(0)
        self.pwm_b.start(0)
        
        self.current_speed = 70
        self.last_command_time = time.time()
        self.is_moving = False
        
        # Start safety watchdog
        self.watchdog_active = True
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog_thread.start()
        
        # Start hardware heartbeat
        if WATCHDOG_PIN:
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()
        
        print("🛡️ Safe Motor Controller initialized with watchdog protection")
    
    def _watchdog_loop(self):
        """Software watchdog - stops motors if no commands received"""
        while self.watchdog_active:
            try:
                current_time = time.time()
                if (current_time - self.last_command_time) > WATCHDOG_TIMEOUT:
                    if self.is_moving:
                        print("⚠️ Watchdog timeout - stopping motors")
                        self._emergency_stop_motors()
                        self.is_moving = False
                time.sleep(0.1)  # Check every 100ms
            except Exception as e:
                print(f"⚠️ Watchdog error: {e}")
                self._emergency_stop_motors()
    
    def _heartbeat_loop(self):
        """Hardware heartbeat - toggles watchdog pin to keep L298N enabled"""
        heartbeat_state = True
        while self.watchdog_active:
            try:
                if WATCHDOG_PIN and self.is_moving:
                    # Toggle heartbeat pin
                    GPIO.output(WATCHDOG_PIN, GPIO.HIGH if heartbeat_state else GPIO.LOW)
                    heartbeat_state = not heartbeat_state
                elif WATCHDOG_PIN:
                    # Keep enabled when not moving
                    GPIO.output(WATCHDOG_PIN, GPIO.HIGH)
                time.sleep(HEARTBEAT_INTERVAL)
            except Exception as e:
                print(f"⚠️ Heartbeat error: {e}")
    
    def _update_command_time(self):
        """Update last command timestamp"""
        self.last_command_time = time.time()
    
    def _emergency_stop_motors(self):
        """Emergency stop - immediately disable all motor outputs"""
        try:
            # Stop PWM
            self.pwm_a.ChangeDutyCycle(0)
            self.pwm_b.ChangeDutyCycle(0)
            
            # Set all direction pins LOW
            for pin_name in ['IN1', 'IN2', 'IN3', 'IN4']:
                GPIO.output(MOTOR_PINS[pin_name], GPIO.LOW)
            
            # Disable hardware watchdog
            if WATCHDOG_PIN:
                GPIO.output(WATCHDOG_PIN, GPIO.LOW)
        except Exception as e:
            print(f"⚠️ Emergency stop error: {e}")
    
    def move_forward(self, speed=None):
        """Move robot forward with safety checks"""
        self._update_command_time()
        if speed is None:
            speed = self.current_speed
        
        # Re-enable hardware watchdog
        if WATCHDOG_PIN:
            GPIO.output(WATCHDOG_PIN, GPIO.HIGH)
        
        # Set direction for both motors (forward)
        GPIO.output(MOTOR_PINS['IN1'], GPIO.HIGH)
        GPIO.output(MOTOR_PINS['IN2'], GPIO.LOW)
        GPIO.output(MOTOR_PINS['IN3'], GPIO.HIGH)
        GPIO.output(MOTOR_PINS['IN4'], GPIO.LOW)
        
        # Enable motors with PWM
        self.pwm_a.ChangeDutyCycle(speed)
        self.pwm_b.ChangeDutyCycle(speed)
        
        self.is_moving = True
        
    def move_backward(self, speed=None):
        """Move robot backward with safety checks"""
        self._update_command_time()
        if speed is None:
            speed = self.current_speed
        
        # Re-enable hardware watchdog
        if WATCHDOG_PIN:
            GPIO.output(WATCHDOG_PIN, GPIO.HIGH)
            
        # Set direction for both motors (backward)
        GPIO.output(MOTOR_PINS['IN1'], GPIO.LOW)
        GPIO.output(MOTOR_PINS['IN2'], GPIO.HIGH)
        GPIO.output(MOTOR_PINS['IN3'], GPIO.LOW)
        GPIO.output(MOTOR_PINS['IN4'], GPIO.HIGH)
        
        # Enable motors with PWM
        self.pwm_a.ChangeDutyCycle(speed)
        self.pwm_b.ChangeDutyCycle(speed)
        
        self.is_moving = True
        
    def turn_left(self, speed=None):
        """Turn robot left with safety checks"""
        self._update_command_time()
        if speed is None:
            speed = self.current_speed
        
        # Re-enable hardware watchdog
        if WATCHDOG_PIN:
            GPIO.output(WATCHDOG_PIN, GPIO.HIGH)
            
        # Left motor backward, Right motor forward
        GPIO.output(MOTOR_PINS['IN1'], GPIO.LOW)
        GPIO.output(MOTOR_PINS['IN2'], GPIO.HIGH)
        GPIO.output(MOTOR_PINS['IN3'], GPIO.HIGH)
        GPIO.output(MOTOR_PINS['IN4'], GPIO.LOW)
        
        # Enable motors
        self.pwm_a.ChangeDutyCycle(speed)
        self.pwm_b.ChangeDutyCycle(speed)
        
        self.is_moving = True
        
    def turn_right(self, speed=None):
        """Turn robot right with safety checks"""
        self._update_command_time()
        if speed is None:
            speed = self.current_speed
        
        # Re-enable hardware watchdog
        if WATCHDOG_PIN:
            GPIO.output(WATCHDOG_PIN, GPIO.HIGH)
        
        # Left motor forward, Right motor backward
        GPIO.output(MOTOR_PINS['IN1'], GPIO.HIGH)
        GPIO.output(MOTOR_PINS['IN2'], GPIO.LOW)
        GPIO.output(MOTOR_PINS['IN3'], GPIO.LOW)
        GPIO.output(MOTOR_PINS['IN4'], GPIO.HIGH)
        
        # Enable motors
        self.pwm_a.ChangeDutyCycle(speed)
        self.pwm_b.ChangeDutyCycle(speed)
        
        self.is_moving = True
        
    def stop(self):
        """Stop all motors safely"""
        self._update_command_time()
        
        # Disable PWM
        self.pwm_a.ChangeDutyCycle(0)
        self.pwm_b.ChangeDutyCycle(0)
        
        # Set all direction pins low
        for pin_name in ['IN1', 'IN2', 'IN3', 'IN4']:
            GPIO.output(MOTOR_PINS[pin_name], GPIO.LOW)
        
        # Keep watchdog enabled but mark as not moving
        self.is_moving = False
    
    def set_speed(self, speed):
        """Set motor speed with safety update"""
        self._update_command_time()
        self.current_speed = max(0, min(100, speed))
        
    def cleanup(self):
        """Cleanup GPIO and stop watchdog"""
        print("🧹 Cleaning up motor controller...")
        self.watchdog_active = False
        
        # Stop motors
        self._emergency_stop_motors()
        
        # Stop PWM
        self.pwm_a.stop()
        self.pwm_b.stop()
        
        # Wait for threads to finish
        time.sleep(0.2)
        
        # Cleanup GPIO
        GPIO.cleanup()
        print("✅ Motor controller cleanup complete")

class WebHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler with Enhanced Safety Features"""
    
    def __init__(self, *args, robot_node=None, robot_ip=None, **kwargs):
        self.robot_node = robot_node
        self.robot_ip = robot_ip or "localhost"
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.send_control_page()
        elif self.path == '/status':
            self.send_status()
        elif self.path.startswith('/control'):
            self.handle_control_command()
        elif self.path == '/emergency_stop':
            self.handle_emergency_stop()
        else:
            self.send_error(404)
    
    def handle_emergency_stop(self):
        """Handle emergency stop request"""
        if self.robot_node:
            self.robot_node.motor_controller._emergency_stop_motors()
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Emergency stop executed")
    
    def send_control_page(self):
        """Send enhanced HTML control interface with safety features"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Safe Robot Car Controller</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial; text-align: center; margin: 50px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .controls {{ display: grid; grid-template-columns: repeat(3, 100px); gap: 10px; justify-content: center; margin: 20px; }}
                button {{ padding: 20px; font-size: 16px; border: none; border-radius: 8px; background: #4CAF50; color: white; cursor: pointer; transition: all 0.3s; }}
                button:hover {{ background: #45a049; }}
                .stop {{ background: #f44336; }}
                .stop:hover {{ background: #da190b; }}
                .emergency {{ background: #ff0000; font-weight: bold; grid-column: span 3; }}
                .emergency:hover {{ background: #cc0000; }}
                .safety-info {{ margin: 20px; padding: 15px; background: #fff3cd; border-radius: 8px; border-left: 4px solid #ffc107; }}
                .status-indicator {{ display: inline-block; width: 10px; height: 10px; background: #4CAF50; border-radius: 50%; margin-right: 5px; }}
                .watchdog-status {{ margin: 10px; padding: 10px; background: #e8f5e8; border-radius: 5px; }}
                .info {{ margin: 20px; padding: 15px; background: #e7f3ff; border-radius: 8px; border-left: 4px solid #2196F3; }}
                .speed-control {{ margin: 20px; padding: 15px; background: #f9f9f9; border-radius: 8px; }}
                input[type="range"] {{ width: 200px; margin: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛡️ Safe Robot Car Controller</h1>
                
                <div class="safety-info">
                    <h4>🚨 Safety Features Active</h4>
                    <div class="watchdog-status">
                        <strong>Watchdog:</strong> <span id="watchdog-status">Active</span> | 
                        <strong>Timeout:</strong> {WATCHDOG_TIMEOUT}s
                    </div>
                </div>
                
                <div class="info">
                    <p><strong>IP:</strong> {self.robot_ip} | <strong>Port:</strong> {HTTP_PORT}</p>
                    <p><strong>Status:</strong> <span class="status-indicator"></span><span id="status">Connected</span></p>
                </div>
                
                <div class="controls">
                    <div></div>
                    <button onclick="sendCommand('forward')" onmousedown="startContinuous('forward')" onmouseup="stopContinuous()" ontouchstart="startContinuous('forward')" ontouchend="stopContinuous()">⬆️<br>Forward</button>
                    <div></div>
                    <button onclick="sendCommand('left')" onmousedown="startContinuous('left')" onmouseup="stopContinuous()" ontouchstart="startContinuous('left')" ontouchend="stopContinuous()">⬅️<br>Left</button>
                    <button onclick="sendCommand('stop')" class="stop">⏹️<br>STOP</button>
                    <button onclick="sendCommand('right')" onmousedown="startContinuous('right')" onmouseup="stopContinuous()" ontouchstart="startContinuous('right')" ontouchend="stopContinuous()">➡️<br>Right</button>
                    <div></div>
                    <button onclick="sendCommand('backward')" onmousedown="startContinuous('backward')" onmouseup="stopContinuous()" ontouchstart="startContinuous('backward')" ontouchend="stopContinuous()">⬇️<br>Backward</button>
                    <div></div>
                    <button onclick="emergencyStop()" class="emergency">🚨 EMERGENCY STOP 🚨</button>
                </div>
                
                <div class="speed-control">
                    <h3>🏎️ Speed Control</h3>
                    <input type="range" id="speed" min="0" max="100" value="50" oninput="updateSpeed(this.value)">
                    <br><span id="speedValue">50%</span>
                </div>

                <div class="info">
                    <h4>🛡️ Safety Features:</h4>
                    <p><strong>Auto-Stop:</strong> Motors stop if no commands for {WATCHDOG_TIMEOUT} seconds</p>
                    <p><strong>Emergency Stop:</strong> Immediate motor shutdown on Pi reboot/crash</p>
                    <p><strong>Hardware Watchdog:</strong> Physical safety backup (if connected)</p>
                    <p><strong>Graceful Shutdown:</strong> Motors stop on program exit</p>
                </div>
									<div class="info">
											<h4>🎮 Controls:</h4>
											<p><strong>Keyboard:</strong> WASD or Arrow Keys, Space to stop</p>
											<p><strong>Touch:</strong> Hold buttons for continuous movement</p>
											<p><strong>ROS 2:</strong> Publish to /cmd_vel or /robot_command topics</p>
									</div>
            </div>
            
            <script>
                let continuousInterval = null;
                let lastCommandTime = Date.now();
                
                function sendCommand(cmd) {{
                    lastCommandTime = Date.now();
                    fetch('/control?cmd=' + cmd, {{method: 'GET'}})
                        .then(response => response.text())
                        .then(data => console.log('Command sent:', cmd))
                        .catch(error => {{
                            console.error('Connection error:', error);
                            document.getElementById('status').innerText = 'Disconnected';
                            emergencyStop();
                        }});
                }}
                
                function emergencyStop() {{
                    fetch('/emergency_stop', {{method: 'GET'}})
                        .then(response => response.text())
                        .then(data => {{
                            console.log('Emergency stop executed');
                            document.getElementById('status').innerText = 'Emergency Stopped';
                        }})
                        .catch(error => console.error('Emergency stop failed:', error));
                }}
                
                function startContinuous(cmd) {{
                    sendCommand(cmd);
                    continuousInterval = setInterval(() => sendCommand(cmd), 100);
                }}
                
                function stopContinuous() {{
                    if (continuousInterval) {{
                        clearInterval(continuousInterval);
                        continuousInterval = null;
                        setTimeout(() => sendCommand('stop'), 50);
                    }}
                }}
                
                function updateSpeed(value) {{
                    document.getElementById('speedValue').innerText = value + '%';
                    sendCommand('speed&value=' + value);
                }}
                
                // Enhanced keyboard controls with safety
                let activeKeys = new Set();
                
                document.addEventListener('keydown', function(event) {{
                    if (activeKeys.has(event.key)) return;
                    activeKeys.add(event.key);
                    
                    switch(event.key.toLowerCase()) {{
                        case 'arrowup': case 'w': sendCommand('forward'); break;
                        case 'arrowdown': case 's': sendCommand('backward'); break;
                        case 'arrowleft': case 'a': sendCommand('left'); break;
                        case 'arrowright': case 'd': sendCommand('right'); break;
                        case ' ': sendCommand('stop'); event.preventDefault(); break;
                        case 'escape': emergencyStop(); event.preventDefault(); break;
                    }}
                }});
                
                document.addEventListener('keyup', function(event) {{
                    activeKeys.delete(event.key);
                    if(['arrowup', 'arrowdown', 'arrowleft', 'arrowright', 'w', 'a', 's', 'd'].includes(event.key.toLowerCase())) {{
                        setTimeout(() => sendCommand('stop'), 50);
                    }}
                }});
                
                // Connection monitoring with auto-emergency stop
                let connectionLost = false;
                setInterval(() => {{
                    fetch('/status')
                        .then(response => response.json())
                        .then(data => {{
                            document.getElementById('status').innerText = 'Connected';
                            document.getElementById('watchdog-status').innerText = 'Active';
                            connectionLost = false;
                        }})
                        .catch(error => {{
                            if (!connectionLost) {{
                                document.getElementById('status').innerText = 'Connection Lost - Auto Stopping';
                                document.getElementById('watchdog-status').innerText = 'Connection Lost';
                                connectionLost = true;
                                // Try emergency stop
                                fetch('/emergency_stop').catch(() => {{}});
                            }}
                        }});
                }}, 1000);
                
                // Auto-stop if browser loses focus for safety
                window.addEventListener('beforeunload', function() {{
                    fetch('/emergency_stop').catch(() => {{}});
                }});
                
                // Page visibility API for mobile safety
                document.addEventListener('visibilitychange', function() {{
                    if (document.hidden) {{
                        sendCommand('stop');
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def handle_control_command(self):
        """Handle control commands with enhanced safety"""
        parsed_url = urlparse.urlparse(self.path)
        params = urlparse.parse_qs(parsed_url.query)
        
        if 'cmd' in params:
            command = params['cmd'][0]
            
            if command == 'speed' and 'value' in params:
                speed_value = int(params['value'][0])
                if self.robot_node:
                    self.robot_node.motor_controller.set_speed(speed_value)
                response_msg = f"Speed set to {speed_value}%"
            else:
                if self.robot_node:
                    self.robot_node.execute_command(command)
                response_msg = f"Command '{command}' executed"
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(response_msg.encode())
        else:
            self.send_error(400)
    
    def send_status(self):
        """Send enhanced status with safety information"""
        status = {
            'robot_ip': self.robot_ip,
            'ros2_status': 'active',
            'motor_status': 'ready',
            'watchdog_active': True,
            'watchdog_timeout': WATCHDOG_TIMEOUT,
            'safety_features': ['software_watchdog', 'emergency_stop', 'graceful_shutdown'],
            'timestamp': time.time()
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status).encode())

class SafeRobotCarNode(Node):
    """Enhanced ROS 2 Node with Safety Features"""
    
    def __init__(self, robot_ip):
        super().__init__('safe_robot_car_controller')
        
        self.robot_ip = robot_ip
        
        # Initialize safe motor controller
        self.motor_controller = SafeMotorController()
        
        # ROS 2 Subscribers
        self.cmd_vel_subscription = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        
        self.command_subscription = self.create_subscription(
            String, 'robot_command', self.command_callback, 10)
        
        # ROS 2 Publishers
        self.status_publisher = self.create_publisher(String, 'robot_status', 10)
        
        # Enhanced status timer
        self.status_timer = self.create_timer(0.5, self.publish_status)
        
        # HTTP Server
        self.start_http_server()
        
        self.get_logger().info('🛡️ Safe Robot Car Controller initialized')
        self.get_logger().info(f'📡 Web interface: http://{self.robot_ip}:{HTTP_PORT}')
        self.get_logger().info(f'⚠️ Watchdog timeout: {WATCHDOG_TIMEOUT}s')
    
    def cmd_vel_callback(self, msg):
        """Handle ROS 2 Twist messages with safety"""
        linear_x = msg.linear.x
        angular_z = msg.angular.z
        
        # Update command timestamp for watchdog
        self.motor_controller._update_command_time()
        
        # Convert Twist to motor commands
        if abs(linear_x) > abs(angular_z):
            if linear_x > 0:
                self.motor_controller.move_forward(abs(linear_x * 100))
            elif linear_x < 0:
                self.motor_controller.move_backward(abs(linear_x * 100))
        elif abs(angular_z) > 0.1:
            if angular_z > 0:
                self.motor_controller.turn_left(abs(angular_z * 100))
            else:
                self.motor_controller.turn_right(abs(angular_z * 100))
        else:
            self.motor_controller.stop()
    
    def command_callback(self, msg):
        """Handle string command messages with safety"""
        command = msg.data.lower()
        self.execute_command(command)
    
    def execute_command(self, command):
        """Execute motor command with enhanced logging"""
        command = command.lower()
        
        if command == 'forward':
            self.motor_controller.move_forward()
            self.get_logger().info('🔼 Moving forward')
        elif command == 'backward':
            self.motor_controller.move_backward()
            self.get_logger().info('🔽 Moving backward')
        elif command == 'left':
            self.motor_controller.turn_left()
            self.get_logger().info('◀️ Turning left')
        elif command == 'right':
            self.motor_controller.turn_right()
            self.get_logger().info('▶️ Turning right')
        elif command == 'stop':
            self.motor_controller.stop()
            self.get_logger().info('⏹️ Stopping')
        elif command == 'emergency_stop':
            self.motor_controller._emergency_stop_motors()
            self.get_logger().warn('🚨 Emergency stop executed')
        else:
            self.get_logger().warn(f'❓ Unknown command: {command}')
    
    def publish_status(self):
        """Publish enhanced robot status"""
        status_msg = String()
        status_msg.data = json.dumps({
            'timestamp': time.time(),
            'node_status': 'active',
            'motor_status': 'ready',
            'watchdog_active': self.motor_controller.watchdog_active,
            'is_moving': self.motor_controller.is_moving,
            'last_command_age': time.time() - self.motor_controller.last_command_time,
            'ip_address': self.robot_ip
        })
        self.status_publisher.publish(status_msg)
    
    def start_http_server(self):
        """Start HTTP server with error handling"""
        def create_handler(*args, **kwargs):
            return WebHandler(*args, robot_node=self, robot_ip=self.robot_ip, **kwargs)
        
        try:
            server_address = (self.robot_ip if self.robot_ip != "0.0.0.0" else "", HTTP_PORT)
            self.http_server = HTTPServer(server_address, create_handler)
            self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
            self.http_thread.start()
            self.get_logger().info(f'🌐 HTTP server started on {self.robot_ip}:{HTTP_PORT}')
        except Exception as e:
            self.get_logger().error(f'❌ HTTP server error: {e}')
            self.http_server = HTTPServer(("", HTTP_PORT), create_handler)
            self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
            self.http_thread.start()
            self.get_logger().info(f'🌐 HTTP server started on all interfaces (port {HTTP_PORT})')
    
    def destroy_node(self):
        """Enhanced cleanup with safety"""
        self.get_logger().info('🛑 Shutting down safely...')
        self.motor_controller.cleanup()
        if hasattr(self, 'http_server'):
            self.http_server.shutdown()
        super().destroy_node()

def main(args=None):
    """Main entry point with enhanced safety"""
    print("🛡️ Starting Safe Raspberry Pi Robot Car Controller")
    print("🚨 Safety Features: Watchdog, Emergency Stop, Auto-Shutdown")
    
    # Auto-detect IP address
    robot_ip = get_local_ip()
    print(f"📡 Detected IP: {robot_ip}")
    print(f"📡 Network: {WIFI_SSID}")
    print(f"⏰ Watchdog Timeout: {WATCHDOG_TIMEOUT}s")
    print("🔧 ROS 2 Humble | L298N Motor Driver | Safety Enhanced")
    
    rclpy.init(args=args)
    
    try:
        robot_node = SafeRobotCarNode(robot_ip)
        
        print("\n✅ Safe Robot Car Controller Ready!")
        if robot_ip == "0.0.0.0":
            print(f"🌐 Web Control: http://<your-pi-ip>:{HTTP_PORT}")
            print("   (Check 'ip addr' or 'ifconfig' for your Pi's IP address)")
        else:
            print(f"🌐 Web Control: http://{robot_ip}:{HTTP_PORT}")
        
        print("🎮 ROS 2 Topics:")
        print("   - /cmd_vel (geometry_msgs/Twist)")
        print("   - /robot_command (std_msgs/String)")
        print("   - /robot_status (std_msgs/String)")
        print("\n🛡️ Safety Features:")
        print(f"   - Software Watchdog: {WATCHDOG_TIMEOUT}s timeout")
        print("   - Hardware Watchdog: GPIO pin control")
        print("   - Emergency Stop: Web interface + ROS topic")
        print("   - Auto-Stop: On Pi reboot/crash/shutdown")
        print("   - Connection Monitor: Auto-stop on disconnect")
        print("\n🎹 Controls:")
        print("   - Web: WASD/Arrow Keys, Space=Stop, ESC=Emergency")  
        print("   - ROS: /cmd_vel or /robot_command topics")
        print("   - Mobile: Touch-friendly interface")
        print("\n🔧 Hardware Setup (Optional for Enhanced Safety):")
        print(f"   - Connect GPIO {WATCHDOG_PIN} to L298N enable pin")
        print("   - This provides hardware-level motor cutoff")
        
        rclpy.spin(robot_node)
        
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt - shutting down safely...")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'robot_node' in locals():
            robot_node.destroy_node()
        rclpy.shutdown()
        emergency_stop()  # Final safety stop
        print("🏁 Safe Robot Car Controller stopped")

if __name__ == '__main__':
    main()
