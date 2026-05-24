import os
import time
from colorbot import Colorbot


def load_env(filepath=".env"):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()


def parse_tuple(val, default):
    if not val:
        return default
    try:
        return tuple(int(x.strip()) for x in val.split(","))
    except Exception:
        return default


def main():
    try:
        load_env()

        # CONFIG loaded dynamically from .env
        ndi_source = os.environ.get("NDI_SOURCE", "DESKTOP-XXXX (OBS)")
        grabzone = int(os.environ.get("GRABZONE", "100"))
        
        res_w = int(os.environ.get("RESOLUTION_WIDTH", "1920"))
        res_h = int(os.environ.get("RESOLUTION_HEIGHT", "1080"))
        resolution = (res_w, res_h)

        color_lower = parse_tuple(os.environ.get("COLOR_LOWER"), (0, 150, 150))
        color_upper = parse_tuple(os.environ.get("COLOR_UPPER"), (10, 255, 255))

        color_range = {
            "lower": color_lower,
            "upper": color_upper
        }
        
        trigger_key = os.environ.get("TRIGGER_KEY", "0x01")
        y_offset = int(os.environ.get("Y_OFFSET", "9"))
        sensitivity = float(os.environ.get("SENSITIVITY", "0.52"))
        smoothing = float(os.environ.get("SMOOTHING", "0.5"))
        mode = int(os.environ.get("MODE", "2"))

        print(f"[*] Initializing Colorbot...")
        print(f"    - NDI Source:   {ndi_source}")
        print(f"    - Grabzone:     {grabzone}")
        print(f"    - Resolution:   {resolution}")
        print(f"    - Colors:       Lower={color_lower}, Upper={color_upper}")
        print(f"    - Trigger Key:  {trigger_key}")
        print(f"    - Y Offset:     {y_offset}")
        print(f"    - Sensitivity:  {sensitivity}")
        print(f"    - Smoothing:    {smoothing}")
        print(f"    - Mode:         {mode}")

        bot = Colorbot(
            ndi_source_name=ndi_source,
            grabzone=grabzone,
            res=resolution,
            color_range=color_range,
            trigger_key=trigger_key,
            y_offset=y_offset,
            sensitivity=sensitivity,
            smoothing=smoothing,
            mode=mode
        )

        bot.wait_for_connection()

        bot.start()
        print("[*] Running... Press Ctrl+C to stop.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[*] Stopping Colorbot...")
        if 'bot' in locals():
            bot.running = False
            bot.sender.running = False
            bot.mouse.close()
        print("[+] Stopped.")


if __name__ == "__main__":
    main()
