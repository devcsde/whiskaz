# whiskaz

Lokales Push-to-talk-Diktat für Debian/Ubuntu und macOS.

Solange du die Taste gedrückt hältst, nimmt whiskaz auf. Beim Loslassen wird der Text lokal erkannt und an der Cursorposition eingefügt. Es gibt keinen Cloud-Dienst, keine Konten und keine API-Schlüssel. Die Spracherkennung läuft mit [faster-whisper](https://github.com/SYSTRAN/faster-whisper) auf dem eigenen Rechner.

## Funktionen

- Push-to-talk mit einer frei wählbaren Taste (Standard: rechte Strg-Taste unter Linux, rechte Cmd-Taste unter macOS)
- Zwei Tastenmodi: **Halten** (gedrückt halten zum Sprechen) oder **Umschalten** (einmal drücken startet, nochmal drücken stoppt)
- Kleines Overlay während der Aufnahme mit Pegel. Es lässt sich mit der Maus verschieben, die Position wird gespeichert. Zum Start sitzt es oben links, in der Mitte oder oben rechts. Es verschwindet beim Stoppen.
- Fenster mit Diktat-Status, Pegelanzeige und Start/Stopp-Knopf
- Verlauf aller Diktate, durchsuchbar, mit Kopieren und Löschen. Dort siehst du auch, welche Wörterbuch-Korrekturen gegriffen haben.
- Wörterbuch für Namen und Fachbegriffe:
  - **Wörter** werden der Erkennung als Vorgabe mitgegeben.
  - **Korrekturen** ersetzen erkannte Schreibweisen zuverlässig, auch wenn Wörter zusammengeschrieben oder mit Bindestrich getrennt sind. „cloud code“ wird so zu „Claude Code“, „CloudCode“ und „Cloud-Code“ ebenfalls. „Cloudflare“ bleibt unverändert, weil nur ganze Wörter ersetzt werden.
- Einstellungen für Taste, Modell, Sprache und Einfügemodus
- Tray-Icon, sofern dein Desktop eines anbietet

## Installation unter Debian/Ubuntu

Das Paket wird lokal gebaut. Es enthält eine eigene Python-Umgebung mit allen Abhängigkeiten.

```bash
sudo apt install dpkg-dev python3-venv
./scripts/build-deb.sh
sudo apt install ./dist/whiskaz_0.1.0-1_amd64.deb
```

Danach startest du whiskaz über das Anwendungsmenü oder mit `whiskaz`. Das Paket ist rund 150 MB groß und belegt installiert etwa 730 MB. Der Großteil sind PySide6 und die Spracherkennungs-Bibliotheken.

**Wichtig:** Baue das Paket auf der Debian- bzw. Ubuntu-Version, auf der du es installieren willst. Die Python-Wheels sind an Python-Version und Architektur gebunden.

### Wayland

Globale Tasten lassen sich unter Wayland nicht zuverlässig abfangen. Melde dich deshalb für whiskaz mit einer X11-Sitzung an. Im Anmeldebildschirm findest du das über das Zahnrad-Symbol, dort etwa „GNOME on Xorg“ oder „Ubuntu on Xorg“, sofern angeboten.

### Erster Start

Beim ersten Start lädt whiskaz das Erkennungsmodell herunter. Das Modell `small` ist rund 480 MB groß. Das dauert einmalig. Danach läuft die Erkennung offline.

## Installation unter macOS

Die Mac-Version ist **noch nicht auf einem Mac getestet**. Zwei Wege:

**A) Direkt aus dem Quellcode starten** (am schnellsten zum Ausprobieren, Python 3.10 oder neuer nötig):

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/whiskaz
```

**B) Als `whiskaz.app` bauen** (Doppelklick, wie eine normale App):

```bash
brew install librsvg
./scripts/build-mac-app.sh
```

Das Ergebnis liegt in `dist/whiskaz.app` und als ZIP in `dist/whiskaz-0.1.0-macos.zip`. Alternativ baut GitHub Actions die App automatisch, sobald das Repo auf GitHub liegt (Workflow „macOS-App“, Artefakt `whiskaz-macos`).

Die App ist nicht signiert. Beim ersten Start blockiert macOS sie. Dann: Rechtsklick auf `whiskaz.app`, „Öffnen“ wählen. Alternativ im Terminal:

```bash
xattr -dr com.apple.quarantine whiskaz.app
```

Damit whiskaz funktioniert, brauchst du drei Freigaben unter **Systemeinstellungen → Datenschutz & Sicherheit**:

- **Mikrofon**, für die Aufnahme
- **Bedienungshilfen**, damit whiskaz einfügen darf
- **Eingabeüberwachung**, damit die Push-to-talk-Taste erkannt wird

Freigeben musst du das Programm, das whiskaz startet, also zum Beispiel Terminal oder iTerm.

## Bedienung

1. Setze den Cursor in ein beliebiges Textfeld.
2. Im Modus **Halten**: Taste gedrückt halten und sprechen, dann loslassen. Im Modus **Umschalten**: einmal drücken, sprechen, nochmal drücken.
3. Der Text erscheint nach kurzer Zeit an der Cursorposition.

Tipps:

- Im Modus **Umschalten** lässt sich die Taste nach dem ersten Druck loslassen. Erst der nächste Druck stoppt die Aufnahme.
- Das Overlay zeigt während der Aufnahme eine rote Lampe und den Pegel. Verschieben geht mit der Maus, die Position wird gespeichert. Unter **Einstellungen** wählst du eine Startposition oder schaltest das Overlay aus.
- Unter **Einstellungen** kannst du „Nach dem Einfügen senden“ auf **Enter** oder **Strg+Enter** stellen. Dann wird der Text nach dem Einfügen direkt abgeschickt, etwa im Chat. Standard ist **Aus**. Der Text wird dann ohne Prüfung abgeschickt, nutze die Option also nur, wenn du dem Ergebnis vertraust.
- Taste unter etwa 0,3 s gilt als Versehen und wird ignoriert.
- Drückst du während des Haltens eine andere Taste, etwa Strg+C, wird die Aufnahme abgebrochen.
- In Terminals fügt Strg+V oft nicht ein. Aktiviere dann unter **Einstellungen** „Ctrl+Shift+V statt Ctrl+V einfügen“.

## Dateien

| Was | Wo (Linux) | Wo (macOS) |
|---|---|---|
| Einstellungen | `~/.config/whiskaz/settings.json` | `~/Library/Application Support/whiskaz/settings.json` |
| Wörterbuch | `~/.config/whiskaz/dictionary.json` | `~/Library/Application Support/whiskaz/dictionary.json` |
| Verlauf | `~/.local/share/whiskaz/history.sqlite3` | `~/Library/Application Support/whiskaz/history.sqlite3` |

Das Wörterbuch lässt sich auch direkt als JSON bearbeiten. Starte whiskaz danach neu.

## Entwicklung

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

Projektaufbau:

- `src/whiskaz/app.py`: Hauptfenster, Tray und Ablaufsteuerung
- `src/whiskaz/audio.py`: Mikrofonaufnahme
- `src/whiskaz/engine.py`: Spracherkennung, mit Filter gegen typische Fantasie-Sätze bei Stille
- `src/whiskaz/dictionary.py`: Wörterbuch und Korrektur-Regeln
- `src/whiskaz/hotkey.py`: globale Push-to-talk-Taste (Modi Halten und Umschalten)
- `src/whiskaz/overlay.py`: Aufnahme-Overlay
- `src/whiskaz/inject.py`: Einfügen über die Zwischenablage
- `scripts/build-deb.sh`: baut das Debian-Paket

## Status

Autor: [devcs.de](https://devcs.de). Lizenz: MIT, siehe [LICENSE](LICENSE). Du darfst whiskaz nutzen, verändern und weitergeben, auch kommerziell. Der Copyright-Hinweis muss erhalten bleiben.
