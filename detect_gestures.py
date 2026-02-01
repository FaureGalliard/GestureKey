import cv2
import mediapipe as mp
import time
import math
import joblib
import numpy as np

# ========================
# Configuración
# ========================
MODEL_PATH = "hand_state_rf.pkl"
FPS_LIMIT = 30
FRAME_TIME = 1 / FPS_LIMIT
prev_time = 0

# ========================
# Cargar modelo
# ========================
model = joblib.load(MODEL_PATH)
print("✓ Modelo cargado")

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
# Fingers definition
# ========================
FINGERS = {
    "THUMB":  [1, 2, 4],
    "INDEX":  [5, 6, 8],
    "MIDDLE": [9, 10, 12],
    "RING":   [13, 14, 16],
    "PINKY":  [17, 18, 20],
}

# ========================
# Utils geométricos
# ========================
def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def _angle(a, b, c):
    """Ángulo ABC (en grados)"""
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
# Extracción de features
# ========================
def extract_features(landmarks):
    """
    Extrae 10 features de una mano:
    - 5 distancias (wrist->tip de cada dedo)
    - 5 ángulos (mcp-pip-tip de cada dedo)
    """
    if not landmarks or landmarks[0] == (-1.0, -1.0):
        return [0.0] * 10
    
    features = []
    wrist = landmarks[0]
    
    # Distancias
    for finger in FINGERS.values():
        tip = landmarks[finger[2]]
        features.append(_dist(wrist, tip))
    
    # Ángulos
    for finger in FINGERS.values():
        mcp = landmarks[finger[0]]
        pip = landmarks[finger[1]]
        tip = landmarks[finger[2]]
        features.append(_angle(mcp, pip, tip))
    
    return features

def predict_gesture(hands_data):
    """
    Predice el gesto usando el modelo.
    Formato: [left_features(10), right_features(10)]
    """
    left_features = extract_features(hands_data.get("Left"))
    right_features = extract_features(hands_data.get("Right"))
    
    # Combinar en vector de 20 features
    full_features = np.array(left_features + right_features).reshape(1, -1)
    
    # Predicción
    prediction = model.predict(full_features)[0]
    probabilities = model.predict_proba(full_features)[0]
    confidence = max(probabilities)
    
    return prediction, confidence

# ========================
# Colores para estados
# ========================
STATE_COLORS = {
    'PALM': (0, 255, 0),           # Verde
    'FIST': (0, 0, 255),           # Rojo
    'PINCH': (255, 0, 255),        # Magenta
    'TWO_FINGERS': (255, 255, 0),  # Cyan
    'THREE_FINGERS': (0, 255, 255),# Amarillo
    'FOUR_FINGERS': (255, 165, 0), # Naranja
}

# ========================
# Webcam
# ========================
cap = cv2.VideoCapture(0)
frame_id = 0

print("\n" + "="*50)
print("DETECCIÓN DE GESTOS EN TIEMPO REAL")
print("="*50)
print("Presiona ESC para salir")
print("="*50 + "\n")

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
    # PREDICCIÓN
    # ========================
    if hands_data:
        predicted_state, confidence = predict_gesture(hands_data)
        state_color = STATE_COLORS.get(predicted_state, (255, 255, 255))
    else:
        predicted_state = "NO HANDS"
        confidence = 0.0
        state_color = (128, 128, 128)

    # ========================
    # UI (flip visual)
    # ========================
    frame = cv2.flip(frame, 1)
    
    # Línea divisoria
    cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 255, 255), 2)

    # Panel de información
    cv2.rectangle(frame, (10, 10), (450, 140), (0, 0, 0), -1)
    cv2.rectangle(frame, (10, 10), (450, 140), state_color, 3)

    # Estado predicho
    cv2.putText(
        frame,
        f"GESTO: {predicted_state}",
        (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        state_color,
        3
    )

    # Confianza
    cv2.putText(
        frame,
        f"Confianza: {confidence*100:.1f}%",
        (20, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    # Manos detectadas
    hands_detected = []
    if "Left" in hands_data:
        hands_detected.append("Izq")
    if "Right" in hands_data:
        hands_detected.append("Der")
    
    hands_text = " + ".join(hands_detected) if hands_detected else "Ninguna"
    
    cv2.putText(
        frame,
        f"Manos: {hands_text}",
        (20, 125),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (200, 200, 200),
        2
    )

    # Instrucciones
    cv2.putText(
        frame,
        "ESC para salir",
        (w - 200, h - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        1
    )

    cv2.imshow("Deteccion de Gestos", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break

# ========================
# Cleanup
# ========================
cap.release()
hands.close()
cv2.destroyAllWindows()
print("\n✓ Aplicación cerrada correctamente")