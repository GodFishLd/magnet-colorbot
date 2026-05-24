import time


class Sender:

    def __init__(self, state, mouse, res, sensitivity=1.0, smoothing=0.5):
        self.state = state
        self.mouse = mouse
        self.running = True
        self.res = res
        self.sensitivity = sensitivity
        self.smoothing = smoothing

    def run(self):

        last_x = 0.0
        last_y = 0.0

        tick = 0.007

        # Calculate sensitivity coefficients (scaling based on in-game sensitivity and resolution)
        res_w, res_h = self.res
        sensitivity_x = 1.0 / self.sensitivity / (res_w / 1920.0) * 1.08
        sensitivity_y = 1.0 / self.sensitivity / (res_h / 1080.0) * 1.08

        while self.running:
            start = time.perf_counter()

            dx = 0.0
            dy = 0.0
            fire = False

            with self.state.lock:
                dx = self.state.dx
                dy = self.state.dy
                fire = self.state.magnet_fire
                self.state.magnet_fire = False

            # Scale target movements based on game sensitivity, resolution, and smoothing
            last_x = dx * sensitivity_x * self.smoothing
            last_y = dy * sensitivity_y * self.smoothing

            # Clamp sub-pixel movements to at least 1 pixel to prevent truncation to 0
            if last_x != 0 and abs(last_x) < 1.0:
                last_x = 1.05 if last_x > 0 else -1.05
            if last_y != 0 and abs(last_y) < 1.0:
                last_y = 1.05 if last_y > 0 else -1.05

            if fire:
                now = time.time()
                if not hasattr(self, 'last_log_time'):
                    self.last_log_time = 0
                if now - self.last_log_time >= 1.5:
                    print(f"[Sender] Command sent -> move(dx={last_x:.1f}, dy={last_y:.1f}), click() | simulated={self.mouse.simulated}")
                    self.last_log_time = now
                self.mouse.move(last_x, last_y)
                self.mouse.click()

            elapsed = time.perf_counter() - start
            time.sleep(max(0, tick - elapsed))