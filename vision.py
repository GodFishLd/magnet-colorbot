import cv2


class Vision:

    def __init__(self, grabzone, color_range, y_offset=9):
        self.grabzone = grabzone
        self.lower = color_range["lower"]
        self.upper = color_range["upper"]
        self.y_offset = y_offset

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

        # Get all points in the contour (reshape from shape (N, 1, 2) to (N, 2))
        points = c.reshape(-1, 2)
        
        # Focus only on the top 15% of the bounding box height (the head/neck region)
        # to prevent arms, weapons, or capes from skewing the center.
        top_threshold = y + max(5, int(h * 0.15))
        top_points = points[points[:, 1] <= top_threshold]
        
        if len(top_points) > 0:
            cx = int(top_points[:, 0].mean())
            cy_base = int(top_points[:, 1].mean())
        else:
            cx = x + w // 2
            cy_base = y

        center = self.grabzone // 2

        dx = cx - center
        dy = (cy_base + self.y_offset) - center

        return dx, dy, True