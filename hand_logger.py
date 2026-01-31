import csv
import math
from datetime import datetime

FINGERS = {
    "THUMB":  [1, 2, 4],
    "INDEX":  [5, 6, 8],
    "MIDDLE": [9, 10, 12],
    "RING":   [13, 14, 16],
    "PINKY":  [17, 18, 20],
}

class HandLogger:
    def __init__(self, filename="hand_features.csv"):
        self.file = open(filename, "w", newline="")
        self.writer = csv.writer(self.file)

        header = ["frame", "time"]

        for hand in ["left", "right"]:
            for finger in FINGERS:
                header.append(f"{hand}_{finger}_dist")
            for finger in FINGERS:
                header.append(f"{hand}_{finger}_angle")

        self.writer.writerow(header)

    # ========================
    # Utils geométricos
    # ========================
    def _dist(self, a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _angle(self, a, b, c):
        """
        ángulo ABC (en grados)
        """
        ba = (a[0] - b[0], a[1] - b[1])
        bc = (c[0] - b[0], c[1] - b[1])

        dot = ba[0]*bc[0] + ba[1]*bc[1]
        mag_ba = math.hypot(*ba)
        mag_bc = math.hypot(*bc)

        if mag_ba * mag_bc == 0:
            return 0.0

        cos_angle = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
        return math.degrees(math.acos(cos_angle))

    # ========================
    # LOG
    # ========================
    def log(self, frame_id, hands_data):
        timestamp = datetime.now().strftime("%H:%M:%S")
        row = [frame_id, timestamp]

        for side in ["Left", "Right"]:
            landmarks = hands_data.get(side)

            if not landmarks or landmarks[0] == (-1.0, -1.0):
                # distancias
                row.extend([0.0] * 5)
                # ángulos
                row.extend([0.0] * 5)
                continue

            wrist = landmarks[0]

            # -------- distancias --------
            for finger in FINGERS.values():
                tip = landmarks[finger[2]]
                row.append(self._dist(wrist, tip))

            # -------- ángulos --------
            for finger in FINGERS.values():
                mcp = landmarks[finger[0]]
                pip = landmarks[finger[1]]
                tip = landmarks[finger[2]]
                row.append(self._angle(mcp, pip, tip))

        self.writer.writerow(row)

    def close(self):
        self.file.close()
