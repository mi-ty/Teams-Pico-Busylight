import serial
import time
from datetime import datetime
import mss
import mss.tools

# Configure serial connection to Pico
PICO_PORT = 'COM3'  # Windows - change to /dev/ttyACM0 on Linux/Mac

# Enable debug mode (set to True for detailed logging)
DEBUG_MODE = True  # Change to False to disable debug output

# Teams status indicator pixel location (from Teams toolbar)
STATUS_PIXEL_X = 131
STATUS_PIXEL_Y = 34

# Color to status mapping (RGB values from Teams status indicator)
# These are approximate - may need adjustment based on your display
COLOR_TO_STATUS = {
    # Format: (R, G, B): 'StatusName'
    # Available - Green
    (146, 195, 83): 'Available',
    (148, 194, 84): 'Available',
    (147, 195, 83): 'Available',

    # Busy - Red
    (196, 49, 75): 'Busy',
    (197, 50, 76): 'Busy',
    (195, 48, 74): 'Busy',

    # Do Not Disturb - Red with line
    (191, 48, 74): 'DoNotDisturb',
    (192, 49, 75): 'DoNotDisturb',

    # Away - Yellow
    (255, 189, 17): 'Away',
    (254, 188, 16): 'Away',
    (255, 190, 18): 'Away',

    # Be Right Back - Yellow (clock icon)
    (255, 189, 17): 'BeRightBack',

    # Offline - Gray
    (143, 149, 158): 'Offline',
    (142, 148, 157): 'Offline',
    (144, 150, 159): 'Offline',

    # In a Call/Meeting - Red
    (196, 49, 75): 'InACall',

    # Presenting - Red
    (196, 49, 75): 'Presenting',
}

def get_pixel_color(x, y):
    """Capture a single pixel color from the screen"""
    try:
        with mss.mss() as sct:
            # Capture 1x1 pixel at the specified coordinates
            monitor = {"top": y, "left": x, "width": 1, "height": 1}
            screenshot = sct.grab(monitor)

            # Get RGB values (mss returns BGRA, we need RGB)
            pixel = screenshot.pixel(0, 0)
            r, g, b = pixel[2], pixel[1], pixel[0]  # Convert BGR to RGB

            return (r, g, b)
    except Exception as e:
        if DEBUG_MODE:
            print(f"[DEBUG] Error capturing pixel: {e}")
        return None

def color_distance(color1, color2):
    """Calculate Euclidean distance between two RGB colors"""
    return sum((a - b) ** 2 for a, b in zip(color1, color2)) ** 0.5

def get_teams_status_from_pixel():
    """Get Teams status by reading the status indicator pixel color"""
    pixel_color = get_pixel_color(STATUS_PIXEL_X, STATUS_PIXEL_Y)

    if pixel_color is None:
        return 'Offline'

    if DEBUG_MODE:
        print(f"[DEBUG] Pixel color at ({STATUS_PIXEL_X}, {STATUS_PIXEL_Y}): RGB{pixel_color}")

    # Find the closest matching color
    min_distance = float('inf')
    closest_status = 'Available'

    for color, status in COLOR_TO_STATUS.items():
        distance = color_distance(pixel_color, color)

        if DEBUG_MODE:
            print(f"[DEBUG] Distance to {status} {color}: {distance:.2f}")

        if distance < min_distance:
            min_distance = distance
            closest_status = status

    # If the closest color is too far away, it might be an unknown status
    if min_distance > 50:  # Threshold for color matching
        if DEBUG_MODE:
            print(f"[DEBUG] ⚠ No close color match (distance: {min_distance:.2f}), using last known status")
        return None

    if DEBUG_MODE:
        print(f"[DEBUG] ✓ Matched to '{closest_status}' (distance: {min_distance:.2f})")

    return closest_status

def get_teams_status():
    """Get current Teams status from screen pixel"""
    try:
        return get_teams_status_from_pixel()
    except Exception as e:
        print(f"Error in get_teams_status: {e}")
        return 'Offline'

# Initialize serial connection with error handling
ser = None
try:
    ser = serial.Serial(PICO_PORT, 115200, timeout=1)
    print(f"Connected to Pico on {PICO_PORT}")
except serial.SerialException as e:
    print(f"ERROR: Could not open serial port {PICO_PORT}")
    print(f"Details: {e}")
    print("\nPlease check:")
    print("  1. Pico is connected via USB")
    print("  2. Correct port is specified (check Device Manager on Windows, 'ls /dev/tty*' on Linux/Mac)")
    print("  3. No other program is using the port (close Thonny, Arduino IDE, etc.)")
    exit(1)

# Main loop
print("Teams Busylight Monitor Started (Screen Capture Mode)")
print(f"Monitoring Teams status pixel at ({STATUS_PIXEL_X}, {STATUS_PIXEL_Y})")
print("Press Ctrl+C to exit\n")
time.sleep(2)  # Give serial connection time to establish

last_status = 'Offline'
last_pixel_color = None

while True:
    try:
        current_status = get_teams_status()

        # Use last known status if we couldn't determine current one
        if current_status is None:
            current_status = last_status

        if current_status != last_status:
            # Send status to Pico with error handling
            try:
                ser.write(f"{current_status}\n".encode())
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] Status changed to: {current_status}")
                last_status = current_status
            except serial.SerialException as e:
                print(f"ERROR: Serial communication failed: {e}")
                print("Attempting to reconnect...")
                try:
                    ser.close()
                    time.sleep(1)
                    ser = serial.Serial(PICO_PORT, 115200, timeout=1)
                    print("Reconnected successfully")
                except:
                    print("Reconnection failed. Exiting...")
                    break

        time.sleep(2)  # Check every 2 seconds (faster than before)

    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        if ser and ser.is_open:
            ser.close()
        print("Serial connection closed. Goodbye!")
        break
    except Exception as e:
        print(f"Error in main loop: {e}")
        time.sleep(2)