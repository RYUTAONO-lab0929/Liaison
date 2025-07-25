# Prototype 1

This prototype demonstrates a system for triggering MP3 playback on a Raspberry Pi based on the proximity of a Bluetooth device (e.g., a Mac or another Raspberry Pi).

## Scripts

- `mac_to_rp4.py`: Runs on a Raspberry Pi (RP4) and monitors the Bluetooth signal strength (RSSI) of a Mac. When the Mac is close, it downloads and plays an MP3 file.
- `rp3_to_rp4.py`: Runs on a Raspberry Pi (RP4) and monitors the RSSI of another Raspberry Pi (RP3). It triggers MP3 playback based on proximity.

## Security & Configuration

**Important:** Sensitive information such as IP addresses and MAC addresses are not hardcoded in the scripts. They must be configured using environment variables.

### How to Set Environment Variables

Before running the scripts, you need to set the following environment variables in your shell:

**For `mac_to_rp4.py`:**

```bash
export MP3_URL="http://<YOUR_MAC_IP_ADDRESS>:8000/art01.mp3"
export MAC_BT_ADDRESS="XX:XX:XX:XX:XX:XX"
```

**For `rp3_to_rp4.py`:**

```bash
export MP3_URL="http://<YOUR_RP3_IP_ADDRESS>:8000/art01.mp3"
export RP3_BT_ADDRESS="XX:XX:XX:XX:XX:XX"
```

Replace `<YOUR_MAC_IP_ADDRESS>`, `<YOUR_RP3_IP_ADDRESS>`, and `XX:XX:XX:XX:XX:XX` with the actual IP and Bluetooth addresses for your devices.

## .gitignore

The `.gitignore` file in the root directory is configured to exclude:
- Python virtual environments (`venv/`, etc.)
- macOS specific files (`.DS_Store`)
- Python bytecode cache (`__pycache__/`)
- Log files (`*.log`)

This ensures that local-only files and sensitive data are not committed to the repository.
