from machine import Pin
import neopixel
import time
import sys
import select

# Configure the WS2812B
LED_PIN = 0  # GPIO pin connected to the LED data line
NUM_LEDS = 1  # Number of LEDs in your strip
np = neopixel.NeoPixel(Pin(LED_PIN), NUM_LEDS)

# Teams status colors (RGB values)
COLORS = {
    'Available': (0, 255, 0),      # Green
    'Busy': (255, 0, 0),           # Red
    'BeRightBack': (255, 255, 0),  # Yellow
    'Away': (255, 255, 0),         # Yellow
    'DoNotDisturb': (128, 0, 128), # Purple
    'Offline': (128, 128, 128),    # Gray
    'InACall': (255, 0, 0),        # Red
    'InAMeeting': (255, 0, 0),     # Red
    'Presenting': (255, 0, 0),     # Red
}

def set_color(color):
    """Set the LED to a specific color"""
    for i in range(NUM_LEDS):
        np[i] = color
    np.write()

def pulse_color(color, duration=2):
    """Pulse effect for the LED - breathe in and out"""
    steps = 50
    for step in range(steps):
        # Fixed brightness calculation: 1.0 at edges, 0.0 at center
        brightness = 1.0 - abs(step - steps/2) / (steps/2)
        adjusted_color = tuple(int(c * brightness) for c in color)
        for i in range(NUM_LEDS):
            np[i] = adjusted_color
        np.write()
        time.sleep(duration / steps)

# Initialize LED to offline state
set_color(COLORS['Offline'])
print("Busylight ready - waiting for status updates...")

# Buffer for incoming serial data
input_buffer = ""

# Main loop - read commands from USB serial
while True:
    try:
        # Check if data is available on stdin (USB serial)
        # MicroPython's sys.stdin.read() is non-blocking when data is available
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            # Read available character
            char = sys.stdin.read(1)

            if char == '\n':
                # End of line - process the status
                status = input_buffer.strip()
                input_buffer = ""  # Clear buffer

                if status in COLORS:
                    color = COLORS[status]
                    if status in ['Busy', 'InACall', 'InAMeeting', 'DoNotDisturb']:
                        # Solid color for busy states
                        set_color(color)
                    else:
                        # Solid color for available states
                        # (can change to pulse_color for breathing effect)
                        set_color(color)
                    print(f"Status updated: {status}")
                elif status:  # Non-empty but unknown status
                    print(f"Unknown status: {status}")
            else:
                # Add character to buffer
                input_buffer += char

                # Prevent buffer overflow
                if len(input_buffer) > 50:
                    input_buffer = ""

    except Exception as e:
        print(f"Error: {e}")
        input_buffer = ""  # Clear buffer on error

    # Small delay to prevent CPU spinning at 100%
    time.sleep(0.01)  # 10ms delay