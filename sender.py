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

    def is_left_click_down(self):
        if not self.mouse.simulated:
            from makcu import MouseButton
            try:
                return self.mouse.is_pressed(MouseButton.LEFT)
            except AttributeError:
                pass
        import ctypes
        return (ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000) != 0

    def is_trigger_active(self):
        if self.trigger_key == "auto":
            return True

        try:
            vk_code = int(self.trigger_key, 16) if self.trigger_key.startswith("0x") else int(self.trigger_key)
        except ValueError:
            vk_code = 0x01

        if not self.mouse.simulated:
            from makcu import MouseButton
            if vk_code == 0x01:
                return self.mouse.is_pressed(MouseButton.LEFT)
            elif vk_code == 0x02:
                try:
                    return self.mouse.is_pressed(MouseButton.RIGHT)
                except AttributeError:
                    pass

        import ctypes
        return (ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000) != 0

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
        was_left_down = False
        was_trigger_active = False

        while self.running:
            start = time.perf_counter()

            # Poll mouse / trigger inputs directly at high frequency
            left_click_down = self.is_left_click_down()
            trigger_active = self.is_trigger_active()
            is_new_click = trigger_active and not was_trigger_active

            # Update shared state for external logging
            with self.state.lock:
                self.state.left_click_down = left_click_down
                self.state.trigger_active = trigger_active

            # Retrieve coordinates and target status from the vision thread
            dx = 0.0
            dy = 0.0
            has_target = False
            with self.state.lock:
                dx = self.state.dx
                dy = self.state.dy
                has_target = self.state.has_target

            # Determine flick-on-click trigger
            fire = is_new_click and has_target

            # Notify vision loop to print HSV debug values if user clicks but misses target
            if is_new_click and not has_target:
                with self.state.lock:
                    self.state.click_pending = True

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

            # Target position calculation and click state mirroring
            moved = False

            # If Left Click is locked physically at the hardware layer, we must mirror
            # click-down and click-up states virtually to PC1.
            if getattr(self.mouse, "left_locked", False):
                if left_click_down and not was_left_down:
                    # User physically clicked down
                    if fire and (self.mode & 1) > 0:
                        mx = dx * sensitivity_x * self.smoothing
                        my = dy * sensitivity_y * self.smoothing
                        if mx != 0 and abs(mx) < 1.0:
                            mx = 1.05 if mx > 0 else -1.05
                        if my != 0 and abs(my) < 1.0:
                            my = 1.05 if my > 0 else -1.05

                        self.mouse.move(mx, my)
                        time.sleep(0.005)
                        self.mouse.press()
                        moved = True
                    else:
                        self.mouse.press()
                elif not left_click_down and was_left_down:
                    # User physically released click
                    self.mouse.release()
            else:
                # Standard non-locked input flow (direct passthrough or simulated fallback)
                if fire and (self.mode & 1) > 0:
                    mx = dx * sensitivity_x * self.smoothing
                    my = dy * sensitivity_y * self.smoothing
                    if mx != 0 and abs(mx) < 1.0:
                        mx = 1.05 if mx > 0 else -1.05
                    if my != 0 and abs(my) < 1.0:
                        my = 1.05 if my > 0 else -1.05

                    self.mouse.move(mx, my)
                    if self.trigger_key != "0x01":
                        time.sleep(0.005)
                        self.mouse.click()
                    moved = True

            # 2. Tracking/Aim Assist Mode (Mode 2 & 3)
            # Active when holding the trigger key and target is spotted
            if (self.mode & 2) > 0 and trigger_active and has_target and not moved:
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

            was_left_down = left_click_down
            was_trigger_active = trigger_active
            elapsed = time.perf_counter() - start
            time.sleep(max(0, tick - elapsed))