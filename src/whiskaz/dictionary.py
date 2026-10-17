"""Persönliches Wörterbuch: Wörter als Vorgabe für die Erkennung und Korrekturen als sichere Ersetzung."""

import json
import re
from dataclasses import asdict, dataclass, field

from whiskaz.paths import config_dir

BIAS_LIMIT = 20  # lange Vorgaben lassen Whisper driften


@dataclass
class Correction:
    source: str  # so wie die Erkennung es ausgibt, z. B. "cloud code"
    target: str  # so wie es geschrieben werden soll, z. B. "Claude Code"


@dataclass
class Dictionary:
    words: list[str] = field(default_factory=list)
    corrections: list[Correction] = field(default_factory=list)

    @staticmethod
    def path():
        return config_dir() / "dictionary.json"

    @classmethod
    def load(cls) -> "Dictionary":
        try:
            raw = json.loads(cls.path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        corrections = [Correction(**c) for c in raw.get("corrections", []) if c.get("source") and c.get("target")]
        return cls(words=[w for w in raw.get("words", []) if w], corrections=corrections)

    def save(self) -> None:
        data = {"words": self.words, "corrections": [asdict(c) for c in self.corrections]}
        self.path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def bias_prompt(self) -> str:
        return ", ".join(self.words[:BIAS_LIMIT])

    def apply(self, text: str) -> tuple[str, list[tuple[str, str, int]]]:
        """Ersetzt Korrekturen, längste Quelle zuerst. Gibt Text und Liste (Quelle, Ziel, Anzahl) zurück."""
        applied: list[tuple[str, str, int]] = []
        for correction in sorted(self.corrections, key=lambda c: len(c.source), reverse=True):
            pattern = compile_pattern(correction.source)
            if pattern is None:
                continue
            target = correction.target
            text, count = pattern.subn(lambda _m, t=target: t, text)
            if count:
                applied.append((correction.source, correction.target, count))
        return text, applied


def compile_pattern(source: str) -> "re.Pattern[str] | None":
    """Teile der Quelle dürfen durch Leerzeichen oder Bindestrich getrennt oder zusammengeschrieben sein.
    (?<!\\w) und (?!\\w) verhindern Treffer mitten in einem Wort, Umlaute eingeschlossen."""
    parts = source.split()
    if not parts:
        return None
    body = r"[\s\-]*".join(re.escape(part) for part in parts)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


def warnings_for(source: str) -> list[str]:
    """Hinweise für Einträge, die in normalem Text versehentlich greifen könnten."""
    if not source.strip():
        return []
    if len(source.split()) == 1:
        return [f"„{source}“ ist ein einzelnes Wort und wird überall im Text ersetzt, wo es so vorkommt."]
    return []
