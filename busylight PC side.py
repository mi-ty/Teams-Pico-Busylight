import serial
import time
import os
import json
import requests
from datetime import datetime, timedelta

# Configure serial connection to Pico
PICO_PORT = 'COM3'  # Windows - change to /dev/ttyACM0 on Linux/Mac
ser = serial.Serial(PICO_PORT, 115200, timeout=1)

# Microsoft Graph API Configuration
# To use this, you need to register an app at https://portal.azure.com
# and grant it User.Read and Presence.Read permissions
CONFIG_FILE = 'teams_config.json'

# Teams presence status mapping to standard status names
PRESENCE_MAPPING = {
    'Available': 'Available',
    'AvailableIdle': 'Available',
    'Away': 'Away',
    'BeRightBack': 'BeRightBack',
    'Busy': 'Busy',
    'BusyIdle': 'Busy',
    'DoNotDisturb': 'DoNotDisturb',
    'Offline': 'Offline',
    'PresenceUnknown': 'Offline',
    'InACall': 'InACall',
    'InAConferenceCall': 'InAMeeting',
    'InAMeeting': 'InAMeeting',
    'Presenting': 'Presenting',
}

class TeamsStatusMonitor:
    def __init__(self):
        self.access_token = None
        self.token_expiry = None
        self.config = self.load_config()

    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            # Create default config file
            default_config = {
                "tenant_id": "YOUR_TENANT_ID",
                "client_id": "YOUR_CLIENT_ID",
                "client_secret": "YOUR_CLIENT_SECRET",
                "user_email": "YOUR_EMAIL@company.com"
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"Created {CONFIG_FILE} - Please configure with your Azure AD app credentials")
            return default_config

    def get_access_token(self):
        """Get OAuth access token for Microsoft Graph API"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token

        token_url = f"https://login.microsoftonline.com/{self.config['tenant_id']}/oauth2/v2.0/token"

        data = {
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret'],
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials'
        }

        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data['access_token']
            # Token expires in seconds, set expiry with 5 min buffer
            expires_in = token_data.get('expires_in', 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)

            return self.access_token
        except Exception as e:
            print(f"Error getting access token: {e}")
            return None

    def get_teams_presence(self):
        """Get presence status from Microsoft Graph API"""
        token = self.get_access_token()
        if not token:
            return 'Offline'

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # Get user ID first
        try:
            user_url = f"https://graph.microsoft.com/v1.0/users/{self.config['user_email']}"
            user_response = requests.get(user_url, headers=headers)
            user_response.raise_for_status()
            user_id = user_response.json()['id']

            # Get presence
            presence_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/presence"
            presence_response = requests.get(presence_url, headers=headers)
            presence_response.raise_for_status()

            presence_data = presence_response.json()
            availability = presence_data.get('availability', 'PresenceUnknown')
            activity = presence_data.get('activity', '')

            # Map to our standard status
            status = PRESENCE_MAPPING.get(availability, 'Offline')

            # Override with activity if it's more specific
            if activity in ['InACall', 'InAMeeting', 'Presenting']:
                status = activity

            return status

        except requests.exceptions.RequestException as e:
            print(f"Error fetching presence: {e}")
            return 'Offline'
        except Exception as e:
            print(f"Unexpected error: {e}")
            return 'Offline'

def get_teams_status():
    """Get current Teams status"""
    try:
        return monitor.get_teams_presence()
    except Exception as e:
        print(f"Error in get_teams_status: {e}")
        return 'Offline'

# Initialize monitor
monitor = TeamsStatusMonitor()

# Main loop
print("Teams Busylight Monitor Started")
print(f"Connecting to Pico on {PICO_PORT}...")
time.sleep(2)  # Give serial connection time to establish

last_status = None
while True:
    try:
        current_status = get_teams_status()

        if current_status != last_status:
            # Send status to Pico
            ser.write(f"{current_status}\n".encode())
            last_status = current_status
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Status changed to: {current_status}")

        time.sleep(5)  # Check every 5 seconds

    except KeyboardInterrupt:
        print("\nShutting down...")
        ser.close()
        break
    except Exception as e:
        print(f"Error in main loop: {e}")
        time.sleep(5)