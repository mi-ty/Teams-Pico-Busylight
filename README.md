# Teams Pico Busylight

A physical presence indicator for Microsoft Teams using a Raspberry Pi Pico and WS2812B RGB LEDs.

## Overview

This project monitors your Microsoft Teams presence status and displays it on an RGB LED strip connected to a Raspberry Pi Pico. The LED color changes based on your availability status (Available = Green, Busy = Red, etc.).

## Hardware Requirements

- Raspberry Pi Pico (or Pico W)
- WS2812B addressable RGB LED strip (NeoPixel compatible)
- USB cable (for connecting Pico to computer)
- Optional: 3.3V to 5V level shifter for reliable LED communication

## Wiring

- LED Data Pin → Pico GPIO 0
- LED VCC → Pico VBUS (5V) or external 5V supply
- LED GND → Pico GND

## Software Requirements

### PC Side (Computer running Teams)
- Python 3.7+
- Required Python packages:
  ```bash
  pip install pyserial requests
  ```

### Pico Side
- MicroPython firmware installed on Pico
- Download from: https://micropython.org/download/rp2-pico/

## Setup Instructions

### 1. Flash MicroPython to Pico

1. Download the latest MicroPython UF2 file for Raspberry Pi Pico
2. Hold the BOOTSEL button on Pico while connecting it to your computer
3. Drag and drop the UF2 file to the RPI-RP2 drive
4. Pico will reboot and appear as a serial device

### 2. Upload Pico Code

1. Use Thonny IDE or `ampy` to upload `busylight pi-thon.py` to your Pico
2. Save it as `main.py` on the Pico so it runs automatically on boot

**Using Thonny:**
- Open Thonny IDE
- Select "MicroPython (Raspberry Pi Pico)" as the interpreter
- Open `busylight pi-thon.py`
- Save it to the Pico as `main.py`

**Using ampy:**
```bash
pip install adafruit-ampy
ampy --port COM3 put "busylight pi-thon.py" main.py
```

### 3. Configure Microsoft Graph API Access

To access Teams presence status, you need to register an application in Azure AD:

1. **Register an Azure AD App:**
   - Go to [Azure Portal](https://portal.azure.com)
   - Navigate to "Azure Active Directory" → "App registrations" → "New registration"
   - Name: "Teams Busylight"
   - Supported account types: "Accounts in this organizational directory only"
   - Click "Register"

2. **Configure API Permissions:**
   - In your app, go to "API permissions"
   - Click "Add a permission" → "Microsoft Graph" → "Application permissions"
   - Add these permissions:
     - `User.Read.All`
     - `Presence.Read.All`
   - Click "Grant admin consent" (requires admin privileges)

3. **Create Client Secret:**
   - Go to "Certificates & secrets" → "New client secret"
   - Description: "Busylight Secret"
   - Expiry: Choose your preferred duration
   - Copy the secret value (you won't see it again!)

4. **Get Your IDs:**
   - **Tenant ID**: Found on the "Overview" page of your app
   - **Client ID**: Also on the "Overview" page (Application ID)
   - **User Email**: Your Microsoft 365 email address

5. **Update Configuration:**

   When you first run the PC-side script, it will create a `teams_config.json` file. Edit it with your values:

   ```json
   {
       "tenant_id": "YOUR_TENANT_ID",
       "client_id": "YOUR_CLIENT_ID",
       "client_secret": "YOUR_CLIENT_SECRET",
       "user_email": "your.email@company.com"
   }
   ```

### 4. Configure Serial Port

Edit `busylight PC side.py` and set the correct port:

- **Windows**: `COM3`, `COM4`, etc.
- **Linux**: `/dev/ttyACM0` or `/dev/ttyUSB0`
- **Mac**: `/dev/tty.usbmodem*`

To find your port:

**Windows:**
```cmd
mode
```

**Linux/Mac:**
```bash
ls /dev/tty* | grep -i usb
```

### 5. Run the Monitor

```bash
python "busylight PC side.py"
```

You should see:
```
Teams Busylight Monitor Started
Connecting to Pico on COM3...
[2026-01-14 10:30:00] Status changed to: Available
```

## LED Color Mapping

| Teams Status | LED Color | Effect |
|-------------|-----------|--------|
| Available | Green | Solid |
| Busy | Red | Solid |
| Do Not Disturb | Purple | Solid |
| Away | Yellow | Solid |
| Be Right Back | Yellow | Solid |
| In a Call | Red | Solid |
| In a Meeting | Red | Solid |
| Presenting | Red | Solid |
| Offline | Gray | Solid |

## Customization

### Change LED Count

Edit `busylight pi-thon.py`:
```python
NUM_LEDS = 5  # Change to your LED strip length
```

### Change Update Interval

Edit `busylight PC side.py`:
```python
time.sleep(5)  # Change to desired seconds
```

### Add Pulse Effect

The Pico code includes a `pulse_color()` function. To enable pulsing for certain states, edit the main loop in `busylight pi-thon.py`:

```python
if status in ['Busy', 'InACall', 'InAMeeting', 'DoNotDisturb']:
    set_color(color)
else:
    pulse_color(color)  # Enable pulsing for non-busy states
```

## Troubleshooting

### "Could not open port COM3"
- Ensure the Pico is connected
- Check Device Manager (Windows) or `ls /dev/tty*` (Linux/Mac) for correct port
- Make sure no other program (like Thonny) is using the serial port

### "Error getting access token"
- Verify `teams_config.json` has correct credentials
- Ensure API permissions are granted and admin consent is given
- Check that your client secret hasn't expired

### "Error fetching presence"
- Verify your user email is correct in config
- Ensure the app has `Presence.Read.All` permission
- Check that you're logged into Teams on the computer

### LED not lighting up
- Check wiring connections
- Verify GPIO pin number in code matches physical connection
- Ensure Pico is receiving power (try USB power supply)
- Test LED strip separately with a simple test script

### LED shows wrong colors
- Some LED strips use GRB instead of RGB color order
- Adjust color tuples in `COLORS` dictionary if needed

## Auto-start on Boot (Optional)

### Windows
1. Create a batch file `start_busylight.bat`:
   ```batch
   @echo off
   cd C:\path\to\Teams-Pico-Busylight
   python "busylight PC side.py"
   ```
2. Press `Win+R`, type `shell:startup`, press Enter
3. Create a shortcut to your batch file in the Startup folder

### Linux
Add to `~/.bashrc` or create a systemd service:
```bash
python3 /path/to/busylight\ PC\ side.py &
```

### Mac
Create a Launch Agent in `~/Library/LaunchAgents/`

## Security Notes

- Keep `teams_config.json` secure and never commit it to version control
- Client secrets should be rotated periodically
- Use application permissions (not delegated) for unattended operation
- Consider using Azure Key Vault for production environments

## License

MIT License - Feel free to modify and distribute

## Contributing

Contributions welcome! Please submit pull requests or open issues for bugs and feature requests.
