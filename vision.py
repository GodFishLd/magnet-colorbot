import cv2
import numpy as np


class Vision:

    def __init__(self, grabzone, y_offset=9):
        self.grabzone = grabzone
        self.y_offset = y_offset

    def process(self, frame):
        bgr = frame

        # Vectorized translation of C++ is_color logic
        b = bgr[:, :, 0].astype(np.int32)
        g = bgr[:, :, 1].astype(np.int32)
        r = bgr[:, :, 2].astype(np.int32)

        g_filter = g < 190
        cond_high_g = (g >= 140) & (np.abs(r - b) <= 8) & (r - g >= 50) & (b - g >= 50) & (r >= 105) & (b >= 105)
        cond_low_g = (g < 140) & (np.abs(r - b) <= 13) & (r - g >= 60) & (b - g >= 60) & (r >= 110) & (b >= 100)

        mask = (g_filter & (cond_high_g | cond_low_g)).astype(np.uint8) * 255
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