import threading
import time

from state import MagnetState
from gdi_capture import NDIScreenCapture  # <-- Import updated
from vision import Vision
from makcu_client import PicoMouse
from sender import Sender


class Colorbot:

    def __init__(self, ndi_source_name, grabzone, res, color_range, trigger_key="0x01", y_offset=9):  # <-- Parameters updated

        self.state = MagnetState()

        # Initialize the NDI Screen Grabber
        self.grabber = NDIScreenCapture(
            ndi_source_name,
            grabzone
        )

        self.vision = Vision(grabzone, color_range, y_offset=y_offset)
        self.mouse = PicoMouse()
        self.sender = Sender(self.state, self.mouse)

        self.running = False
        self.last_left = False
        self.click_pending = False
        self.trigger_key = trigger_key

    def wait_for_connection(self):
        self.grabber.wait_for_connection()

    def start(self):
        self.running = True

        threading.Thread(target=self.vision_loop, daemon=True).start()
        threading.Thread(target=self.sender.run, daemon=True).start()
        print("[+] Colorbot threads successfully started!")

    def is_trigger_active(self):
        if self.trigger_key == "auto":
            return True

        try:
            vk_code = int(self.trigger_key, 16) if self.trigger_key.startswith("0x") else int(self.trigger_key)
        except ValueError:
            vk_code = 0x01  # Default to Left Click

        # If it's a left/right click, we can check the physical Pico mouse button state
        # if the hardware is connected.
        if not self.mouse.simulated:
            from makcu import MouseButton
            if vk_code == 0x01:
                return self.mouse.is_pressed(MouseButton.LEFT)
            elif vk_code == 0x02:
                try:
                    return self.mouse.is_pressed(MouseButton.RIGHT)
                except AttributeError:
                    pass

        # Fallback to checking Windows virtual key state (works globally on Windows)
        import ctypes
        return (ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000) != 0

    def vision_loop(self):
        import time
        last_target_log = 0
        frame_count = 0
        fps_start = time.time()
        last_frame_counter = -1

        while self.running:
            current_counter = self.grabber.frame_counter
            if current_counter == last_frame_counter:
                time.sleep(0.001)
                continue

            frame = self.grabber.get_screen()

            # IMPORTANT ADDITION (NEW SAFETY)
            if frame is None:
                time.sleep(0.001)
                continue

            last_frame_counter = current_counter

            frame_count += 1
            now = time.time()
            if now - fps_start >= 5.0:
                fps = frame_count / (now - fps_start)
                print(f"[Vision] Capture rate: {fps:.1f} FPS")
                frame_count = 0
                fps_start = now

            dx, dy, found = self.vision.process(frame)
            trigger_active = self.is_trigger_active()
            is_new_click = trigger_active and not self.last_left

            # Detect edge transition: from not-pressed to pressed (click down)
            if self.trigger_key == "auto":
                click_triggered = True
            else:
                # If a new click is registered, mark it as pending
                if is_new_click:
                    self.click_pending = True
                
                # If the trigger key is released, clear the pending click
                if not trigger_active:
                    self.click_pending = False
                
                # We trigger correction if a click is pending
                click_triggered = self.click_pending
            
            self.last_left = trigger_active

            with self.state.lock:
                if found:
                    self.state.dx = dx
                    self.state.dy = dy
                    self.state.has_target = True
                    
                    if click_triggered:
                        self.state.magnet_fire = True
                        # Consume the pending click
                        self.click_pending = False
                        
                        if now - last_target_log >= 1.0:
                            print(f"[Vision] Target spotted at (dx={dx:.1f}, dy={dy:.1f}) | CLICK DETECTED -> Position correction activated")
                            last_target_log = now
                    else:
                        self.state.magnet_fire = False
                        if now - last_target_log >= 2.0:
                            print(f"[Vision] Target spotted at (dx={dx:.1f}, dy={dy:.1f}) | Waiting for new click...")
                            last_target_log = now
                else:
                    self.state.has_target = False
                    self.state.dx = 0
                    self.state.dy = 0
                    self.state.magnet_fire = False
                    if is_new_click:
                        import cv2
                        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                        avg_h = hsv[:, :, 0].mean()
                        avg_s = hsv[:, :, 1].mean()
                        avg_v = hsv[:, :, 2].mean()
                        print(f"[Debug] Click detected! No target found. Avg HSV in grabzone: H={avg_h:.1f}, S={avg_s:.1f}, V={avg_v:.1f}. Target range: Lower={self.vision.lower}, Upper={self.vision.upper}")

            time.sleep(0.001)
