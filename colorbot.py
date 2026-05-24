import threading
import time

from state import MagnetState
from gdi_capture import NDIScreenCapture  # <-- Import updated
from vision import Vision
from makcu_client import PicoMouse
from sender import Sender


class Colorbot:

    def __init__(self, ndi_source_name, grabzone, res, color_range, trigger_key="0x01", y_offset=9, sensitivity=1.0, smoothing=0.5, mode=2):  # <-- Parameters updated

        self.state = MagnetState()

        # Initialize the NDI Screen Grabber
        self.grabber = NDIScreenCapture(
            ndi_source_name,
            grabzone
        )

        self.vision = Vision(grabzone, y_offset=y_offset)
        self.mouse = PicoMouse()
        self.sender = Sender(self.state, self.mouse, res=res, sensitivity=sensitivity, smoothing=smoothing, mode=mode, grabber=self.grabber, trigger_key=trigger_key)

        self.running = False
        self.last_left = False
        self.click_pending = False
        self.trigger_key = trigger_key

    def wait_for_connection(self):
        self.grabber.wait_for_connection()

    def start(self):
        self.running = True
        if self.trigger_key == "0x01" and not self.mouse.simulated:
            self.mouse.lock_left(True)
            print("[+] PicoMouse left click suppressed (locked) at firmware level.")

        threading.Thread(target=self.vision_loop, daemon=True).start()
        threading.Thread(target=self.sender.run, daemon=True).start()
        print("[+] Colorbot threads successfully started!")

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

            # Retrieve click_pending debug flag and trigger state from sender thread
            click_pending = False
            trigger_active_shared = False
            with self.state.lock:
                self.state.has_target = found
                trigger_active_shared = self.state.trigger_active
                
                if found:
                    self.state.dx = dx
                    self.state.dy = dy
                    
                    if now - last_target_log >= 1.5:
                        status_str = "ACTIVE (Tracking)" if trigger_active_shared else "IDLE"
                        print(f"[Vision] Target spotted at (dx={dx:.1f}, dy={dy:.1f}) | Trigger={status_str}")
                        last_target_log = now
                else:
                    self.state.dx = 0.0
                    self.state.dy = 0.0

                if self.state.click_pending:
                    click_pending = True
                    self.state.click_pending = False

            if click_pending:
                import cv2
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                avg_h = hsv[:, :, 0].mean()
                avg_s = hsv[:, :, 1].mean()
                avg_v = hsv[:, :, 2].mean()
                print(f"[Debug] Click detected! No target found. Avg HSV in grabzone: H={avg_h:.1f}, S={avg_s:.1f}, V={avg_v:.1f}")

            time.sleep(0.001)
