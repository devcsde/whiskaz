"""Verlauf aller Diktate in einer SQLite-Datei."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from whiskaz.paths import data_dir


@dataclass
class Entry:
    id: int
    created_at: str
    text: str
    raw: str
    corrections: list[list]  # [quelle, ziel, anzahl]


class History:
    def __init__(self, path=None):
        self._conn = sqlite3.connect(path or (data_dir() / "history.sqlite3"))
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                text TEXT NOT NULL,
                raw TEXT NOT NULL,
                corrections TEXT NOT NULL DEFAULT '[]'
            )"""
        )
        self._conn.commit()

    def add(self, text: str, raw: str, corrections: list[list]) -> Entry:
        created = datetime.now().isoformat(timespec="seconds")
        cursor = self._conn.execute(
            "INSERT INTO entries (created_at, text, raw, corrections) VALUES (?, ?, ?, ?)",
            (created, text, raw, json.dumps(corrections, ensure_ascii=False)),
        )
        self._conn.commit()
        return Entry(cursor.lastrowid, created, text, raw, corrections)

    def search(self, query: str = "", limit: int = 500) -> list[Entry]:
        if query.strip():
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            rows = self._conn.execute(
                "SELECT id, created_at, text, raw, corrections FROM entries "
                "WHERE text LIKE ? ESCAPE '\\' ORDER BY id DESC LIMIT ?",
                (f"%{escaped}%", limit),
            )
        else:
            rows = self._conn.execute(
                "SELECT id, created_at, text, raw, corrections FROM entries ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        return [Entry(i, c, t, r, json.loads(k)) for i, c, t, r, k in rows.fetchall()]

    def delete(self, entry_id: int) -> None:
        self._conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
