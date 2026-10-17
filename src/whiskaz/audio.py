"""Mikrofonaufnahme als 16-kHz-Mono-Float-Array, direkt für Whisper geeignet."""

import threading
from collections.abc import Callable

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
BLOCK_SIZE = 1600  # 100 ms


class Recorder:
    def __init__(self, on_level: Callable[[float], None] | None = None):
        self._on_level = on_level
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if self._stream is not None:
            return
        with self._lock:
            self._chunks = []
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=BLOCK_SIZE,
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata, frames, time_info, status):
        block = indata[:, 0].copy()
        with self._lock:
            self._chunks.append(block)
        if self._on_level is not None and block.size:
            self._on_level(float(np.sqrt(np.mean(block**2))))

    def stop(self) -> np.ndarray:
        stream, self._stream = self._stream, None
        if stream is not None:
            stream.stop()  # wartet, bis der Callback nicht mehr läuft
            stream.close()
        with self._lock:
            chunks, self._chunks = self._chunks, []
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks)
