"""whiskaz: Hauptfenster, Tray-Icon und Verdrahtung von Hotkey, Aufnahme, Erkennung und Einfügen."""

import math
import sys
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from whiskaz import __version__
from whiskaz.audio import SAMPLE_RATE, Recorder
from whiskaz.dictionary import Correction, Dictionary, warnings_for
from whiskaz.engine import Engine
from whiskaz.history import History
from whiskaz.hotkey import HotkeyListener, resolve_key
from whiskaz.inject import Paster
from whiskaz.overlay import RecordingOverlay, overlay_position
from whiskaz.paths import asset_path
from whiskaz.settings import (
    ANCHOR_CHOICES,
    AUTO_SEND_CHOICES,
    DEFAULT_HOTKEY,
    HOTKEY_CHOICES,
    LANGUAGE_CHOICES,
    MODE_CHOICES,
    MODEL_CHOICES,
    Settings,
    hotkey_label,
)
from whiskaz.theme import STYLE

MIN_DURATION_S = 0.3  # kürzere Tipper gelten als Versehen


def accessibility_missing() -> bool:
    """macOS: True, wenn whiskaz keine Bedienungshilfen-Freigabe hat. Sonst immer False."""
    if sys.platform != "darwin":
        return False
    try:
        from ApplicationServices import AXIsProcessTrusted
    except ImportError:
        return False
    return not AXIsProcessTrusted()


