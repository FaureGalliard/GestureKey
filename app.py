import cv2
import mediapipe as mp
import time
import math
from hand_logger import HandLogger

# ========================
# Logger
# ========================
logger = HandLogger()
frame_id = 0
gesture_state = "PALM"

# ========================
# Configuración FPS
# ========================
FPS_LIMIT = 30
FRAME_TIME = 1 / FPS_LIMIT
prev_time = 0

# ========================
# MediaPipe Hands
# ========================
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.2,
    min_tracking_confidence=0.1
)

# ========================
# Webcam
# ========================
cap = cv2.VideoCapture(0)

while True:
    now = time.time()
    if now - prev_time < FRAME_TIME:
        continue
    prev_time = now

    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape

    # ========================
    # MediaPipe (SIN flip)
    # ========================
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    frame_id += 1
    hands_data = {}
    detected_hands = []

    # ========================
    # Extraer landmarks (px)
    # ========================
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            coords = []
            for lm in hand_landmarks.landmark:
                x = lm.x * w
                y = lm.y * h
                coords.append((x, y))

            detected_hands.append(coords)

            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

    # ========================
    # ASIGNACIÓN POR ZONAS
    # ========================
    if len(detected_hands) == 1:
        wrist_x = detected_hands[0][0][0]
        side = "Right" if wrist_x < w // 2 else "Left"
        hands_data[side] = detected_hands[0]

    elif len(detected_hands) == 2:
        detected_hands.sort(key=lambda c: c[0][0])
        hands_data["Right"] = detected_hands[0]
        hands_data["Left"] = detected_hands[1]

    # ========================
    # NORMALIZACIÓN GEOMÉTRICA
    # ========================
    for side, landmarks in hands_data.items():
        if landmarks[0] == (-1, -1):
            continue

        # muñeca como origen
        x0, y0 = landmarks[0]

        centered = [(x - x0, y - y0) for x, y in landmarks]

        # escala: muñeca -> dedo medio MCP (landmark 9)
        sx, sy = centered[9]
        scale = math.hypot(sx, sy)
        if scale < 1e-6:
            scale = 1.0

        normalized = [(x / scale, y / scale) for x, y in centered]

        hands_data[side] = normalized

    # ========================
    # LOG
    # ========================
    if hands_data:
        for side in ["Left", "Right"]:
            if side not in hands_data:
                hands_data[side] = [(-1.0, -1.0)] * 21

        logger.log(frame_id, hands_data, gesture_state)

    # ========================
    # UI (flip visual)
    # ========================
    frame = cv2.flip(frame, 1)
    cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 255, 255), 2)

    cv2.putText(
        frame,
        f"STATE: {gesture_state}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow("Webcam + Hand Tracking", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('e'):
        gesture_state = "FIST" if gesture_state == "PALM" else "PALM"

    if key == 27:
        break
# ========================
# Cleanup
# ========================
cap.release()
hands.close()
logger.close()
cv2.destroyAllWindows()
