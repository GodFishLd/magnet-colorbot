import cv2


class Vision:

    def __init__(self, grabzone, color_range):
        self.grabzone = grabzone
        self.lower = color_range["lower"]
        self.upper = color_range["upper"]

    def process(self, frame):
        bgr = frame

        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower, self.upper)
        mask = cv2.dilate(mask, None, iterations=5)

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return 0.0, 0.0, False

        c = max(contours, key=cv2.contourArea)

        if cv2.contourArea(c) < 40:
            return 0.0, 0.0, False

        x, y, w, h = cv2.boundingRect(c)

        cx = x + w // 2
        center = self.grabzone // 2

        dx = cx - center
        dy = (y + 9) - center

        return dx, dy, True