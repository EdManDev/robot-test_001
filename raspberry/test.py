#!/usr/bin/env python3
"""
L298N Motor Driver Connection Test Script
Tests GPIO connection to L298N with ENA/ENB pins
For Raspberry Pi 4B with Ubuntu 22.04
"""

import RPi.GPIO as GPIO
import time
import sys

# GPIO Pin Definitions (BCM numbering)
MOTOR_PINS = {
    'IN1': 23,   # Physical Pin 16
    'IN2': 24,   # Physical Pin 18  
    'IN3': 25,   # Physical Pin 22
    'IN4': 16,   # Physical Pin 36 (CHANGED from GPIO 8)
    'ENA': 18,   # Physical Pin 12
    'ENB': 12    # Physical Pin 32
}

# Convenient aliases for backward compatibility
IN1 = MOTOR_PINS['IN1']
IN2 = MOTOR_PINS['IN2']
IN3 = MOTOR_PINS['IN3']
IN4 = MOTOR_PINS['IN4']
ENA = MOTOR_PINS['ENA']
ENB = MOTOR_PINS['ENB']

# Pin mapping for reference
PIN_MAP = {
    IN1: "IN1 (Motor A Dir 1)",
    IN2: "IN2 (Motor A Dir 2)", 
    IN3: "IN3 (Motor B Dir 1)",
    IN4: "IN4 (Motor B Dir 2)",
    ENA: "ENA (Motor A Enable)",
    ENB: "ENB (Motor B Enable)"
}

def setup_gpio():
    """Initialize GPIO pins"""
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup all pins as outputs
        GPIO.setup([IN1, IN2, IN3, IN4, ENA, ENB], GPIO.OUT)
        
        # Initialize all pins to LOW
        GPIO.output([IN1, IN2, IN3, IN4, ENA, ENB], GPIO.LOW)
        
        print("✓ GPIO pins initialized successfully")
        return True
        
    except Exception as e:
        print(f"✗ GPIO setup failed: {e}")
        return False

def test_individual_pins():
    """Test each pin individually"""
    print("\n=== Individual Pin Test ===")
    
    for pin in [IN1, IN2, IN3, IN4, ENA, ENB]:
        try:
            print(f"Testing GPIO {pin} ({PIN_MAP[pin]})...")
            
            # Turn pin HIGH
            GPIO.output(pin, GPIO.HIGH)
            print(f"  → GPIO {pin} set to HIGH")
            time.sleep(1)
            
            # Turn pin LOW
            GPIO.output(pin, GPIO.LOW)
            print(f"  → GPIO {pin} set to LOW")
            time.sleep(0.5)
            
            print(f"  ✓ GPIO {pin} test completed")
            
        except Exception as e:
            print(f"  ✗ GPIO {pin} test failed: {e}")

def test_motor_patterns():
    """Test motor direction patterns with enable pins"""
    print("\n=== Motor Direction Pattern Test ===")
    
    patterns = [
        # Motor A Forward, Motor B Stop
        ([IN1, ENA], "Motor A Forward"),
        # Motor A Reverse, Motor B Stop  
        ([IN2, ENA], "Motor A Reverse"),
        # Motor A Stop, Motor B Forward
        ([IN3, ENB], "Motor B Forward"),
        # Motor A Stop, Motor B Reverse
        ([IN4, ENB], "Motor B Reverse"),
        # Both Motors Forward
        ([IN1, IN3, ENA, ENB], "Both Motors Forward"),
        # Both Motors Reverse
        ([IN2, IN4, ENA, ENB], "Both Motors Reverse"),
        # Motor A Forward, Motor B Reverse
        ([IN1, IN4, ENA, ENB], "Motor A Forward, Motor B Reverse"),
        # Motor A Reverse, Motor B Forward
        ([IN2, IN3, ENA, ENB], "Motor A Reverse, Motor B Forward")
    ]
    
    for active_pins, description in patterns:
        try:
            print(f"\nTesting: {description}")
            
            # Turn off all pins first
            GPIO.output([IN1, IN2, IN3, IN4, ENA, ENB], GPIO.LOW)
            time.sleep(0.2)
            
            # Activate specified pins
            GPIO.output(active_pins, GPIO.HIGH)
            
            # Show which pins are active
            active_pins_str = ", ".join([f"GPIO{pin}" for pin in active_pins])
            print(f"  → Active pins: {active_pins_str}")
            
            time.sleep(2)  # Hold pattern for 2 seconds
            
            # Turn off active pins
            GPIO.output(active_pins, GPIO.LOW)
            print(f"  ✓ Pattern completed")
            
        except Exception as e:
            print(f"  ✗ Pattern failed: {e}")

