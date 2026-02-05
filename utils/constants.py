# =========================
# CONSTANTES
# =========================
DEADZONE = 0.015
SMOOTHING = 0.7
SCROLL_SENS = 1.2
VOLUME_SENS = 1.0
ZOOM_SENS = 1.5
PAUSE_MIN_TIME = 0.2
MUTE_MAX_TIME = 1.0
COOLDOWN = 0.6

# =========================
# STATE STABILIZER (🏗️ ARQUITECTURA NUEVA)
# =========================
STATE_CONFIRM_TIME = 0.15      # 150ms - tiempo para confirmar un estado nuevo
UNKNOWN_GRACE_TIME = 0.3       # 300ms - tiempo de gracia para UNKNOWN
STATE_LOSS_TIMEOUT = 0.5       # 500ms - timeout para declarar pérdida de estado

# =========================
# SCROLL MEJORADO
# =========================
SCROLL_DEADZONE = 0.02
SCROLL_TRIGGER = 0.04
SCROLL_COOLDOWN = 0.15
# Ventana de tiempo para gesto intencional
SCROLL_ARM_TIME = 0.18      # tiempo mínimo para activar scroll
SCROLL_MAX_TIME = 3.0       # después de esto se desarma solo
SCROLL_DIRECTION_FRAMES = 4 # frames para consistencia de dirección
# Zona neutral (centro de la cámara)
SCROLL_CENTER_Y = 0.45      # centro vertical aceptable
SCROLL_CENTER_TOL = 0.18    # tolerancia arriba/abajo

# =========================
# VOLUMEN MEJORADO
# =========================
VOLUME_DEADZONE = 0.025     # deadzone ligeramente mayor que scroll (más deliberado)
VOLUME_ARM_TIME = 0.20      # tiempo mínimo para activar volumen
VOLUME_MAX_TIME = 3.0       # después de esto se desarma solo

# =========================
# ZOOM MEJORADO
# =========================
ZOOM_ARM_TIME = 0.18        # tiempo mínimo para activar zoom (similar a scroll)

# =========================
# PAUSE/RESUME (transición PALM→FIST)
# =========================
PAUSE_MIN_TIME = 0.2      # 200ms mínimo en PALM antes de poder hacer FIST
PAUSE_MAX_TIME = 1.5      # Máximo 1.5s para completar transición (opcional)
PAUSE_COOLDOWN = 0.5      # 500ms entre toggles (evita doble activación)

# =========================
# PROFUNDIDAD PARA INTENCIÓN (DEPTH GATE)
# =========================
# Usado tanto por scroll como volumen
INTENT_Z_NEAR  = -0.035    # mano relativamente lejos ya cuenta
INTENT_Z_FAR   =  0.00     # casi fuera de cámara → ignorar
INTENT_Z_ENTER = -0.045    # entra fácil
INTENT_Z_EXIT  = -0.005    # sale solo cuando te alejas mucho

# =========================
# TASK VIEW (Vista de tareas)
# =========================
TASK_VIEW_ARM_TIME = 0.15          # tiempo de estabilidad antes de armar (150ms)
TASK_VIEW_MIN_APPROACH = 0.15      # acercamiento mínimo total (15% de pantalla)
TASK_VIEW_COOLDOWN = 1.5  