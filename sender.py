import time


class Sender:

    def __init__(self, state, mouse, res, sensitivity=1.0, smoothing=0.5, mode=2, grabber=None, trigger_key="0x01"):
        self.state = state
        self.mouse = mouse
        self.running = True
        self.res = res
        self.sensitivity = sensitivity
        self.smoothing = smoothing
        self.mode = mode
        self.grabber = grabber
        self.trigger_key = trigger_key

    def run(self):
        last_x = 0.0
        last_y = 0.0
        tick = 0.007

        # Calculate sensitivity coefficients (scaling based on in-game sensitivity and resolution)
        res_w, res_h = self.res
        if self.grabber is not None:
            res_w = self.grabber.width
            res_h = self.grabber.height
        
        print(f"[Sender] Scaling using NDI stream resolution: {res_w}x{res_h}")

        sensitivity_x = (1.0 / self.sensitivity) * (1920.0 / res_w) * 1.08
        sensitivity_y = (1.0 / self.sensitivity) * (1080.0 / res_h) * 1.08

        left_start = None

        while self.running:
            start = time.perf_counter()

            dx = 0.0
            dy = 0.0
            has_target = False
            trigger_active = False
            left_click_down = False
            fire = False

            with self.state.lock:
                dx = self.state.dx
                dy = self.state.dy
                has_target = self.state.has_target
                trigger_active = self.state.trigger_active
                left_click_down = self.state.left_click_down
                fire = self.state.magnet_fire
                self.state.magnet_fire = False

            # Recoil Control System (RCS)
            if left_click_down:
                if left_start is None:
                    left_start = time.perf_counter()
                recoil_ms = (time.perf_counter() - left_start) * 1000.0
                
                # Recoil math from C++: 38.0 * (res_h / 1080.0) * (recoil_ms / 1000.0)
                # clamped at 38.0 * (res_h / 1080.0)
                max_recoil = 38.0 * (res_h / 1080.0)
                extra = max_recoil * (recoil_ms / 1000.0)
                if extra > max_recoil:
                    extra = max_recoil
            else:
                left_start = None
                extra = 0.0

            # Target position calculation
            moved = False

            # 1. Flick Mode (Mode 1 & 3)
            if fire and (self.mode & 1) > 0 and has_target:
                # Direct C++ translation for instantaneous correction scaling
                mx = dx * sensitivity_x
                my = dy * sensitivity_y
                
                # Check for minimum registered step size
                if mx != 0 and abs(mx) < 1.0:
                    mx = 1.05 if mx > 0 else -1.05
                if my != 0 and abs(my) < 1.0:
                    my = 1.05 if my > 0 else -1.05
                    
                now = time.time()
                if not hasattr(self, 'last_log_time'):
                    self.last_log_time = 0
                if now - self.last_log_time >= 1.5:
                    print(f"[Sender] Mode {self.mode} Flick -> move(dx={mx:.1f}, dy={my:.1f}), click()")
                    self.last_log_time = now
                    
                # Deliver movement
                self.mouse.move(mx, my)
                
                # If trigger key is not left click (e.g. it is Auto, Shift, or Right Click),
                # the bot must handle the shooting itself. We add a short delay to let the
                # mouse arrive before clicking.
                if self.trigger_key != "0x01":
                    time.sleep(0.005)
                    self.mouse.click()
                
                moved = True

            # 2. Tracking/Aim Assist Mode (Mode 2 & 3)
            elif (self.mode & 2) > 0 and trigger_active and has_target and not moved:
                vx = dx * sensitivity_x * self.smoothing
                vy = (dy + extra) * sensitivity_y * self.smoothing

                if vx != 0 and abs(vx) < 1.0:
                    vx = 1.05 if vx > 0 else -1.05
                if vy != 0 and abs(vy) < 1.0:
                    vy = 1.05 if vy > 0 else -1.05

                now = time.time()
                if not hasattr(self, 'last_log_time'):
                    self.last_log_time = 0
                if now - self.last_log_time >= 1.5:
                    print(f"[Sender] Mode {self.mode} Track -> move(dx={vx:.1f}, dy={vy:.1f}) | RCS Extra={extra:.1f}")
                    self.last_log_time = now

                self.mouse.move(vx, vy)

            elapsed = time.perf_counter() - start
            time.sleep(max(0, tick - elapsed))