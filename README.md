# magnet-colorbot

A Windows color-detection bot written in Python. It captures a region of the screen, locates targets by color signature, and dispatches mouse movement — either through the OS or through a MAKCU hardware input device over serial.

## How it works

```text
gdi_capture.py  →  vision.py  →  colorbot.py  →  sender.py / makcu_client.py
   screen grab      detection      decision        input dispatch
```

## Project structure

| File | Purpose |
| --- | --- |
| `main.py` | Entry point — starts the bot |
| `colorbot.py` | Core loop: capture, detect, act |
| `vision.py` | Color-based target detection |
| `gdi_capture.py` | Fast screen capture via Windows GDI |
| `sender.py` | Mouse movement dispatch |
| `makcu_client.py` | Serial client for MAKCU hardware input |
| `state.py` | Shared runtime state |

## Requirements

- Windows (GDI capture is platform-specific)
- Python 3.10+
- Optional: a MAKCU device for hardware-level input

## Installation

```bash
git clone https://github.com/GodFishLd/magnet-colorbot.git
cd magnet-colorbot
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

Adjust capture region, target color thresholds, and input backend in the configuration section before running.

## Disclaimer

Provided for educational and research purposes. Using automated input tools in online games typically violates their terms of service. Use at your own risk.
