"""Speicherorte für Einstellungen, Wörterbuch und Verlauf."""

import os
import sys
from pathlib import Path

APP_NAME = "whiskaz"


def _is_mac() -> bool:
    return sys.platform == "darwin"


def config_dir() -> Path:
    if _is_mac():
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def data_dir() -> Path:
    if _is_mac():
        return config_dir()
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def asset_path(name: str) -> Path:
    return Path(__file__).parent / "assets" / name
