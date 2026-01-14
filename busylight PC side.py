import serial
import time
import os
import json

# Configure serial connection to Pico
PICO_PORT = 'COM3'  # Windows - change to /dev/ttyACM0 on Linux/Mac
ser = serial.Serial(PICO_PORT, 115200, timeout=1)

# Path to Teams logs (Windows example)
TEAMS_LOG_PATH = os.path.expanduser(
    '~\\AppData\\Roaming\\Microsoft\\Teams\\logs.txt'
)

def get_teams_status():
    """Read Teams status from presence API or logs"""
    # This is a simplified version - actual implementation depends on 
    # whether you use the Graph API or read from logs
    try:
        # Example: read from Teams logs
        with open(TEAMS_LOG_PATH, 'r') as f:
            # Parse log for status - this is simplified
            lines = f.readlines()
            # Look for status updates in logs
            for line in reversed(lines[-100:]):
                if 'status' in line.lower():
                    # Extract and return status
                    pass
    except:
        return 'Offline'
    
    return 'Available'

# Main loop
last_status = None
while True:
    current_status = get_teams_status()
    
    if current_status != last_status:
        # Send status to Pico
        ser.write(f"{current_status}\n".encode())
        last_status = current_status
        print(f"Status changed to: {current_status}")
    
    time.sleep(5)  # Check every 5 seconds