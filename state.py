import threading


class MagnetState:
    def __init__(self):
        self.lock = threading.Lock()

        self.dx = 0.0
        self.dy = 0.0
        self.has_target = False

        self.magnet_fire = False