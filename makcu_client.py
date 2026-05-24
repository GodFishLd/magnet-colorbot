from makcu import create_controller, MouseButton


class PicoMouse:
    def __init__(self):
        self.simulated = False
        self.left_locked = False

        try:
            self.controller = create_controller(debug=False)
            if not self.controller.is_connected():
                self.controller.connect()
            print("[+] PicoMouse: Successfully connected to Pico USB hardware.")
        except Exception as e:
            self.simulated = True
            self.controller = None
            print(f"[-] PicoMouse: Hardware not found or failed to connect ({e}). Running in SIMULATED mode.")

    def lock_left(self, lock=True):
        if self.simulated:
            return
        try:
            self.controller.lock_left(lock)
            self.left_locked = lock
        except Exception as e:
            print(f"[-] PicoMouse: Failed to lock/unlock left click ({e})")

    def move(self, x, y):
        if self.simulated:
            import ctypes
            # MOUSEEVENTF_MOVE = 0x0001
            ctypes.windll.user32.mouse_event(0x0001, int(x), int(y), 0, 0)
            return
        self.controller.move(int(x), int(y))

    def click(self, button=MouseButton.LEFT):
        if self.simulated:
            import ctypes
            import time
            # MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004
            ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
            time.sleep(0.01)
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
            return
        self.controller.click(button)

    def is_pressed(self, button=MouseButton.LEFT):
        if self.simulated:
            return False
        return self.controller.is_pressed(button)

    def close(self):
        if not self.simulated:
            self.lock_left(False)
            self.controller.disconnect()