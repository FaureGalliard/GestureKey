import csv
from datetime import datetime

LANDMARK_NAMES = [
    "WRIST",
    "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
    "INDEX_MCP", "INDEX_PIP", "INDEX_DIP", "INDEX_TIP",
    "MIDDLE_MCP", "MIDDLE_PIP", "MIDDLE_DIP", "MIDDLE_TIP",
    "RING_MCP", "RING_PIP", "RING_DIP", "RING_TIP",
    "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP"
]

class HandLogger:
    def __init__(self, filename="hand_tracking_wide.csv"):
        self.file = open(filename, "w", newline="")
        self.writer = csv.writer(self.file)

        header = ["frame", "time"]

        for hand in ["left", "right"]:
            for name in LANDMARK_NAMES:
                header.append(f"{hand}_{name}")

        self.writer.writerow(header)

    def log(self, frame_id, hands_data):
        """
        hands_data = {
            'Left': [(x,y), ... 21],
            'Right': [(x,y), ... 21]
        }
        """

        timestamp = datetime.now().strftime("%H:%M:%S")
        row = [frame_id, timestamp]

        for side in ["Left", "Right"]:
            if side in hands_data:
                for (x, y) in hands_data[side]:
                    row.append(f"({x},{y})")
            else:
                for _ in range(21):
                    row.append("(-1,-1)")

        self.writer.writerow(row)

    def close(self):
        self.file.close()
