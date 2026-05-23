from makcu import create_controller, MouseButton


class PicoMouse:
    def __init__(self):
        self.simulated = False

        try:
            self.controller = create_controller(debug=False)
            if not self.controller.is_connected():
                self.controller.connect()
        except:
            self.simulated = True
            self.controller = None

    def move(self, x, y):
        if self.simulated:
            return
        self.controller.move(int(x), int(y))

    def click(self, button=MouseButton.LEFT):
        if self.simulated:
            return
        self.controller.click(button)

    def is_pressed(self, button=MouseButton.LEFT):
        if self.simulated:
            return False
        return self.controller.is_pressed(button)

    def close(self):
        if not self.simulated:
            self.controller.disconnect()