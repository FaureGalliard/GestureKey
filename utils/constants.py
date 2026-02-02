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

# Profundidad para intención (depth gate)
INTENT_Z_NEAR  = -0.035    # mano relativamente lejos ya cuenta
INTENT_Z_FAR   =  0.00     # casi fuera de cámara → ignorar
INTENT_Z_ENTER = -0.045    # entra fácil
INTENT_Z_EXIT  = -0.005    # sale solo cuando te alejas mucho
