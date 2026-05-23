import threading
import time

from state import MagnetState
from gdi_capture import NDIScreenCapture  # <-- Import updated
from vision import Vision
from makcu_client import PicoMouse
from sender import Sender


class Colorbot:

    def __init__(self, ndi_source_name, grabzone, res, color_range):  # <-- Parameters updated

        self.state = MagnetState()

        # Initialize the NDI Screen Grabber
        self.grabber = NDIScreenCapture(
            ndi_source_name,
            grabzone
        )

        self.vision = Vision(grabzone, color_range)
        self.mouse = PicoMouse()
        self.sender = Sender(self.state, self.mouse)

        self.running = False
        self.last_left = False

    def wait_for_connection(self):
        self.grabber.wait_for_connection()

    def start(self):
        self.running = True

        threading.Thread(target=self.vision_loop, daemon=True).start()
        threading.Thread(target=self.sender.run, daemon=True).start()
        print("[+] Colorbot threads successfully started!")

    def vision_loop(self):

        while self.running:

            frame = self.grabber.get_screen()

            # IMPORTANT ADDITION (NEW SAFETY)
            if frame is None:
                continue

            dx, dy, found = self.vision.process(frame)

            with self.state.lock:
                if found:
                    self.state.dx = dx
                    self.state.dy = dy
                    self.state.has_target = True
                else:
                    self.state.has_target = False
                    self.state.dx = 0
                    self.state.dy = 0
