"""Lokale Spracherkennung mit faster-whisper (CPU, int8)."""

import threading

import numpy as np
from faster_whisper import WhisperModel

# Whisper erfindet bei Stille oder leisem Rauschen gern Abspann-Floskeln.
# Typische deutsche Muster, die komplett verworfen werden, wenn sie den Text dominieren.
HALLUCINATION_PHRASES = [
    "untertitel im auftrag",
    "untertitelung im auftrag",
    "untertitel der amara.org",
    "untertitel von",
    "vielen dank fürs zuschauen",
    "vielen dank für's zuschauen",
    "danke fürs zuschauen",
    "thanks for watching",
]
SILENCE_PEAK = 0.005  # darunter wird gar nicht erst transkribiert
MAX_HALLUCINATION_LENGTH = 120


def filter_hallucination(text: str) -> str:
    lowered = text.lower()
    if len(text) <= MAX_HALLUCINATION_LENGTH and any(p in lowered for p in HALLUCINATION_PHRASES):
        return ""
    return text.strip()


class Engine:
    def __init__(self):
        self._model: WhisperModel | None = None
        self._model_name: str | None = None
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._model is not None

    def load(self, name: str) -> None:
        """Lädt das Modell beim ersten Mal herunter. Blockiert, daher nie im UI-Thread aufrufen."""
        with self._lock:
            if self._model is not None and self._model_name == name:
                return
            self._model = WhisperModel(name, device="cpu", compute_type="int8")
            self._model_name = name

    def transcribe(self, audio: np.ndarray, language: str, prompt: str = "") -> str:
        with self._lock:
            model = self._model
        if model is None:
            raise RuntimeError("Das Spracherkennungsmodell ist noch nicht geladen.")
        if audio.size == 0 or float(np.max(np.abs(audio))) < SILENCE_PEAK:
            return ""
        segments, _info = model.transcribe(
            audio,
            language=None if language == "auto" else language,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=prompt or None,
            beam_size=5,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return filter_hallucination(text)
