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
  pip install pyserial
  ```
- Microsoft Teams desktop application (running on the same computer)

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

### 3. Configure Serial Port

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

### 4. Run the Monitor

Make sure Microsoft Teams desktop app is running, then:

```bash
python "busylight PC side.py"
```

You should see:
```
Connected to Pico on COM3
Teams data path: C:\Users\YourName\AppData\Roaming\Microsoft\Teams
Teams Busylight Monitor Started (Local Mode)
Monitoring Teams status from local files...
Press Ctrl+C to exit

[2026-01-19 10:30:00] Status changed to: Available
```

## How It Works

The monitor reads your Teams status **locally** from your computer without requiring Azure AD setup:

1. **Process Detection**: Checks if Teams.exe is running
2. **Local File Reading**: Reads status from multiple sources:
   - `logs.db` - SQLite database with presence logs
   - `storage.json` - Cached user status
   - Log files - Recent activity logs
3. **Status Updates**: Sends status changes to Pico via USB serial
4. **LED Control**: Pico updates LED color based on received status

**Advantages of Local Method:**
- ✅ No Azure AD app registration required
- ✅ No admin consent needed
- ✅ Works offline (no internet required)
- ✅ Instant updates (no API rate limits)
- ✅ No credentials or secrets to manage

**Note**: The local method reads Teams data files which may be locked while Teams is running. The script tries multiple methods to ensure reliable status detection.

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

### "Teams data path not found" or status always shows "Offline"
- Ensure Microsoft Teams desktop app is installed and running
- Verify Teams is logged in and active
- Check that Teams data folder exists at the path shown in console output
- Try manually changing your Teams status to trigger file updates

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

- The script reads local Teams data files (read-only access)
- No credentials or API keys are stored or transmitted
- All processing happens locally on your computer
- Serial communication with Pico only sends status strings (e.g., "Available", "Busy")
- No personal information or message content is accessed

## License

MIT License - Feel free to modify and distribute

## Contributing

Contributions welcome! Please submit pull requests or open issues for bugs and feature requests.
