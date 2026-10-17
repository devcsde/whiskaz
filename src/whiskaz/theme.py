"""Design-Tokens und Stylesheet. Farben und Abstände stehen nur hier, nicht in den Views."""

COLOR_TEXT = "#1f2328"
COLOR_ERROR = "#b3261e"
COLOR_WARNING = "#9a5b00"
COLOR_LEVEL = "#d9a441"
SPACING = 8
RADIUS = 6

# Overlay: dunkles Gehäuse, rote Aufnahmelampe, Pegel in Bernstein
OVERLAY_BG = "#2b2d30"
OVERLAY_BORDER = "#4a4e54"
OVERLAY_TEXT = "#e8e4da"
OVERLAY_SEGMENT_OFF = "#43474d"
REC_RED = "#c8102e"
OVERLAY_RADIUS = 10

STYLE = f"""
QLabel#status {{
    font-size: 18px;
    font-weight: 600;
    color: {COLOR_TEXT};
}}
QLabel#status[error="true"] {{
    color: {COLOR_ERROR};
}}
QLabel#last {{
    color: {COLOR_TEXT};
}}
QLabel#warning {{
    color: {COLOR_WARNING};
}}
QProgressBar#level {{
    border: 1px solid palette(mid);
    border-radius: {RADIUS}px;
    height: 14px;
}}
QProgressBar#level::chunk {{
    background-color: {COLOR_LEVEL};
    border-radius: {RADIUS}px;
}}
QGroupBox {{
    font-weight: 600;
    margin-top: 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: {SPACING}px;
    padding: 0 4px;
}}
"""
