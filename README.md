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
  pip install mss pyserial
  ```
- Microsoft Teams desktop application (running on the same computer)
- Teams window must be visible (not minimized)

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

The monitor reads your Teams status by **capturing the status indicator pixel** from your screen:

1. **Screen Capture**: Captures a single pixel at coordinates (131, 34) from your screen
2. **Color Matching**: Compares the RGB color to known Teams status colors
3. **Status Detection**: Uses Euclidean distance to find the closest matching status
4. **Status Updates**: Sends status changes to Pico via USB serial every 2 seconds
5. **LED Control**: Pico updates LED color based on received status

**Advantages of Screen Capture Method:**
- ✅ Works with Teams 2.0 and Classic Teams
- ✅ No file system access required
- ✅ Real-time updates (2-second polling)
- ✅ No credentials or Azure AD setup needed
- ✅ Simple and reliable
- ✅ Easy to calibrate for different displays

**Requirements:**
- Teams window must be visible on screen (status indicator visible)
- Works with any Teams version (Classic or 2.0)
- Pixel location may need adjustment if Teams window is in different position

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

## Calibration

The script captures a pixel at coordinates **(131, 34)** which should be the Teams status indicator. You may need to adjust this:

### Finding the Correct Pixel Location:

1. **Position your Teams window** in its normal location
2. **Take a screenshot** with Teams status visible (use Print Screen or Snipping Tool)
3. **Open in Paint** or any image viewer that shows pixel coordinates
4. **Hover over the status indicator dot** (the colored circle showing your status)
5. **Note the X and Y coordinates** shown in the bottom of the window
6. **Update the script** with your coordinates:
   ```python
   STATUS_PIXEL_X = 131  # Your X coordinate
   STATUS_PIXEL_Y = 34   # Your Y coordinate
   ```

### Calibrating Colors:

If the status detection is incorrect, you may need to calibrate colors for your display:

1. **Enable debug mode** (`DEBUG_MODE = True` on line 11)
2. **Set your Teams status** to a known state (e.g., "Busy")
3. **Run the script** and observe the debug output:
   ```
   [DEBUG] Pixel color at (131, 34): RGB(196, 49, 75)
   [DEBUG] Distance to Available (146, 195, 83): 162.45
   [DEBUG] Distance to Busy (196, 49, 75): 0.00
   [DEBUG] ✓ Matched to 'Busy' (distance: 0.00)
   ```
4. **Copy the RGB values** shown for each status
5. **Update `COLOR_TO_STATUS`** dictionary with your actual colors

## Debugging

Debug mode shows detailed information about pixel capture and color matching.

Enable debug mode:
1. Open `busylight PC side.py`
2. Set `DEBUG_MODE = True` (line 11)
3. Run the script

Example debug output:
```
[DEBUG] Pixel color at (131, 34): RGB(196, 49, 75)
[DEBUG] Distance to Available (146, 195, 83): 162.45
[DEBUG] Distance to Busy (196, 49, 75): 0.00
[DEBUG] Distance to DoNotDisturb (191, 48, 74): 6.40
[DEBUG] ✓ Matched to 'Busy' (distance: 0.00)
[2026-01-19 16:45:12] Status changed to: Busy
```

## Troubleshooting

### Status is always wrong or doesn't change
1. **Check pixel location**: The status indicator must be at (131, 34) on your screen
   - Try taking a screenshot and measuring the exact position
   - Update `STATUS_PIXEL_X` and `STATUS_PIXEL_Y` in the script
2. **Calibrate colors**: Your display might show different RGB values
   - Enable debug mode to see actual pixel colors
   - Update `COLOR_TO_STATUS` with your actual colors
3. **Ensure Teams window is visible**: The status indicator must not be minimized or covered

### "Could not open port COM3"
- Ensure the Pico is connected via USB
- Check Device Manager (Windows) or `ls /dev/tty*` (Linux/Mac) for correct port
- Make sure no other program (like Thonny) is using the serial port

### Status shows "Offline" constantly
- Make sure Teams window is visible on screen (not minimized)
- Check that the status indicator is actually at coordinates (131, 34)
- Enable debug mode to see what pixel color is being captured

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
