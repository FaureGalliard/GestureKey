from __future__ import annotations

# Colors
BG_MAIN    = "#1a1a1a"
BG_PANEL   = "#111111"
BG_CAMERA  = "#0d0d0d"
BG_CARD    = "#1e1e1e"
BG_HOVER   = "#2a2a2a"
BORDER     = "rgba(255,255,255,0.08)"
BORDER_MED = "rgba(255,255,255,0.05)"

TEXT_HIGH  = "rgba(255,255,255,0.85)"
TEXT_MED   = "rgba(255,255,255,0.60)"
TEXT_LOW   = "rgba(255,255,255,0.35)"
TEXT_MUTED = "rgba(255,255,255,0.20)"

# State colors
STATE_COLORS = {
    "PALM":          "#34d399",  # emerald-400
    "FIST":          "#f87171",  # red-400
    "PINCH":         "#fbbf24",  # amber-400
    "TWO_FINGERS":   "#60a5fa",  # blue-400
    "THREE_FINGERS": "#a78bfa",  # violet-400
    "FOUR_FINGERS":  "#f472b6",  # pink-400
    "UNKNOWN":       "rgba(255,255,255,0.40)",
    "NO HANDS":      "rgba(255,255,255,0.25)",
}

EVENT_LABELS = {
    "SCROLL":               "Scroll",
    "VOLUME_UP":            "Volume ↑",
    "VOLUME_DOWN":          "Volume ↓",
    "ZOOM_IN":              "Zoom ↑",
    "ZOOM_OUT":             "Zoom ↓",
    "SCREENSHOT":           "Screenshot",
    "CLOSE_WINDOW":         "Close Window",
    "MUTE_TOGGLE":          "Mute Toggle",
    "TASK_VIEW":            "Task View",
    "PAUSE_TOGGLE_PAUSED":  "Paused",
    "PAUSE_TOGGLE_RESUMED": "Resumed",
}

BASE_STYLE = f"""
    QWidget {{
        background-color: {BG_MAIN};
        color: {TEXT_HIGH};
        font-family: 'Inter', 'Segoe UI', sans-serif;
        font-size: 11px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 3px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(255,255,255,0.10);
        border-radius: 1px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
"""