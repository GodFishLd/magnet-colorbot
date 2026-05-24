import numpy as np
import threading
import time

# Dynamic selection of the NDI library backend
NDI_BACKEND = None

try:
    import NDIlib as ndi  # type: ignore
    if ndi.initialize():
        NDI_BACKEND = "ndi-python"
    else:
        pass
except ImportError:
    pass

if NDI_BACKEND is None:
    try:
        from cyndilib.receiver import Receiver
        NDI_BACKEND = "cyndilib"
    except ImportError:
        pass


class NDIScreenCapture:

    def __init__(self, ndi_source_name, grabzone):
        self.grabzone = grabzone
        self.screen = None
        self.running = True
        self.ndi_source_name = ndi_source_name
        self.frame_counter = 0

        if NDI_BACKEND == "ndi-python":
            recv_create = ndi.RecvCreateV3()
            recv_create.color_format = ndi.RECV_COLOR_FORMAT_BGRX_BGRA
            self.ndi_recv = ndi.recv_create_v3(recv_create)
            if self.ndi_recv is None:
                raise RuntimeError("Failed to create NDI receiver via ndi-python")
            self.connected = False
        elif NDI_BACKEND == "cyndilib":
            self.ndi = Receiver(source_name=ndi_source_name)
            self.connected = True
        else:
            raise RuntimeError(
                "No working NDI library found. Please install either 'ndi-python' (pip install ndi-python) or 'cyndilib'."
            )

        # start capture thread
        threading.Thread(target=self._loop, daemon=True).start()

    # -------------------------
    # CAPTURE LOOP (HOT PATH)
    # -------------------------
    def _loop(self):
        if NDI_BACKEND == "ndi-python":
            self._loop_ndi_python()
        elif NDI_BACKEND == "cyndilib":
            self._loop_cyndilib()

    def _loop_ndi_python(self):
        while self.running:
            if not self.connected:
                ndi_find = ndi.find_create_v2()
                if ndi_find:
                    ndi.find_wait_for_sources(ndi_find, 1000)
                    sources = ndi.find_get_current_sources(ndi_find)
                    target_source = None
                    for s in sources:
                        if s.ndi_name == self.ndi_source_name:
                            target_source = s
                            break
                    if not target_source and sources:
                        target_source = sources[0]
                    
                    if target_source:
                        ndi.recv_connect(self.ndi_recv, target_source)
                        self.connected = True
                        print(f"[+] Connected to NDI source: {target_source.ndi_name}")
                    ndi.find_destroy(ndi_find)
                
                if not self.connected:
                    time.sleep(1)
                    continue

            try:
                t, v, a, _ = ndi.recv_capture_v3(self.ndi_recv, 1000)
                if t == ndi.FRAME_TYPE_VIDEO:
                    img = np.copy(v.data)
                    img = img.reshape((v.yres, v.xres, 4))
                    img = img[:, :, :3]

                    h, w = img.shape[:2]
                    cx, cy = w // 2, h // 2
                    g = self.grabzone // 2

                    x1 = cx - g
                    y1 = cy - g
                    x2 = x1 + self.grabzone
                    y2 = y1 + self.grabzone

                    if not (x1 < 0 or y1 < 0 or x2 > w or y2 > h):
                        self.screen = img[y1:y2, x1:x2]
                        self.frame_counter += 1

                    ndi.recv_free_video_v2(self.ndi_recv, v)
                elif t == ndi.FRAME_TYPE_AUDIO:
                    ndi.recv_free_audio_v3(self.ndi_recv, a)
                elif t == ndi.FRAME_TYPE_METADATA:
                    ndi.recv_free_metadata(self.ndi_recv, a)
            except Exception:
                continue

    def _loop_cyndilib(self):
        while self.running:
            try:
                frame = self.ndi.get_video_frame()
                if frame is None:
                    continue

                img = np.asarray(frame.data)

                if img.shape[-1] >= 3:
                    img = img[:, :, :3]

                h, w = img.shape[:2]
                cx, cy = w // 2, h // 2
                g = self.grabzone // 2

                x1 = cx - g
                y1 = cy - g
                x2 = x1 + self.grabzone
                y2 = y1 + self.grabzone

                if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
                    continue

                self.screen = img[y1:y2, x1:x2]
                self.frame_counter += 1

            except Exception:
                continue

    # -------------------------
    # READ (used by vision)
    # -------------------------
    def get_screen(self):
        return self.screen

    # -------------------------
    # CONNECTION WAIT
    # -------------------------
    def wait_for_connection(self):
        if NDI_BACKEND == "ndi-python" and not self.connected:
            print(f"[*] Waiting for NDI source '{self.ndi_source_name}' to start...")
            while self.running and not self.connected:
                time.sleep(0.5)

    # -------------------------
    # STOP
    # -------------------------
    def stop(self):
        self.running = False
        if NDI_BACKEND == "ndi-python":
            if hasattr(self, 'ndi_recv') and self.ndi_recv:
                ndi.recv_destroy(self.ndi_recv)
            ndi.destroy()