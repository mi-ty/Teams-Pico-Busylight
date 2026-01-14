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
    """Pulse effect for the LED"""
    steps = 50
    for step in range(steps):
        brightness = abs(step - steps/2) / (steps/2)
        adjusted_color = tuple(int(c * brightness) for c in color)
        for i in range(NUM_LEDS):
            np[i] = adjusted_color
        np.write()
        time.sleep(duration / steps)

# Main loop - read commands from USB serial
while True:
    # Wait for status from computer via USB serial
    if select.select([sys.stdin], [], [], 0)[0]:
        status = sys.stdin.readline().strip()
        
        if status in COLORS:
            color = COLORS[status]
            if status in ['Busy', 'InACall', 'InAMeeting', 'DoNotDisturb']:
                # Solid color for busy states
                set_color(color)
            else:
                # Could add pulse for other states
                set_color(color)