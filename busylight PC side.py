import serial
import time
import os
import json
import platform
import sqlite3
import re
from datetime import datetime
from pathlib import Path

# Configure serial connection to Pico
PICO_PORT = 'COM3'  # Windows - change to /dev/ttyACM0 on Linux/Mac

# Teams presence status mapping
STATUS_MAPPING = {
    'available': 'Available',
    'busy': 'Busy',
    'donotdisturb': 'DoNotDisturb',
    'away': 'Away',
    'berightback': 'BeRightBack',
    'offline': 'Offline',
    'incall': 'InACall',
    'inaconferencecall': 'InAMeeting',
    'inameeting': 'InAMeeting',
    'presenting': 'Presenting',
}

class LocalTeamsMonitor:
    """Monitor Teams status by reading local files"""

    def __init__(self):
        self.teams_path = self._find_teams_path()
        self.last_status = 'Offline'
        print(f"Teams data path: {self.teams_path}")

    def _find_teams_path(self):
        """Find Teams application data path"""
        system = platform.system()

        if system == 'Windows':
            # Teams stores data in AppData\Roaming\Microsoft\Teams
            base_path = os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Teams')
        elif system == 'Darwin':  # macOS
            base_path = os.path.expanduser('~/Library/Application Support/Microsoft/Teams')
        else:  # Linux
            base_path = os.path.expanduser('~/.config/Microsoft/Microsoft Teams')

        return base_path

    def _is_teams_running(self):
        """Check if Teams process is running"""
        try:
            system = platform.system()
            if system == 'Windows':
                import subprocess
                result = subprocess.run(['tasklist'], capture_output=True, text=True, timeout=2)
                return 'Teams.exe' in result.stdout or 'ms-teams.exe' in result.stdout
            elif system == 'Darwin':  # macOS
                import subprocess
                result = subprocess.run(['pgrep', '-x', 'Teams'], capture_output=True, timeout=2)
                return result.returncode == 0
            else:  # Linux
                import subprocess
                result = subprocess.run(['pgrep', '-f', 'teams'], capture_output=True, timeout=2)
                return result.returncode == 0
        except Exception as e:
            print(f"Error checking Teams process: {e}")
            return False

    def _read_from_logs_db(self):
        """Read status from Teams logs.db SQLite database"""
        try:
            db_path = os.path.join(self.teams_path, 'logs.db')
            if not os.path.exists(db_path):
                return None

            conn = sqlite3.connect(db_path, timeout=1)
            cursor = conn.cursor()

            # Query for recent presence/status entries
            query = """
                SELECT message FROM logs
                WHERE message LIKE '%availability%'
                   OR message LIKE '%presence%'
                   OR message LIKE '%status%'
                ORDER BY timestamp DESC
                LIMIT 10
            """

            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            # Parse the most recent status from log messages
            for row in rows:
                message = row[0].lower()
                for key, value in STATUS_MAPPING.items():
                    if key in message:
                        return value

            return None

        except Exception as e:
            # Database might be locked or not exist
            return None

    def _read_from_storage_json(self):
        """Read status from Teams storage JSON files"""
        try:
            # Teams stores presence in various JSON cache files
            storage_paths = [
                os.path.join(self.teams_path, 'storage.json'),
                os.path.join(self.teams_path, 'Cache', 'presence.json'),
                os.path.join(self.teams_path, 'IndexedDB', 'https_teams.microsoft.com_0.indexeddb.leveldb'),
            ]

            for storage_file in storage_paths:
                if os.path.exists(storage_file):
                    try:
                        with open(storage_file, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read().lower()

                            # Look for status patterns in the file
                            for key, value in STATUS_MAPPING.items():
                                if key in content:
                                    return value
                    except:
                        continue

            return None

        except Exception as e:
            return None

    def _read_from_logs_txt(self):
        """Read status from Teams log text files"""
        try:
            logs_dir = os.path.join(self.teams_path, 'logs')
            if not os.path.exists(logs_dir):
                return None

            # Find the most recent log file
            log_files = []
            for file in os.listdir(logs_dir):
                if file.endswith('.txt') or file.endswith('.log'):
                    file_path = os.path.join(logs_dir, file)
                    log_files.append((file_path, os.path.getmtime(file_path)))

            if not log_files:
                return None

            # Sort by modification time, most recent first
            log_files.sort(key=lambda x: x[1], reverse=True)
            most_recent_log = log_files[0][0]

            # Read last 100 lines of the most recent log
            with open(most_recent_log, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

                # Search backwards through recent log entries
                for line in reversed(lines[-100:]):
                    line_lower = line.lower()

                    # Look for presence/status updates
                    if 'presence' in line_lower or 'availability' in line_lower or 'status' in line_lower:
                        for key, value in STATUS_MAPPING.items():
                            if key in line_lower:
                                return value

            return None

        except Exception as e:
            return None

    def get_teams_status(self):
        """Get current Teams status from local sources"""

        # First check if Teams is running
        if not self._is_teams_running():
            return 'Offline'

        # Try multiple methods to get status
        status = None

        # Method 1: Read from logs.db (most reliable if accessible)
        status = self._read_from_logs_db()
        if status:
            self.last_status = status
            return status

        # Method 2: Read from storage/cache JSON files
        status = self._read_from_storage_json()
        if status:
            self.last_status = status
            return status

        # Method 3: Parse log text files
        status = self._read_from_logs_txt()
        if status:
            self.last_status = status
            return status

        # If Teams is running but we can't determine status, assume Available
        # or return last known status
        return self.last_status if self.last_status != 'Offline' else 'Available'

def get_teams_status():
    """Get current Teams status"""
    try:
        return monitor.get_teams_status()
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

# Initialize monitor
try:
    monitor = LocalTeamsMonitor()
except Exception as e:
    print(f"ERROR: Failed to initialize Teams monitor: {e}")
    ser.close()
    exit(1)

# Main loop
print("Teams Busylight Monitor Started (Local Mode)")
print("Monitoring Teams status from local files...")
print("Press Ctrl+C to exit\n")
time.sleep(2)  # Give serial connection time to establish

last_status = None
while True:
    try:
        current_status = get_teams_status()

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

        time.sleep(5)  # Check every 5 seconds

    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        if ser and ser.is_open:
            ser.close()
        print("Serial connection closed. Goodbye!")
        break
    except Exception as e:
        print(f"Error in main loop: {e}")
        time.sleep(5)