class ModelLoader(QThread):
    done = Signal(bool, str, str)  # Erfolg, Modellname, Fehlertext

    def __init__(self, engine: Engine, name: str, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._name = name

    def run(self):
        try:
            self._engine.load(self._name)
            self.done.emit(True, self._name, "")
        except Exception as exc:  # Netzwerk, Speicher, fehlende Bibliothek
            self.done.emit(False, self._name, str(exc))


class Transcriber(QThread):
    done = Signal(object)  # str bei Erfolg, Exception bei Fehler

    def __init__(self, engine: Engine, audio, language: str, prompt: str, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._audio = audio
        self._language = language
        self._prompt = prompt

    def run(self):
        try:
            self.done.emit(self._engine.transcribe(self._audio, self._language, self._prompt))
        except Exception as exc:
            self.done.emit(exc)


def format_level(rms: float) -> int:
    """Lineares RMS auf eine Skala von 0 bis 100, bei -60 dBFS beginnend."""
    db = 20 * math.log10(max(rms, 1e-5))
    return max(0, min(100, int((db + 60) * 100 / 60)))


class MainWindow(QMainWindow):
    levelChanged = Signal(float)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("whiskaz")
        self.resize(860, 620)

        self.settings = Settings.load()
        self.dictionary = Dictionary.load()
        self.history = History()
        self.engine = Engine()
        self.recorder = Recorder(on_level=self.levelChanged.emit)
        self.overlay = RecordingOverlay()
        self.overlay.moved.connect(self._on_overlay_moved)
        self.levelChanged.connect(self._on_level)

        self._state = "loading"  # loading, idle, recording, busy
        self._requested_model = self.settings.model
        self._listener: HotkeyListener | None = None
        self._paster = Paster(QApplication.clipboard(), self.settings.terminal_paste, self.settings.auto_send)
        self._tray: QSystemTrayIcon | None = None

        self._build_ui()
        self._build_menu()
        self._build_tray()
        self._start_hotkey()
        self._load_model(self.settings.model)
        self._refresh_history()
        self._refresh_dictionary()

    # ----- Aufbau -----

    def _build_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(self._build_dictate_tab(), "Diktat")
        self.tabs.addTab(self._build_history_tab(), "Verlauf")
        self.tabs.addTab(self._build_dictionary_tab(), "Wörterbuch")
        self.tabs.addTab(self._build_settings_tab(), "Einstellungen")
        self.setStyleSheet(STYLE)

    def _build_dictate_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        self.status_label = QLabel()
        self.status_label.setObjectName("status")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        self.level_bar.setTextVisible(False)
        self.level_bar.setObjectName("level")
        layout.addWidget(self.level_bar)

        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        self.toggle_button = QPushButton("Aufnahme starten")
        self.toggle_button.clicked.connect(self._on_toggle_clicked)
        self.toggle_button.setEnabled(False)
        layout.addWidget(self.toggle_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.last_label = QLabel()
        self.last_label.setWordWrap(True)
        self.last_label.setObjectName("last")
        layout.addWidget(self.last_label)

        layout.addStretch(1)
        self._update_hint()
        return page

    def _build_history_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Verlauf durchsuchen …")
        self.search_input.textChanged.connect(self._refresh_history)
        layout.addWidget(self.search_input)

        self.history_table = QTableWidget(0, 3)
        self.history_table.setHorizontalHeaderLabels(["Zeit", "Text", "Korrekturen"])
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.verticalHeader().setVisible(False)
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.history_table, 1)

        buttons = QHBoxLayout()
        copy_button = QPushButton("Kopieren")
        copy_button.clicked.connect(self._copy_selected)
        delete_button = QPushButton("Löschen")
        delete_button.clicked.connect(self._delete_selected)
        buttons.addWidget(copy_button)
        buttons.addWidget(delete_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return page

    def _build_dictionary_tab(self) -> QWidget:
        page = QWidget()
        columns = QHBoxLayout(page)

        words_box = QGroupBox("Wörter (Vorgabe für die Erkennung)")
        words_layout = QVBoxLayout(words_box)
        self.words_list = QListWidget()
        self.words_list.itemChanged.connect(self._on_words_edited)
        words_layout.addWidget(self.words_list, 1)
        word_row = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("z. B. Anthropic")
        self.word_input.returnPressed.connect(self._add_word)
        add_word = QPushButton("Hinzufügen")
        add_word.clicked.connect(self._add_word)
        remove_word = QPushButton("Entfernen")
        remove_word.clicked.connect(self._remove_word)
        word_row.addWidget(self.word_input, 1)
        word_row.addWidget(add_word)
        word_row.addWidget(remove_word)
        words_layout.addLayout(word_row)
        columns.addWidget(words_box, 1)

        corrections_box = QGroupBox("Korrekturen (erkannt → schreibe)")
        corrections_layout = QVBoxLayout(corrections_box)
        self.corr_table = QTableWidget(0, 2)
        self.corr_table.setHorizontalHeaderLabels(["Erkannt als", "Schreibe"])
        self.corr_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.corr_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.corr_table.verticalHeader().setVisible(False)
        self.corr_table.cellChanged.connect(self._on_corrections_edited)
        corrections_layout.addWidget(self.corr_table, 1)
        corr_row = QHBoxLayout()
        self.corr_source = QLineEdit()
        self.corr_source.setPlaceholderText("cloud code")
        self.corr_target = QLineEdit()
        self.corr_target.setPlaceholderText("Claude Code")
        self.corr_target.returnPressed.connect(self._add_correction)
        corr_row.addWidget(self.corr_source, 1)
        corr_row.addWidget(self.corr_target, 1)
        corrections_layout.addLayout(corr_row)
        corr_buttons = QHBoxLayout()
        add_corr = QPushButton("Hinzufügen")
        add_corr.clicked.connect(self._add_correction)
        remove_corr = QPushButton("Entfernen")
        remove_corr.clicked.connect(self._remove_correction)
        corr_buttons.addWidget(add_corr)
        corr_buttons.addWidget(remove_corr)
        corr_buttons.addStretch(1)
        corrections_layout.addLayout(corr_buttons)
        self.corr_warning = QLabel()
        self.corr_warning.setObjectName("warning")
        self.corr_warning.setWordWrap(True)
        corrections_layout.addWidget(self.corr_warning)
        columns.addWidget(corrections_box, 1)
        return page

    def _build_settings_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.hotkey_box = QComboBox()
        self.hotkey_box.setEditable(True)
        self.hotkey_box.addItems(HOTKEY_CHOICES)
        self.hotkey_box.setCurrentText(self.settings.hotkey)
        form.addRow("Push-to-talk-Taste:", self.hotkey_box)

        self.model_box = QComboBox()
        self.model_box.addItems(MODEL_CHOICES)
        self.model_box.setCurrentText(self.settings.model)
        form.addRow("Modell:", self.model_box)

        self.language_box = QComboBox()
        self.language_box.addItems(LANGUAGE_CHOICES)
        self.language_box.setCurrentText(self.settings.language)
        form.addRow("Sprache:", self.language_box)

        self.terminal_check = QCheckBox("Ctrl+Shift+V statt Ctrl+V einfügen (für Terminals)")
        self.terminal_check.setChecked(self.settings.terminal_paste)
        form.addRow("", self.terminal_check)

        self.auto_send_box = QComboBox()
        for value, label in AUTO_SEND_CHOICES:
            self.auto_send_box.addItem(label, value)
        self.auto_send_box.setCurrentIndex(max(0, self.auto_send_box.findData(self.settings.auto_send)))
        self.auto_send_box.setToolTip("Sendet nach dem Einfügen automatisch eine Taste, z. B. zum Absenden im Chat.")
        form.addRow("Nach dem Einfügen senden:", self.auto_send_box)

        auto_send_note = QLabel(
            "Achtung: Mit aktiviertem Senden wird der Text sofort abgeschickt, ohne dass du ihn vorher prüfen kannst."
        )
        auto_send_note.setWordWrap(True)
        form.addRow("", auto_send_note)

        self.mode_box = QComboBox()
        for value, label in MODE_CHOICES:
            self.mode_box.addItem(label, value)
        self.mode_box.setCurrentIndex(max(0, self.mode_box.findData(self.settings.mode)))
        form.addRow("Tastenmodus:", self.mode_box)

        self.overlay_check = QCheckBox("Aufnahme-Overlay anzeigen")
        self.overlay_check.setChecked(self.settings.overlay_enabled)
        form.addRow("", self.overlay_check)

        self.anchor_box = QComboBox()
        for value, label in ANCHOR_CHOICES:
            self.anchor_box.addItem(label, value)
        self.anchor_box.setCurrentIndex(max(0, self.anchor_box.findData(self.settings.overlay_anchor)))
        form.addRow("Startposition Overlay:", self.anchor_box)

        overlay_note = QLabel(
            "Das Overlay lässt sich mit der Maus verschieben, die Position wird gespeichert. "
            "Eine neue Startposition verwirft die gespeicherte Position."
        )
        overlay_note.setWordWrap(True)
        form.addRow("", overlay_note)

        note = QLabel(
            "Größere Modelle sind genauer, aber langsamer. „small“ ist ein guter Start. "
            "Beim ersten Gebrauch wird das Modell heruntergeladen."
        )
        note.setWordWrap(True)
        form.addRow("", note)

        apply_button = QPushButton("Übernehmen")
        apply_button.clicked.connect(self._apply_settings)
        form.addRow("", apply_button)
        return page

    def _build_menu(self):
        quit_action = QAction("Beenden", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self._quit)
        self.menuBar().addMenu("Datei").addAction(quit_action)

        about_action = QAction("Über whiskaz", self)
        about_action.triggered.connect(self._about)
        self.menuBar().addMenu("Hilfe").addAction(about_action)

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray = QSystemTrayIcon(QIcon(str(asset_path("whiskaz.svg"))), self)
        tray_menu = QMenu()
        show_action = QAction("Fenster zeigen", self)
        show_action.triggered.connect(self._show_window)
        quit_action = QAction("Beenden", self)
        quit_action.triggered.connect(self._quit)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    # ----- Hotkey und Modell -----

    def _start_hotkey(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        try:
            listener = HotkeyListener(self.settings.hotkey, self.settings.mode)
            if self.settings.mode == "toggle":
                listener.pressed.connect(self._on_toggle_clicked)
            else:
                listener.pressed.connect(self._on_pressed)
                listener.released.connect(self._on_released)
                listener.interrupted.connect(self._on_interrupted)
            listener.start()
        except Exception as exc:
            self._show_error(f"Hotkey konnte nicht aktiviert werden: {exc}")
            return
        self._listener = listener
        self._update_hint()

    def _load_model(self, name: str):
        self._requested_model = name
        self._set_state("loading")
        self._show(f"Modell „{name}“ wird geladen … (beim ersten Mal wird es heruntergeladen)")
        loader = ModelLoader(self.engine, name, parent=self)
        loader.done.connect(self._on_model_loaded)
        loader.finished.connect(loader.deleteLater)
        loader.start()

    def _on_model_loaded(self, ok: bool, name: str, error: str):
        if name != self._requested_model:
            return  # ein neueres Modell ist schon angefragt
        if ok:
            self._set_state("idle")
            if accessibility_missing():
                self._show_error(
                    "Bedienungshilfen fehlen. Unter Systemeinstellungen → Datenschutz & Sicherheit → "
                    "Bedienungshilfen whiskaz freigeben und die App danach neu starten."
                )
                return
            self._show(f"Bereit. Halte die {hotkey_label(self.settings.hotkey)} gedrückt und sprich.")
        else:
            self._set_state("error")
            self._show_error(f"Modell konnte nicht geladen werden: {error}")

    # ----- Diktat-Ablauf -----

    def _on_pressed(self):
        if self._state == "loading":
            self._show("Das Modell lädt noch, bitte kurz warten.")
            return
        if self._state != "idle":
            return
        self._start_recording()

    def _start_recording(self):
        try:
            self.recorder.start()
        except Exception as exc:
            self._show_error(f"Mikrofon nicht verfügbar: {exc}")
            return
        self._set_state("recording")
        self._show("Aufnahme läuft …")
        self._show_overlay()

    def _on_released(self):
        if self._state != "recording":
            return
        audio = self.recorder.stop()
        self._hide_overlay()
        self.level_bar.setValue(0)
        if audio.size / SAMPLE_RATE < MIN_DURATION_S:
            self._set_state("idle")
            self._show("Zu kurz. Halte die Taste etwas länger.")
            return
        self._set_state("busy")
        self._show("Wird erkannt …")
        worker = Transcriber(self.engine, audio, self.settings.language, self.dictionary.bias_prompt(), parent=self)
        worker.done.connect(self._on_transcribed)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _on_interrupted(self):
        if self._state != "recording":
            return
        self.recorder.stop()
        self._hide_overlay()
        self.level_bar.setValue(0)
        self._set_state("idle")
        self._show("Aufnahme abgebrochen, weil eine andere Taste gedrückt wurde.")

    def _on_transcribed(self, result):
        self._set_state("idle")
        if isinstance(result, Exception):
            self._show_error(f"Erkennung fehlgeschlagen: {result}")
            return
        raw = result
        text, applied = self.dictionary.apply(raw)
        if not text.strip():
            self._show("Nichts erkannt.")
            return
        self.history.add(text, raw, [list(a) for a in applied])
        self._refresh_history()
        self.last_label.setText(f"Zuletzt: {text}")
        self._paster.paste(text)
        self._show("Eingefügt.")

    def _on_toggle_clicked(self):
        if self._state == "recording":
            self._on_released()
        else:
            self._on_pressed()

    def _on_level(self, rms: float):
        if self._state == "recording":
            level = format_level(rms)
            self.level_bar.setValue(level)
            self.overlay.set_level(level)

    # ----- Overlay -----

    def _show_overlay(self):
        if not self.settings.overlay_enabled:
            return
        area = QApplication.primaryScreen().availableGeometry()
        x, y = overlay_position(
            self.settings.overlay_anchor,
            self.settings.overlay_pos,
            area,
            self.overlay.width(),
            self.overlay.height(),
        )
        self.overlay.show_at(x, y)

    def _hide_overlay(self):
        self.overlay.hide()

    def _on_overlay_moved(self, x: int, y: int):
        self.settings.overlay_pos = [x, y]
        self.settings.save()

    # ----- Zustand und Anzeige -----

    def _set_state(self, state: str):
        self._state = state
        self.toggle_button.setText("Aufnahme stoppen" if state == "recording" else "Aufnahme starten")
        self.toggle_button.setEnabled(state in ("idle", "recording"))
        if self._tray is not None:
            self._tray.setToolTip(f"whiskaz: {state}")

    def _show(self, message: str):
        self.status_label.setProperty("error", False)
        self.status_label.setText(message)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _show_error(self, message: str):
        self.status_label.setProperty("error", True)
        self.status_label.setText(message)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _update_hint(self):
        if self.settings.mode == "toggle":
            how = "Einmal drücken startet die Aufnahme, nochmal drücken stoppt sie."
        else:
            how = "Gedrückt halten zum Sprechen, loslassen zum Einfügen."
        hint = (
            f"Taste: {hotkey_label(self.settings.hotkey)}. {how} "
            "Der erkannte Text wird an der Cursorposition eingefügt."
        )
        if sys.platform == "darwin":
            hint += " whiskaz braucht die Freigaben Mikrofon, Bedienungshilfen und Eingabeüberwachung."
        self.hint_label.setText(hint)

    # ----- Verlauf -----

    def _refresh_history(self):
        entries = self.history.search(self.search_input.text())
        self.history_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            when = datetime.fromisoformat(entry.created_at).strftime("%d.%m.%Y %H:%M:%S")
            corrections = "; ".join(f"{src} → {dst} (×{n})" for src, dst, n in entry.corrections)
            time_item = QTableWidgetItem(when)
            time_item.setData(Qt.ItemDataRole.UserRole, entry.id)
            text_item = QTableWidgetItem(entry.text)
            text_item.setToolTip(f"Erkennung ohne Korrektur:\n{entry.raw}")
            corr_item = QTableWidgetItem(corrections or "–")
            self.history_table.setItem(row, 0, time_item)
            self.history_table.setItem(row, 1, text_item)
            self.history_table.setItem(row, 2, corr_item)

    def _copy_selected(self):
        row = self.history_table.currentRow()
        if row < 0:
            return
        QApplication.clipboard().setText(self.history_table.item(row, 1).text())
        self._show("Kopiert.")

    def _delete_selected(self):
        row = self.history_table.currentRow()
        if row < 0:
            return
        answer = QMessageBox.question(self, "Löschen", "Diesen Eintrag wirklich löschen?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.history.delete(self.history_table.item(row, 0).data(Qt.ItemDataRole.UserRole))
        self._refresh_history()

    # ----- Wörterbuch -----

    def _refresh_dictionary(self):
        self.words_list.blockSignals(True)
        self.words_list.clear()
        for word in self.dictionary.words:
            item = QListWidgetItem(word)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.words_list.addItem(item)
        self.words_list.blockSignals(False)

        self.corr_table.blockSignals(True)
        self.corr_table.setRowCount(len(self.dictionary.corrections))
        for row, correction in enumerate(self.dictionary.corrections):
            self.corr_table.setItem(row, 0, QTableWidgetItem(correction.source))
            self.corr_table.setItem(row, 1, QTableWidgetItem(correction.target))
        self.corr_table.blockSignals(False)

    def _add_word(self):
        word = self.word_input.text().strip()
        if not word or word in self.dictionary.words:
            return
        self.dictionary.words.append(word)
        self.dictionary.save()
        self.word_input.clear()
        self._refresh_dictionary()

    def _remove_word(self):
        row = self.words_list.currentRow()
        if row < 0:
            return
        del self.dictionary.words[row]
        self.dictionary.save()
        self._refresh_dictionary()

    def _on_words_edited(self, _item):
        self.dictionary.words = [
            self.words_list.item(i).text().strip()
            for i in range(self.words_list.count())
            if self.words_list.item(i).text().strip()
        ]
        self.dictionary.save()

    def _add_correction(self):
        source = self.corr_source.text().strip()
        target = self.corr_target.text().strip()
        if not source or not target:
            self.corr_warning.setText("Beide Felder ausfüllen: erkannte Schreibweise und Zielschreibweise.")
            return
        self.dictionary.corrections.append(Correction(source, target))
        self.dictionary.save()
        self.corr_source.clear()
        self.corr_target.clear()
        self.corr_warning.setText("\n".join(warnings_for(source)))
        self._refresh_dictionary()

    def _remove_correction(self):
        row = self.corr_table.currentRow()
        if row < 0:
            return
        del self.dictionary.corrections[row]
        self.dictionary.save()
        self._refresh_dictionary()

    def _on_corrections_edited(self, row: int, _column: int):
        if row >= len(self.dictionary.corrections):
            return
        source = (self.corr_table.item(row, 0) or QTableWidgetItem("")).text().strip()
        target = (self.corr_table.item(row, 1) or QTableWidgetItem("")).text().strip()
        if not source or not target:
            return
        self.dictionary.corrections[row] = Correction(source, target)
        self.dictionary.save()

    # ----- Einstellungen -----

    def _apply_settings(self):
        hotkey = self.hotkey_box.currentText().strip() or DEFAULT_HOTKEY
        try:
            resolve_key(hotkey)
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self.settings.hotkey = hotkey
        self.settings.model = self.model_box.currentText()
        self.settings.language = self.language_box.currentText()
        self.settings.terminal_paste = self.terminal_check.isChecked()
        self.settings.auto_send = self.auto_send_box.currentData()
        self.settings.mode = self.mode_box.currentData()
        self.settings.overlay_enabled = self.overlay_check.isChecked()
        anchor = self.anchor_box.currentData()
        if anchor != self.settings.overlay_anchor:
            self.settings.overlay_pos = None  # neue Startposition verwirft die gespeicherte
        self.settings.overlay_anchor = anchor
        self.settings.save()
        self._paster = Paster(QApplication.clipboard(), self.settings.terminal_paste, self.settings.auto_send)
        self._start_hotkey()
        if self.settings.model != self._requested_model:
            self._load_model(self.settings.model)
        self._show("Einstellungen gespeichert.")

    # ----- Fenster, Tray, Beenden -----

    def _show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _about(self):
        QMessageBox.about(
            self,
            "Über whiskaz",
            f"whiskaz {__version__}\n\nLokales Push-to-talk-Diktat. "
            "Die Spracherkennung läuft vollständig auf diesem Rechner (faster-whisper).",
        )

    def closeEvent(self, event):
        if self._tray is not None and self._tray.isVisible():
            event.ignore()
            self.hide()
            return
        self._quit()
        event.accept()

    def _quit(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        if self.recorder.recording:
            self.recorder.stop()
        self.history.close()
        QApplication.quit()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("whiskaz")
    app.setApplicationDisplayName("whiskaz")
    app.setDesktopFileName("whiskaz")
    app.setWindowIcon(QIcon(str(asset_path("whiskaz.svg"))))
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    return app.exec()
