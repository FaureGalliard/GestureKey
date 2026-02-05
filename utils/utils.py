import math

# =========================
# UTILS
# =========================

def dist(a, b):
    """Calcula la distancia euclidiana entre dos puntos"""
    return math.hypot(a[0] - b[0], a[1] - b[1])

def hand_center(hand):
    """Calcula el centro geométrico de una mano"""
    xs = [p[0] for p in hand]
    ys = [p[1] for p in hand]
    return (sum(xs) / len(xs), sum(ys) / len(ys))