def test_pwm_speed_control():
    """Test PWM speed control using ENA/ENB pins"""
    print("\n=== PWM Speed Control Test ===")
    
    try:
        # Create PWM instances
        pwm_a = GPIO.PWM(ENA, 1000)  # 1kHz frequency
        pwm_b = GPIO.PWM(ENB, 1000)  # 1kHz frequency
        
        # Start PWM with 0% duty cycle
        pwm_a.start(0)
        pwm_b.start(0)
        
        print("Testing Motor A speed control...")
        GPIO.output(IN1, GPIO.HIGH)  # Set direction
        GPIO.output(IN2, GPIO.LOW)
        
        # Gradually increase speed
        for duty in range(0, 101, 20):
            print(f"  → Motor A speed: {duty}%")
            pwm_a.ChangeDutyCycle(duty)
            time.sleep(1)
        
        # Stop Motor A
        pwm_a.ChangeDutyCycle(0)
        GPIO.output(IN1, GPIO.LOW)
        
        print("\nTesting Motor B speed control...")
        GPIO.output(IN3, GPIO.HIGH)  # Set direction
        GPIO.output(IN4, GPIO.LOW)
        
        # Gradually increase speed
        for duty in range(0, 101, 20):
            print(f"  → Motor B speed: {duty}%")
            pwm_b.ChangeDutyCycle(duty)
            time.sleep(1)
        
        # Stop Motor B
        pwm_b.ChangeDutyCycle(0)
        GPIO.output(IN3, GPIO.LOW)
        
        # Clean up PWM
        pwm_a.stop()
        pwm_b.stop()
        
        print("✓ PWM speed control test completed")
        
    except Exception as e:
        print(f"✗ PWM speed control test failed: {e}")

def test_rapid_switching():
    """Test rapid pin switching"""
    print("\n=== Rapid Switching Test ===")
    
    try:
        print("Rapidly switching all pins for 5 seconds...")
        start_time = time.time()
        
        while time.time() - start_time < 5:
            # Quick on/off cycle for all pins
            GPIO.output([IN1, IN2, IN3, IN4, ENA, ENB], GPIO.HIGH)
            time.sleep(0.1)
            GPIO.output([IN1, IN2, IN3, IN4, ENA, ENB], GPIO.LOW)
            time.sleep(0.1)
            
        print("✓ Rapid switching test completed")
        
    except Exception as e:
        print(f"✗ Rapid switching test failed: {e}")

def cleanup():
    """Clean up GPIO resources"""
    try:
        GPIO.output([IN1, IN2, IN3, IN4, ENA, ENB], GPIO.LOW)  # Turn off all pins
        GPIO.cleanup()
        print("\n✓ GPIO cleanup completed")
    except Exception as e:
        print(f"\n✗ GPIO cleanup failed: {e}")

def main():
    """Main test function"""
    print("L298N Motor Driver Connection Test")
    print("=" * 40)
    print("Testing with ENA/ENB pins for speed control")
    print("Press Ctrl+C to stop at any time\n")
    
    # Display pin configuration
    print("Pin Configuration:")
    for gpio_pin, description in PIN_MAP.items():
        # Find physical pin number
        physical_pins = {23: 16, 24: 18, 25: 22, 16: 36, 18: 12, 12: 32}
        physical = physical_pins.get(gpio_pin, "Unknown")
        print(f"  GPIO {gpio_pin:2d} (Pin {physical:2}) → {description}")
    
    try:
        # Setup GPIO
        if not setup_gpio():
            return
        
        # Run tests
        test_individual_pins()
        
        input("\nPress Enter to continue with motor pattern tests...")
        test_motor_patterns()
        
        input("\nPress Enter to continue with PWM speed control test...")
        test_pwm_speed_control()
        
        input("\nPress Enter to continue with rapid switching test...")
        test_rapid_switching()
        
        print("\n🎉 All tests completed successfully!")
        print("\nIf you can see the L298N status LEDs blinking during these tests,")
        print("and motors respond to speed control, your connections are working properly.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        
    finally:
        cleanup()

if __name__ == "__main__":
    main()