from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from playxls.layout import LayoutDefinition, LayoutNode, collect_cells, count_cells, preset_layouts, remove_leaf_at, split_leaf_at
from playxls.keybindings import normalize_combo
from playxls.models import AppSettings, KeyBinding
from playxls.theme import Theme
from playxls.ui.widgets import LayoutThumbnailWidget, SegmentedControl, action_button, clear_layout, make_section_label


class DiagnosticsDialog(QDialog):
    def __init__(self, theme: Theme, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Diagnostics")
        self.setModal(False)
        self.resize(820, 620)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        header = QLabel("Diagnostics")
        header.setStyleSheet(f"font-size:16px;font-weight:600;color:{theme.text_primary};")
        root.addWidget(header)
        viewer = QPlainTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(text)
        viewer.setStyleSheet(
            f'font-family:"JetBrains Mono", monospace;'
            f"background:{theme.surface2};color:{theme.text_primary};border:1px solid {theme.border};"
        )
        root.addWidget(viewer, 1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        root.addLayout(footer)


class SettingsDialog(QDialog):
    settings_changed = Signal(object)
    bindings_changed = Signal(object)

    def __init__(self, theme: Theme, settings: AppSettings, bindings: list[KeyBinding], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.settings = settings
        self.bindings = bindings
        self.recording_binding: KeyBinding | None = None
        self.recording_button: QPushButton | None = None
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(768, 640)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        title = QLabel("Settings")
        title.setStyleSheet(f"font-size:16px;font-weight:600;color:{theme.text_primary};padding:12px;background:{theme.surface2};")
        close = QPushButton("×")
        close.clicked.connect(self.accept)
        header.addWidget(title, 1)
        header.addWidget(close)
        root.addLayout(header)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        self.nav = QListWidget()
        self.nav.setFixedWidth(158)
        self.stack = QStackedWidget()
        for name, widget in [
            ("Appearance", self._appearance()),
            ("Playback", self._playback()),
            ("Library", self._library()),
            ("Shortcuts", self._shortcuts()),
            ("Advanced", self._advanced()),
        ]:
            item = QListWidgetItem(name)
            self.nav.addItem(item)
            self.stack.addWidget(widget)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        body.addWidget(self.nav)
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)
        footer = QHBoxLayout()
        footer.setContentsMargins(12, 8, 12, 12)
        saved = QLabel("Saved automatically")
        saved.setStyleSheet(f"color:{theme.text_tertiary};")
        done = QPushButton("Done")
        done.setObjectName("primaryButton")
        done.clicked.connect(self.accept)
        footer.addWidget(saved, 1)
        footer.addWidget(done)
        root.addLayout(footer)

    def _appearance(self) -> QWidget:
        panel, form = self._form_panel()
        theme_control = SegmentedControl([("dark", "Dark"), ("light", "Light")], self.settings.theme, self.theme)
        theme_control.changed.connect(lambda value: self._patch(theme=value))
        form.addRow("Theme", theme_control)
        border_control = SegmentedControl([("always", "Always"), ("hover", "Hover"), ("never", "Hidden")], self.settings.border_mode, self.theme)
        border_control.changed.connect(lambda value: self._patch(border_mode=value))
        form.addRow("Border visibility", border_control)
        expand = QCheckBox()
        expand.setChecked(self.settings.expand_on_hover)
        expand.toggled.connect(lambda value: self._patch(expand_on_hover=value))
        form.addRow("Expand cell on hover", expand)
        form.addRow("Expand amount", self._slider(105, 200, self.settings.expand_percent, lambda value: self._patch(expand_percent=value)))
        volume = QCheckBox()
        volume.setChecked(self.settings.volume_on_hover)
        volume.toggled.connect(lambda value: self._patch(volume_on_hover=value))
        form.addRow("Adjust volume on hover", volume)
        mode = SegmentedControl([("boost", "Boost"), ("duck", "Duck")], self.settings.hover_volume_mode, self.theme)
        mode.changed.connect(lambda value: self._patch(hover_volume_mode=value))
        form.addRow("Volume mode", mode)
        form.addRow("Volume amount", self._slider(10, 80, self.settings.hover_volume_amount, lambda value: self._patch(hover_volume_amount=value)))
        return panel

    def _playback(self) -> QWidget:
        panel, form = self._form_panel()
        for label, attr in [
            ("Pause when minimized", "pause_on_minimize"),
            ("Disable screensaver while playing", "disable_screensaver"),
            ("Resume videos where you left off", "save_playback_position"),
            ("Normalize local-video audio", "audio_normalize"),
        ]:
            box = QCheckBox()
            box.setChecked(bool(getattr(self.settings, attr)))
            box.toggled.connect(lambda value, name=attr: self._patch(**{name: value}))
            form.addRow(label, box)
        sync = SegmentedControl([("disabled", "Disabled"), ("soft", "Soft"), ("hard", "Hard")], self.settings.seek_sync_mode, self.theme)
        sync.changed.connect(lambda value: self._patch(seek_sync_mode=value))
        form.addRow("Seek sync mode", sync)
        return panel

    def _library(self) -> QWidget:
        panel, form = self._form_panel()
        strategy = SegmentedControl([("off", "Off"), ("lazy", "Lazy"), ("thumb", "Thumb")], self.settings.preview_mode, self.theme)
        strategy.changed.connect(lambda value: self._patch(preview_mode=value))
        form.addRow("Strategy", strategy)
        delay = QSpinBox()
        delay.setRange(0, 2000)
        delay.setValue(self.settings.preview_delay)
        delay.valueChanged.connect(lambda value: self._patch(preview_delay=value))
        form.addRow("Hover delay", delay)
        cache = QSpinBox()
        cache.setRange(1, 20)
        cache.setValue(self.settings.preview_cache_size)
        cache.valueChanged.connect(lambda value: self._patch(preview_cache_size=value))
        form.addRow("Cache size", cache)
        mute = QCheckBox()
        mute.setChecked(self.settings.preview_mute)
        mute.toggled.connect(lambda value: self._patch(preview_mute=value))
        form.addRow("Mute previews", mute)
        return panel

    def _shortcuts(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)
        layout.addWidget(make_section_label("Shortcuts", self.theme))
        for binding in self.bindings:
            row = QFrame()
            row.setStyleSheet(f"background:{self.theme.surface2};border:1px solid {self.theme.border};border-radius:6px;")
            row_layout = QHBoxLayout(row)
            row_layout.addWidget(QLabel(binding.action), 1)
            button = QPushButton(binding.combo)
            button.clicked.connect(lambda _=False, b=binding, btn=button: self._record_binding(b, btn))
            row_layout.addWidget(button)
            layout.addWidget(row)
        layout.addStretch(1)
        return panel

    def _advanced(self) -> QWidget:
        panel, form = self._form_panel()
        profile_scope = SegmentedControl([("shared", "Shared"), ("per_cell", "Per cell")], self.settings.browser_profile_scope, self.theme)
        profile_scope.changed.connect(lambda value: self._patch(browser_profile_scope=value))
        form.addRow("Browser profiles", profile_scope)
        form.addRow("Hardware acceleration", QLabel(self.settings.hw_acceleration))
        form.addRow("Logging level", QLabel(self.settings.logging_level))
        form.addRow("Open log", QPushButton("Open log"))
        return panel

    def _form_panel(self) -> tuple[QWidget, QFormLayout]:
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(18, 18, 18, 18)
        form = QFormLayout()
        form.setSpacing(12)
        outer.addLayout(form)
        outer.addStretch(1)
        return panel, form

    def _slider(self, low: int, high: int, value: int, callback) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high)
        slider.setValue(value)
        slider.valueChanged.connect(callback)
        return slider

    def _patch(self, **patch) -> None:
        for key, value in patch.items():
            setattr(self.settings, key, value)
        self.settings_changed.emit(self.settings)

    def _record_binding(self, binding: KeyBinding, button: QPushButton) -> None:
        self.recording_binding = binding
        self.recording_button = button
        button.setText("recording...")
        button.setProperty("recording_binding", binding.id)
        button.setFocus()
        self.setFocus()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        if self.recording_binding is None or self.recording_button is None:
            super().keyPressEvent(event)
            return
        combo = self._event_combo(event)
        if not combo:
            return
        self.recording_binding.combo = combo
        self.recording_button.setText(combo)
        self.recording_button.setProperty("recording_binding", "")
        self.recording_binding = None
        self.recording_button = None
        self.bindings_changed.emit(self.bindings)

    def _event_combo(self, event: QKeyEvent) -> str:
        if event.key() in (Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift, Qt.Key.Key_Meta):
            return ""
        pieces: list[str] = []
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            pieces.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            pieces.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            pieces.append("Shift")
        key_text = {
            Qt.Key.Key_Space: "Space",
            Qt.Key.Key_Escape: "Esc",
            Qt.Key.Key_Comma: ",",
        }.get(event.key(), event.text().upper() if event.text() else "")
        if key_text:
            pieces.append(key_text)
        return normalize_combo("+".join(pieces))


class GridEditorDialog(QDialog):
    layout_saved = Signal(object)

    def __init__(self, theme: Theme, initial: LayoutDefinition, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.tree = initial.tree
        self.history: list[LayoutNode] = []
        self.selected_path: tuple[str, ...] = ()
        self.setWindowTitle("Grid Editor")
        self.resize(760, 560)
        root = QHBoxLayout(self)
        rail = QVBoxLayout()
        rail.addWidget(make_section_label("Templates", theme))
        for layout in preset_layouts():
            button = QPushButton(layout.label)
            button.clicked.connect(lambda _=False, tree=layout.tree: self._set_tree(tree))
            rail.addWidget(button)
        rail.addSpacing(16)
        rail.addWidget(make_section_label("Edit", theme))
        rail.addWidget(action_button("Split vertical", lambda: self._split("v"), theme))
        rail.addWidget(action_button("Split horizontal", lambda: self._split("h"), theme))
        rail.addWidget(action_button("Remove cell", self._remove, theme))
        rail.addWidget(action_button("Undo", self._undo, theme))
        rail.addWidget(action_button("Reset", lambda: self._set_tree(initial.tree), theme))
        rail.addStretch(1)
        self.name = QLineEdit(initial.label if initial.custom else "")
        self.name.setPlaceholderText("Layout name")
        rail.addWidget(self.name)
        save = action_button("Save Layout", self._save, theme, primary=True)
        rail.addWidget(save)
        root.addLayout(rail, 0)
        self.preview_host = QFrame()
        self.preview_host.setStyleSheet(f"background:{theme.bg};border:1px solid {theme.border};border-radius:8px;")
        self.preview_layout = QVBoxLayout(self.preview_host)
        self.preview_layout.setContentsMargins(24, 24, 24, 24)
        root.addWidget(self.preview_host, 1)
        self._render_preview()

    def _render_preview(self) -> None:
        clear_layout(self.preview_layout)
        self.preview_layout.addWidget(LayoutThumbnailWidget(self.tree, self.theme, active=True))
        count = QLabel(f"{count_cells(self.tree)} cells")
        count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count.setStyleSheet(f"color:{self.theme.text_secondary};")
        self.preview_layout.addWidget(count)
        self.preview_layout.addStretch(1)

    def _push(self) -> None:
        self.history.append(self.tree)

    def _set_tree(self, tree: LayoutNode) -> None:
        self._push()
        self.tree = tree
        self._render_preview()

    def _split(self, direction: str) -> None:
        self._push()
        self.tree = split_leaf_at(self.tree, self.selected_path, "h" if direction == "h" else "v")
        self._render_preview()

    def _remove(self) -> None:
        self._push()
        cells = collect_cells(self.tree)
        if len(cells) > 1:
            self.tree = remove_leaf_at(self.tree, cells[-1].path)
        self._render_preview()

    def _undo(self) -> None:
        if self.history:
            self.tree = self.history.pop()
            self._render_preview()

    def _save(self) -> None:
        label = self.name.text().strip() or "Custom layout"
        self.layout_saved.emit(LayoutDefinition(id="", label=label, tree=self.tree, custom=True))
        self.accept()
