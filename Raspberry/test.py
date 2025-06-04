#!/usr/bin/env python3
"""
L298N Motor Driver Connection Test Script
Tests GPIO connection to L298N without using ENA/ENB pins
For Raspberry Pi 4B with Ubuntu 22.04
"""

import RPi.GPIO as GPIO
import time
import sys

# GPIO pin definitions (BCM numbering)
IN1 = 23  # Pin 16 - Motor A Direction 1
IN2 = 24  # Pin 18 - Motor A Direction 2  
IN3 = 25  # Pin 22 - Motor B Direction 1
IN4 = 8   # Pin 24 - Motor B Direction 2

# Pin mapping for reference
PIN_MAP = {
    IN1: "IN1 (Motor A Dir 1)",
    IN2: "IN2 (Motor A Dir 2)", 
    IN3: "IN3 (Motor B Dir 1)",
    IN4: "IN4 (Motor B Dir 2)"
}

def setup_gpio():
    """Initialize GPIO pins"""
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup all pins as outputs
        GPIO.setup([IN1, IN2, IN3, IN4], GPIO.OUT)
        
        # Initialize all pins to LOW
        GPIO.output([IN1, IN2, IN3, IN4], GPIO.LOW)
        
        print("✓ GPIO pins initialized successfully")
        return True
        
    except Exception as e:
        print(f"✗ GPIO setup failed: {e}")
        return False

def test_individual_pins():
    """Test each pin individually"""
    print("\n=== Individual Pin Test ===")
    
    for pin in [IN1, IN2, IN3, IN4]:
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
    """Test motor direction patterns"""
    print("\n=== Motor Direction Pattern Test ===")
    
    patterns = [
        # Motor A Forward, Motor B Stop
        ([IN1], "Motor A Forward"),
        # Motor A Reverse, Motor B Stop  
        ([IN2], "Motor A Reverse"),
        # Motor A Stop, Motor B Forward
        ([IN3], "Motor B Forward"),
        # Motor A Stop, Motor B Reverse
        ([IN4], "Motor B Reverse"),
        # Both Motors Forward
        ([IN1, IN3], "Both Motors Forward"),
        # Both Motors Reverse
        ([IN2, IN4], "Both Motors Reverse"),
        # Motor A Forward, Motor B Reverse
        ([IN1, IN4], "Motor A Forward, Motor B Reverse"),
        # Motor A Reverse, Motor B Forward
        ([IN2, IN3], "Motor A Reverse, Motor B Forward")
    ]
    
    for active_pins, description in patterns:
        try:
            print(f"\nTesting: {description}")
            
            # Turn off all pins first
            GPIO.output([IN1, IN2, IN3, IN4], GPIO.LOW)
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

def test_rapid_switching():
    """Test rapid pin switching"""
    print("\n=== Rapid Switching Test ===")
    
    try:
        print("Rapidly switching all pins for 5 seconds...")
        start_time = time.time()
        
        while time.time() - start_time < 5:
            # Quick on/off cycle for all pins
            GPIO.output([IN1, IN2, IN3, IN4], GPIO.HIGH)
            time.sleep(0.1)
            GPIO.output([IN1, IN2, IN3, IN4], GPIO.LOW)
            time.sleep(0.1)
            
        print("✓ Rapid switching test completed")
        
    except Exception as e:
        print(f"✗ Rapid switching test failed: {e}")

def cleanup():
    """Clean up GPIO resources"""
    try:
        GPIO.output([IN1, IN2, IN3, IN4], GPIO.LOW)  # Turn off all pins
        GPIO.cleanup()
        print("\n✓ GPIO cleanup completed")
    except Exception as e:
        print(f"\n✗ GPIO cleanup failed: {e}")

def main():
    """Main test function"""
    print("L298N Motor Driver Connection Test")
    print("=" * 40)
    print("Testing without ENA/ENB pins")
    print("Press Ctrl+C to stop at any time\n")
    
    # Display pin configuration
    print("Pin Configuration:")
    for gpio_pin, description in PIN_MAP.items():
        print(f"  GPIO {gpio_pin:2d} → {description}")
    
    try:
        # Setup GPIO
        if not setup_gpio():
            return
        
        # Run tests
        test_individual_pins()
        
        input("\nPress Enter to continue with motor pattern tests...")
        test_motor_patterns()
        
        input("\nPress Enter to continue with rapid switching test...")
        test_rapid_switching()
        
        print("\n🎉 All tests completed successfully!")
        print("\nIf you can see the L298N status LEDs blinking during these tests,")
        print("your connections are working properly.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        
    finally:
        cleanup()

if __name__ == "__main__":
    main()
