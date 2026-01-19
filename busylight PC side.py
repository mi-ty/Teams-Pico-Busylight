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

# Enable debug mode (set to True for detailed logging)
DEBUG_MODE = True  # Change to False to disable debug output

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

    def __init__(self, debug=False):
        self.teams_path = self._find_teams_path()
        self.last_status = 'Offline'
        self.debug = debug
        print(f"Teams data path: {self.teams_path}")

        if self.debug:
            self._debug_teams_directory()

    def _debug_teams_directory(self):
        """Debug: List Teams directory structure"""
        print("\n=== DEBUG: Teams Directory Structure ===")
        if os.path.exists(self.teams_path):
            try:
                for root, dirs, files in os.walk(self.teams_path):
                    # Only show first 2 levels to avoid spam
                    level = root.replace(self.teams_path, '').count(os.sep)
                    if level < 2:
                        indent = ' ' * 2 * level
                        print(f'{indent}{os.path.basename(root)}/')
                        sub_indent = ' ' * 2 * (level + 1)
                        for file in files[:10]:  # Limit files shown
                            print(f'{sub_indent}{file}')
            except Exception as e:
                print(f"Error listing directory: {e}")
        else:
            print(f"Teams path does not exist: {self.teams_path}")
        print("========================================\n")

    def _find_teams_path(self):
        """Find Teams application data path"""
        system = platform.system()

        if system == 'Windows':
            # Try new Teams first (Teams 2.0), then classic Teams
            appdata = os.environ.get('APPDATA', '')
            localappdata = os.environ.get('LOCALAPPDATA', '')

            # New Teams path
            new_teams_path = os.path.join(localappdata, 'Packages',
                                         'MSTeams_8wekyb3d8bbwe', 'LocalCache', 'Microsoft', 'MSTeams')
            if os.path.exists(new_teams_path):
                return new_teams_path

            # Classic Teams path
            classic_path = os.path.join(appdata, 'Microsoft', 'Teams')
            return classic_path

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
                if self.debug:
                    print(f"[DEBUG] logs.db not found at {db_path}")
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

            if self.debug and rows:
                print(f"[DEBUG] Found {len(rows)} log entries")

            # Parse the most recent status from log messages
            for row in rows:
                message = row[0].lower()
                if self.debug:
                    print(f"[DEBUG] Log message: {message[:100]}...")
                for key, value in STATUS_MAPPING.items():
                    if key in message:
                        if self.debug:
                            print(f"[DEBUG] logs.db: Found status '{value}'")
                        return value

            return None

        except Exception as e:
            # Database might be locked or not exist
            if self.debug:
                print(f"[DEBUG] logs.db error: {e}")
            return None

    def _read_from_settings_json(self):
        """Read status from Teams settings/app_settings.json"""
        try:
            # Try both settings.json and app_settings.json (new Teams uses app_settings)
            settings_files = [
                os.path.join(self.teams_path, 'settings.json'),
                os.path.join(self.teams_path, 'app_settings.json'),
            ]

            for settings_path in settings_files:
                if not os.path.exists(settings_path):
                    if self.debug:
                        print(f"[DEBUG] {os.path.basename(settings_path)} not found")
                    continue

                if self.debug:
                    print(f"[DEBUG] Checking {os.path.basename(settings_path)}")

                with open(settings_path, 'r', encoding='utf-8', errors='ignore') as f:
                    try:
                        data = json.load(f)
                        if self.debug:
                            print(f"[DEBUG] {os.path.basename(settings_path)} loaded successfully")

                        # Look for presence or status keys
                        json_str = json.dumps(data).lower()
                        for key, value in STATUS_MAPPING.items():
                            if key in json_str:
                                if self.debug:
                                    print(f"[DEBUG] {os.path.basename(settings_path)}: Found status '{value}'")
                                return value
                    except json.JSONDecodeError:
                        # Try as plain text
                        f.seek(0)
                        content = f.read().lower()
                        for key, value in STATUS_MAPPING.items():
                            if key in content:
                                if self.debug:
                                    print(f"[DEBUG] {os.path.basename(settings_path)} (text): Found status '{value}'")
                                return value

            return None

        except Exception as e:
            if self.debug:
                print(f"[DEBUG] settings error: {e}")
            return None

    def _read_from_ebwebview_storage(self):
        """Read status from EBWebView Local Storage and Session Storage"""
        try:
            ebwebview_path = os.path.join(self.teams_path, 'EBWebView')
            if not os.path.exists(ebwebview_path):
                if self.debug:
                    print(f"[DEBUG] EBWebView directory not found")
                return None

            if self.debug:
                print(f"[DEBUG] Searching EBWebView directory thoroughly...")

            # Search all files in EBWebView recursively
            for root, dirs, files in os.walk(ebwebview_path):
                for file in files:
                    file_path = os.path.join(root, file)

                    # Skip binary files that are too large
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > 50 * 1024 * 1024:  # Skip files > 50MB
                            continue

                        # Check various file types that might contain status
                        if any(ext in file.lower() for ext in ['.log', '.ldb', '.leveldb', '.localstorage',
                                                                '.sessionstorage', '.json', 'storage',
                                                                'cookies', 'preferences']):
                            try:
                                if self.debug:
                                    print(f"[DEBUG] Checking {file}")

                                with open(file_path, 'rb') as f:
                                    content = f.read().decode('utf-8', errors='ignore')
                                    content_lower = content.lower()

                                    # Look for more specific presence patterns
                                    # Teams uses specific keys like "presence", "userState", "availability"
                                    presence_patterns = [
                                        '"presence":"',
                                        '"userstate":"',
                                        '"availability":"',
                                        '"status":"',
                                        'presence=',
                                        'userstate=',
                                        'availability=',
                                    ]

                                    # Check if this file has presence-related keys
                                    has_presence_key = any(pattern in content_lower for pattern in presence_patterns)

                                    if has_presence_key:
                                        # Try to extract the value near the presence key
                                        for pattern in presence_patterns:
                                            if pattern in content_lower:
                                                # Find position and extract value
                                                pos = content_lower.find(pattern)
                                                # Get 50 characters after the pattern
                                                snippet = content_lower[pos:pos+70]

                                                if self.debug:
                                                    print(f"[DEBUG] Found presence pattern in {file}: {snippet[:60]}...")

                                                # Check for status keywords in this specific area
                                                for key, value in STATUS_MAPPING.items():
                                                    if key in snippet:
                                                        if self.debug:
                                                            print(f"[DEBUG] EBWebView/{file}: Found status '{value}' near presence key")
                                                        return value
                            except Exception as e:
                                if self.debug and 'permission' in str(e).lower():
                                    print(f"[DEBUG] Permission denied: {file}")
                                continue
                    except:
                        continue

            return None

        except Exception as e:
            if self.debug:
                print(f"[DEBUG] EBWebView search error: {e}")
            return None

    def _read_from_windows_registry(self):
        """Read Teams status from Windows Registry (Teams 2.0 specific)"""
        try:
            import winreg

            if self.debug:
                print("[DEBUG] Checking Windows Registry...")

            # Teams 2.0 might store status in user registry
            reg_paths = [
                r"SOFTWARE\Microsoft\Office\Teams",
                r"SOFTWARE\Microsoft\Teams",
                r"SOFTWARE\Classes\Local Settings\Software\Microsoft\Teams",
            ]

            for reg_path in reg_paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)

                    # Try to read various possible value names
                    value_names = ['PresenceState', 'Status', 'Availability', 'UserState']
                    for value_name in value_names:
                        try:
                            value, _ = winreg.QueryValueEx(key, value_name)
                            if self.debug:
                                print(f"[DEBUG] Registry: Found {value_name} = {value}")

                            # Map the value to our status
                            value_lower = str(value).lower()
                            for status_key, status_value in STATUS_MAPPING.items():
                                if status_key in value_lower:
                                    if self.debug:
                                        print(f"[DEBUG] Registry: Mapped to '{status_value}'")
                                    winreg.CloseKey(key)
                                    return status_value
                        except FileNotFoundError:
                            continue

                    winreg.CloseKey(key)
                except WindowsError:
                    continue

            return None

        except ImportError:
            # Not on Windows
            return None
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] Registry error: {e}")
            return None

    def _read_from_storage_json(self):
        """Read status from Teams storage JSON files and IndexedDB"""
        try:
            # Teams stores presence in various JSON cache files
            storage_paths = [
                os.path.join(self.teams_path, 'storage.json'),
                os.path.join(self.teams_path, 'Cache', 'presence.json'),
                os.path.join(self.teams_path, 'IndexedDB', 'https_teams.microsoft.com_0.indexeddb.leveldb'),
                # New Teams 2.0 paths
                os.path.join(self.teams_path, 'EBWebView', 'IndexedDB'),
            ]

            for storage_file in storage_paths:
                if os.path.exists(storage_file):
                    try:
                        if self.debug:
                            print(f"[DEBUG] Checking {storage_file}")

                        # If it's a directory (IndexedDB), search all files in it
                        if os.path.isdir(storage_file):
                            for root, dirs, files in os.walk(storage_file):
                                for file in files:
                                    if file.endswith(('.log', '.ldb', '.leveldb')):
                                        file_path = os.path.join(root, file)
                                        try:
                                            with open(file_path, 'rb') as f:
                                                # Read as binary for IndexedDB files
                                                content = f.read().decode('utf-8', errors='ignore').lower()
                                                for key, value in STATUS_MAPPING.items():
                                                    if key in content:
                                                        if self.debug:
                                                            print(f"[DEBUG] IndexedDB/{file}: Found status '{value}'")
                                                        return value
                                        except:
                                                            continue
                        else:
                            # Regular file
                            with open(storage_file, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read().lower()

                                # Look for status patterns in the file
                                for key, value in STATUS_MAPPING.items():
                                    if key in content:
                                        if self.debug:
                                            print(f"[DEBUG] {os.path.basename(storage_file)}: Found status '{value}'")
                                        return value
                    except Exception as e:
                        if self.debug:
                            print(f"[DEBUG] Error reading {storage_file}: {e}")
                        continue
                else:
                    if self.debug:
                        print(f"[DEBUG] File not found: {storage_file}")

            return None

        except Exception as e:
            if self.debug:
                print(f"[DEBUG] storage_json error: {e}")
            return None

    def _read_from_logs_txt(self):
        """Read status from Teams log text files"""
        try:
            # Try both 'logs' and 'Logs' (new Teams uses capital L)
            log_dirs = [
                os.path.join(self.teams_path, 'logs'),
                os.path.join(self.teams_path, 'Logs'),
            ]

            for logs_dir in log_dirs:
                if not os.path.exists(logs_dir):
                    if self.debug:
                        print(f"[DEBUG] {logs_dir} not found")
                    continue

                # Find the most recent log files, prioritize MSTeams process logs
                msteams_logs = []
                other_logs = []

                for file in os.listdir(logs_dir):
                    if file.endswith('.txt') or file.endswith('.log'):
                        file_path = os.path.join(logs_dir, file)
                        mtime = os.path.getmtime(file_path)

                        # Prioritize actual MSTeams process logs over Launcher/Background logs
                        if file.startswith('MSTeams_') and not 'Launcher' in file and not 'Background' in file and not 'NM_' in file:
                            msteams_logs.append((file_path, mtime))
                        else:
                            other_logs.append((file_path, mtime))

                # Sort both lists by modification time
                msteams_logs.sort(key=lambda x: x[1], reverse=True)
                other_logs.sort(key=lambda x: x[1], reverse=True)

                # Check MSTeams logs first (most recent 5), then others
                log_files_to_check = msteams_logs[:5] + other_logs[:2]

                if not log_files_to_check:
                    if self.debug:
                        print(f"[DEBUG] No log files found in {logs_dir}")
                    continue

                # Check the prioritized log files
                for log_file_path, _ in log_files_to_check:
                    if self.debug:
                        print(f"[DEBUG] Reading log file: {os.path.basename(log_file_path)}")

                    try:
                        # Read last 200 lines of the log file
                        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()

                            # Search backwards through recent log entries
                            for line in reversed(lines[-200:]):
                                line_lower = line.lower()

                                # Look for specific presence update patterns (more precise)
                                presence_keywords = [
                                    'presence updated',
                                    'presence changed',
                                    'set presence',
                                    'user presence',
                                    'availability:',
                                    'userstate:',
                                    '"presence":',
                                    '"availability":'
                                ]

                                if any(keyword in line_lower for keyword in presence_keywords):
                                    # This line mentions presence, check for status nearby
                                    for key, value in STATUS_MAPPING.items():
                                        if key in line_lower:
                                            if self.debug:
                                                print(f"[DEBUG] log file: Found status '{value}' in line: {line.strip()[:100]}...")
                                            return value
                    except Exception as e:
                        if self.debug:
                            print(f"[DEBUG] Error reading {log_file_path}: {e}")
                        continue

            return None

        except Exception as e:
            if self.debug:
                print(f"[DEBUG] logs_txt error: {e}")
            return None

    def get_teams_status(self):
        """Get current Teams status from local sources"""

        # First check if Teams is running
        if not self._is_teams_running():
            if self.debug:
                print("[DEBUG] Teams process not running")
            return 'Offline'

        if self.debug:
            print("[DEBUG] Teams is running, checking status sources...")

        # Try multiple methods to get status
        status = None

        # Method 1: Windows Registry (Teams 2.0 specific)
        status = self._read_from_windows_registry()
        if status:
            if self.debug:
                print(f"[DEBUG] ✓ Status found via Registry: {status}")
            self.last_status = status
            return status

        # Method 2: EBWebView storage (Teams 2.0 specific)
        status = self._read_from_ebwebview_storage()
        if status:
            if self.debug:
                print(f"[DEBUG] ✓ Status found via EBWebView: {status}")
            self.last_status = status
            return status

        # Method 3: Read from settings.json / app_settings.json
        status = self._read_from_settings_json()
        if status:
            if self.debug:
                print(f"[DEBUG] ✓ Status found via settings.json: {status}")
            self.last_status = status
            return status

        # Method 4: Read from logs.db (most reliable if accessible)
        status = self._read_from_logs_db()
        if status:
            if self.debug:
                print(f"[DEBUG] ✓ Status found via logs.db: {status}")
            self.last_status = status
            return status

        # Method 5: Read from storage/cache JSON files
        status = self._read_from_storage_json()
        if status:
            if self.debug:
                print(f"[DEBUG] ✓ Status found via storage JSON: {status}")
            self.last_status = status
            return status

        # Method 6: Parse log text files
        status = self._read_from_logs_txt()
        if status:
            if self.debug:
                print(f"[DEBUG] ✓ Status found via log files: {status}")
            self.last_status = status
            return status

        # If Teams is running but we can't determine status
        # Return last known status or Available as fallback
        if self.debug:
            print(f"[DEBUG] ⚠ Could not determine status, using last known: {self.last_status}")

        # Only default to Available if we've never successfully read a status
        if self.last_status == 'Offline':
            if self.debug:
                print("[DEBUG] Defaulting to Available (first run)")
            return 'Available'

        return self.last_status

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
    monitor = LocalTeamsMonitor(debug=DEBUG_MODE)
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