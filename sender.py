import time


class Sender:

    def __init__(self, state, mouse):
        self.state = state
        self.mouse = mouse
        self.running = True

    def run(self):

        last_x = 0.0
        last_y = 0.0

        tick = 0.007

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

            alpha = 0.4

            last_x = last_x * (1 - alpha) + dx * alpha
            last_y = last_y * (1 - alpha) + dy * alpha

            if abs(last_x) < 0.5:
                last_x = 0
            if abs(last_y) < 0.5:
                last_y = 0

            if fire:
                self.mouse.move(last_x, last_y)
                self.mouse.click()

            elapsed = time.perf_counter() - start
            time.sleep(max(0, tick - elapsed))