"""Benutzereinstellungen, gespeichert als JSON im Konfigurationsordner."""

import json
import sys
from dataclasses import asdict, dataclass, fields

from whiskaz.paths import config_dir

# Rechte Ctrl-Taste auf Linux, rechte Cmd-Taste auf dem Mac: beide kollidieren
# auf deutschen Layouts nicht mit Sonderzeichen wie @, €, { oder [.
DEFAULT_HOTKEY = "cmd_r" if sys.platform == "darwin" else "ctrl_r"

HOTKEY_CHOICES = ["ctrl_r", "ctrl_l", "alt_r", "cmd_r", "shift_r", "f8", "f9", "f12", "scroll_lock", "pause"]
HOTKEY_LABELS = {
    "ctrl_r": "rechte Strg-Taste",
    "ctrl_l": "linke Strg-Taste",
    "alt_r": "rechte Alt-Taste",
    "cmd_r": "rechte Cmd-Taste",
    "shift_r": "rechte Umschalttaste",
    "scroll_lock": "Rollen-Taste",
}


def hotkey_label(name: str) -> str:
    return HOTKEY_LABELS.get(name, name)
MODEL_CHOICES = ["tiny", "base", "small", "medium", "large-v3-turbo", "large-v3"]
LANGUAGE_CHOICES = ["de", "en", "auto"]
MODE_CHOICES = [
    ("hold", "Halten: Taste gedrückt halten zum Sprechen"),
    ("toggle", "Umschalten: einmal drücken startet, nochmal drücken stoppt"),
]
ANCHOR_CHOICES = [("left", "Oben links"), ("center", "Oben Mitte"), ("right", "Oben rechts")]


@dataclass
class Settings:
    hotkey: str = DEFAULT_HOTKEY
    model: str = "small"
    language: str = "de"
    terminal_paste: bool = False
    mode: str = "hold"  # hold | toggle
    overlay_enabled: bool = True
    overlay_anchor: str = "center"  # left | center | right, gilt ohne gespeicherte Position
    overlay_pos: list[int] | None = None  # [x, y], nach dem Verschieben gespeichert

    @classmethod
    def path(cls):
        return config_dir() / "settings.json"

    @classmethod
    def load(cls) -> "Settings":
        try:
            raw = json.loads(cls.path().read_text(encoding="utf-8"))
            known = {f.name for f in fields(cls)}
            return cls(**{k: v for k, v in raw.items() if k in known})
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self) -> None:
        self.path().write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
