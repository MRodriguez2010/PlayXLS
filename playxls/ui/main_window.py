from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QDragEnterEvent, QDropEvent, QIcon, QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from playxls.assets import app_icon_path, title_mark_path
from playxls.browser import browser_compatibility_notice, normalize_browser_url
from playxls.config import ConfigStore
from playxls.folders import DEFAULT_SCAN_INTERVAL_SECONDS, FolderScanner, scan_folder
from playxls.keybindings import KeyBindingRegistry, normalize_combo
from playxls.layout import LayoutDefinition, count_cells, preset_layouts
from playxls.models import VIDEO_EXTENSIONS, AppState, BrowserPreset, CellContent, FolderEntry, VideoItem
from playxls.queueing import adjacent_video, next_video_for_repeat
from playxls.theme import Theme, app_stylesheet, resolve_theme
from playxls.transport import TransportSnapshot
from playxls.ui.dialogs import DiagnosticsDialog, GridEditorDialog, SettingsDialog
from playxls.ui.grid import GridStage
from playxls.ui.panels import SourcesPanel
from playxls.ui.widgets import LayoutThumbnailWidget, MonoLabel, MultiHeadTimeline, TimelineTrack, ToastHost, make_section_label


DEFAULT_MAIN_SPLITTER_SIZES = [320, 960]


class MainWindow(QMainWindow):
    folder_video_detected = Signal(object)
    folder_scan_refreshed = Signal(object)

    def __init__(
        self,
        state: AppState,
        layouts: list[LayoutDefinition],
        store: ConfigStore,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.state = state
        self.layouts = layouts
        self.store = store
        self.theme = resolve_theme(state.settings.theme)
        self.hovered_cell: int | None = None
        self.active_browser_cell: int | None = None
        self.browser_load_failures: dict[int, str] = {}
        self._auto_advance_eof_keys: set[tuple[int, str]] = set()
        self.resume_after_minimize = False
        self.border_visible = state.settings.border_mode == "always"
        self.border_timer = QTimer(self)
        self.border_timer.setSingleShot(True)
        self.border_timer.timeout.connect(self._hide_hover_borders)
        self.folder_scanner: FolderScanner | None = None
        self.registry = KeyBindingRegistry(state.bindings)
        self._register_keybindings()
        self.folder_video_detected.connect(self._folder_video_added)
        self.folder_scan_refreshed.connect(self._folder_scan_refreshed)
        self.open_external_url = QDesktopServices.openUrl

        self.setWindowTitle("PlayXLS")
        icon_path = app_icon_path()
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setAcceptDrops(True)
        self.resize(1280, 820)
        self.setMinimumSize(960, 620)
        self.setStyleSheet(app_stylesheet(self.theme))

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.title_bar = self._title_bar()
        root.addWidget(self.title_bar)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.sources = SourcesPanel(self.theme)
        self.sources.assign_video.connect(self._assign_video)
        self.sources.assign_browser.connect(self._assign_browser)
        self.sources.add_browser_requested.connect(self._add_browser_preset)
        self.sources.remove_video.connect(self._remove_video)
        self.sources.remove_folder.connect(self._remove_folder)
        self.sources.remove_browser.connect(self._remove_browser_preset)
        self.sources.folders_changed.connect(self._folders_changed)
        self.sources.add_folder_requested.connect(self._add_folder)
        self.main_splitter.addWidget(self.sources)

        self.stage_shell = QWidget()
        self.stage_shell.setStyleSheet(f"background:{self.theme.bg};")
        stage_layout = QVBoxLayout(self.stage_shell)
        stage_layout.setContentsMargins(0, 0, 0, 0)
        stage_layout.setSpacing(0)
        self.toolbar = self._toolbar()
        stage_layout.addWidget(self.toolbar)
        self.browser_toolbar = self._browser_toolbar()
        stage_layout.addWidget(self.browser_toolbar)
        self.stage_frame = QFrame()
        self.stage_frame.setMouseTracking(True)
        self.stage_frame.installEventFilter(self)
        self.stage_frame.setStyleSheet(f"background:{self.theme.bg};padding:20px;")
        stage_inner = QVBoxLayout(self.stage_frame)
        stage_inner.setContentsMargins(20, 20, 20, 20)
        self.grid = GridStage(self.theme, self.store.cache_dir, self.stage_frame)
        self.grid.hovered_changed.connect(self._hovered_changed)
        self.grid.fullscreen_changed.connect(lambda _: self._sync_ui())
        self.grid.cell_cleared.connect(self._clear_cell)
        self.grid.browser_url_changed.connect(self._browser_url_changed)
        self.grid.browser_load_failed.connect(self._browser_load_failed)
        self.grid.browser_load_succeeded.connect(self._browser_load_succeeded)
        self.grid.video_load_failed.connect(self._video_load_failed)
        stage_inner.addWidget(self.grid, 1)
        stage_layout.addWidget(self.stage_frame, 1)
        self.transport = self._transport()
        stage_layout.addWidget(self.transport)
        self.main_splitter.addWidget(self.stage_shell)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self._restore_main_splitter_sizes()
        root.addWidget(self.main_splitter, 1)

        self.toast = ToastHost(self.theme, self.stage_shell)
        self._sync_ui()
        self._start_folder_scanner()
        self.transport_timer = QTimer(self)
        self.transport_timer.setInterval(500)
        self.transport_timer.timeout.connect(self._refresh_transport)
        self.transport_timer.start()
        self._refresh_transport()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._save_session()
        if self.folder_scanner:
            self.folder_scanner.stop()
        self.sources.shutdown()
        self.grid.shutdown()
        super().closeEvent(event)

    def changeEvent(self, event) -> None:  # type: ignore[override]
        if event.type() == QEvent.Type.WindowStateChange:
            self._handle_minimized_for_playback(self.isMinimized())
        super().changeEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        combo = self._event_combo(event)
        if combo and self.registry.dispatch(combo):
            event.accept()
            return
        if combo == "Esc":
            if self.grid.fullscreen_cell is not None:
                self.grid.toggle_fullscreen(self.grid.fullscreen_cell)
            event.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        if watched == getattr(self, "stage_frame", None) and event.type() == QEvent.Type.MouseMove:
            if self.state.settings.border_mode == "hover" and self.grid.fullscreen_cell is None:
                pos = event.position().toPoint()
                near_top = pos.y() <= 12
                near_left = pos.x() <= 12
                near_right = pos.x() >= self.stage_frame.width() - 12
                if near_top or near_left or near_right:
                    self.border_visible = True
                    self.border_timer.start(900)
                    self._sync_ui()
        return super().eventFilter(watched, event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
        if self._video_paths_from_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
        paths = self._video_paths_from_mime(event.mimeData())
        if paths:
            self._add_video_files(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def _title_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(36)
        bar.setStyleSheet(f"background:{self.theme.title_bar};border-bottom:1px solid {self.theme.border};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(22, 22)
        mark_path = title_mark_path()
        if mark_path.exists():
            self.logo_label.setPixmap(QIcon(str(mark_path)).pixmap(22, 22))
        layout.addWidget(self.logo_label)
        title = QLabel("PlayXLS")
        title.setStyleSheet(f"font-size:12px;font-weight:600;color:{self.theme.text_primary};background:transparent;")
        subtitle = MonoLabel("multi-stream player")
        subtitle.setStyleSheet(f'font-family:"JetBrains Mono";font-size:10px;color:{self.theme.text_muted};background:transparent;')
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        self.theme_button = QPushButton("☀" if self.state.settings.theme == "dark" else "☾")
        self.theme_button.setFixedSize(28, 28)
        self.theme_button.setToolTip("Toggle theme (Ctrl+T)")
        self.theme_button.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_button)
        self.grid_meta = MonoLabel("")
        self.grid_meta.setStyleSheet(f'font-family:"JetBrains Mono";font-size:10px;color:{self.theme.text_muted};background:transparent;')
        layout.addWidget(self.grid_meta)
        return bar

    def _toolbar(self) -> QFrame:
        toolbar = QFrame()
        toolbar.setFixedHeight(48)
        toolbar.setStyleSheet(f"background:{self.theme.bg};border-bottom:1px solid {self.theme.border};")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)
        self.layout_button = QPushButton("")
        self.layout_button.clicked.connect(self._layout_menu)
        layout.addWidget(self.layout_button)
        self.border_button = QPushButton("")
        self.border_button.clicked.connect(self._cycle_borders)
        layout.addWidget(self.border_button)
        self.hover_button = QPushButton("hover ▾")
        self.hover_button.clicked.connect(self._hover_menu)
        layout.addWidget(self.hover_button)
        layout.addStretch(1)
        diagnostics = QPushButton("ⓘ")
        diagnostics.setToolTip("Diagnostics")
        diagnostics.clicked.connect(self._open_diagnostics)
        layout.addWidget(diagnostics)
        settings = QPushButton("⚙")
        settings.setToolTip("Settings (Ctrl+,)")
        settings.clicked.connect(self._open_settings)
        layout.addWidget(settings)
        return toolbar

    def _browser_toolbar(self) -> QFrame:
        toolbar = QFrame()
        toolbar.setFixedHeight(44)
        toolbar.setStyleSheet(f"background:{self.theme.surface1};border-bottom:1px solid {self.theme.border};")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)
        self.browser_cell_label = MonoLabel("Browser")
        self.browser_cell_label.setFixedWidth(72)
        self.browser_cell_label.setStyleSheet(f'font-family:"JetBrains Mono";font-size:11px;color:{self.theme.text_muted};background:transparent;')
        layout.addWidget(self.browser_cell_label)
        self.browser_back = QPushButton("‹")
        self.browser_forward = QPushButton("›")
        self.browser_reload = QPushButton("↻")
        self.browser_external = QPushButton("↗")
        self.browser_external.setToolTip("Open in system browser")
        for button in (self.browser_back, self.browser_forward, self.browser_reload, self.browser_external):
            button.setFixedSize(28, 28)
            layout.addWidget(button)
        self.browser_url = QLineEdit()
        self.browser_url.setFixedHeight(28)
        self.browser_url.setPlaceholderText("Browser URL")
        layout.addWidget(self.browser_url, 1)
        self.browser_notice = MonoLabel("")
        self.browser_notice.setFixedWidth(92)
        self.browser_notice.setStyleSheet(f'font-family:"JetBrains Mono";font-size:10px;color:{self.theme.danger};background:transparent;')
        self.browser_notice.hide()
        layout.addWidget(self.browser_notice)
        self.browser_back.clicked.connect(lambda: self._browser_action("back"))
        self.browser_forward.clicked.connect(lambda: self._browser_action("forward"))
        self.browser_reload.clicked.connect(lambda: self._browser_action("reload"))
        self.browser_external.clicked.connect(self._browser_open_external)
        self.browser_url.returnPressed.connect(self._browser_go)
        toolbar.hide()
        return toolbar

    def _transport(self) -> QFrame:
        transport = QFrame()
        transport.setFixedHeight(56)
        transport.setStyleSheet(f"background:{self.theme.surface1};border-top:1px solid {self.theme.border};")
        layout = QHBoxLayout(transport)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        self.previous_button = QPushButton("⏮")
        self.previous_button.setToolTip("Previous video")
        self.previous_button.setFixedSize(32, 32)
        self.previous_button.clicked.connect(lambda: self._skip_video(-1))
        layout.addWidget(self.previous_button)
        self.play_button = QPushButton("Ⅱ")
        self.play_button.setFixedSize(36, 36)
        self.play_button.setStyleSheet(f"border-radius:18px;background:{self.theme.text_primary};color:{self.theme.bg};")
        self.play_button.clicked.connect(self._toggle_play)
        layout.addWidget(self.play_button)
        self.stop_button = QPushButton("■")
        self.stop_button.setToolTip("Stop active video")
        self.stop_button.setFixedSize(32, 32)
        self.stop_button.clicked.connect(self._stop_video)
        layout.addWidget(self.stop_button)
        self.next_button = QPushButton("⏭")
        self.next_button.setToolTip("Next video")
        self.next_button.setFixedSize(32, 32)
        self.next_button.clicked.connect(lambda: self._skip_video(1))
        layout.addWidget(self.next_button)
        self.mute_button = QPushButton("🔊")
        self.mute_button.clicked.connect(self._toggle_mute)
        layout.addWidget(self.mute_button)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setFixedWidth(90)
        self.volume.setRange(0, 100)
        self.volume.setValue(int(self.state.master_volume * 100))
        self.volume.valueChanged.connect(self._set_master_volume)
        layout.addWidget(self.volume)
        self.repeat_button = QPushButton("")
        self.repeat_button.setFixedWidth(42)
        self.repeat_button.setToolTip("Repeat mode")
        self.repeat_button.clicked.connect(self._cycle_repeat_mode)
        layout.addWidget(self.repeat_button)
        self.shuffle_button = QPushButton("")
        self.shuffle_button.setFixedWidth(42)
        self.shuffle_button.setToolTip("Shuffle")
        self.shuffle_button.clicked.connect(self._toggle_shuffle)
        layout.addWidget(self.shuffle_button)
        self.time_left = MonoLabel("--:--")
        self.time_right = MonoLabel("--:--")
        layout.addWidget(self.time_left)
        self.timeline = MultiHeadTimeline(self.theme)
        self.timeline.seek_requested.connect(self._timeline_seek_requested)
        layout.addWidget(self.timeline, 1)
        layout.addWidget(self.time_right)
        sync = MonoLabel("● SYNCED")
        sync.setStyleSheet(f'font-family:"JetBrains Mono";font-size:10px;color:{self.theme.danger};background:transparent;')
        layout.addWidget(sync)
        return transport

    def _register_keybindings(self) -> None:
        self.registry.register("Play / Pause", self._toggle_play)
        self.registry.register("Toggle Grid Borders", self._cycle_borders)
        self.registry.register("Cycle Grid Layout", self._cycle_layout)
        self.registry.register("Mute Hovered", self._toggle_mute)
        self.registry.register("Open Grid Editor", self._open_grid_editor)
        self.registry.register("Open Settings", self._open_settings)
        self.registry.register("Cell Fullscreen", lambda: self.grid.toggle_fullscreen(self.hovered_cell))
        self.registry.register("Toggle Theme", self._toggle_theme)

    def _sync_ui(self) -> None:
        layout = self._current_layout()
        cell_count = count_cells(layout.tree)
        self.state.ensure_cell_capacity(max(20, cell_count))
        self.grid_meta.setText(f"{layout.label} · {cell_count} {'cell' if cell_count == 1 else 'cells'}")
        self.layout_button.setText(f"{layout.label} ▾")
        self.border_button.setText(f"borders {self.state.settings.border_mode}")
        hover_active = self.state.settings.expand_on_hover or self.state.settings.volume_on_hover
        self.hover_button.setChecked(hover_active)
        self.play_button.setText("Ⅱ" if self.state.playing else "▶")
        self.mute_button.setText("🔇" if self.state.muted else "🔊")
        self.repeat_button.setText(self._repeat_button_label())
        self.shuffle_button.setText("⤨" if self.state.shuffle else "⇄")
        self.sources.set_data(
            self.state.library_videos,
            self.state.folders,
            self.state.browser_presets,
            self.state.cell_content,
            cell_count,
            self.state.settings,
        )
        self.grid.set_data(
            layout,
            self.state.cell_content,
            self.state.library_videos,
            self.state.settings,
            self._show_borders(),
            self.state.playback_positions,
        )
        self.grid.set_playing(self.state.playing)
        self.grid.set_volume_state(self.state.master_volume, self.state.muted)
        self._apply_repeat_mode_to_cells()
        self._sync_browser_toolbar()

    def _current_layout(self) -> LayoutDefinition:
        return next((layout for layout in self.layouts if layout.id == self.state.layout_id), self.layouts[0])

    def _show_borders(self) -> bool:
        return self.state.settings.border_mode == "always" or (self.state.settings.border_mode == "hover" and self.border_visible)

    def _layout_menu(self) -> None:
        menu = QMenu(self)
        for layout in self.layouts:
            action = QAction(layout.label, self)
            action.triggered.connect(lambda _=False, layout_id=layout.id: self._set_layout(layout_id))
            menu.addAction(action)
        menu.addSeparator()
        custom = menu.addAction("Create Custom Layout")
        custom.triggered.connect(self._open_grid_editor)
        custom_layouts = [layout for layout in self.layouts if layout.custom]
        if custom_layouts:
            delete_menu = menu.addMenu("Delete Custom Layout")
            for layout in custom_layouts:
                action = QAction(layout.label, self)
                action.triggered.connect(lambda _=False, layout_id=layout.id: self._delete_custom_layout(layout_id))
                delete_menu.addAction(action)
        menu.exec(self.layout_button.mapToGlobal(self.layout_button.rect().bottomLeft()))

    def _hover_menu(self) -> None:
        menu = QMenu(self)
        expand = menu.addAction(f"Expand: {'on' if self.state.settings.expand_on_hover else 'off'}")
        volume = menu.addAction(f"Volume: {'on' if self.state.settings.volume_on_hover else 'off'}")
        scale_up = menu.addAction(f"Scale +10% ({self.state.settings.expand_percent}%)")
        action = menu.exec(self.hover_button.mapToGlobal(self.hover_button.rect().bottomLeft()))
        if action == expand:
            self.state.settings.expand_on_hover = not self.state.settings.expand_on_hover
        elif action == volume:
            self.state.settings.volume_on_hover = not self.state.settings.volume_on_hover
        elif action == scale_up:
            self.state.settings.expand_percent = 105 if self.state.settings.expand_percent >= 200 else min(200, self.state.settings.expand_percent + 10)
        self._settings_changed()

    def _set_layout(self, layout_id: str) -> None:
        self.state.layout_id = layout_id
        self._toast(f"Grid: {self._current_layout().label}")
        self._save_session()
        self._sync_ui()

    def _cycle_layout(self) -> None:
        index = next((i for i, layout in enumerate(self.layouts) if layout.id == self.state.layout_id), 0)
        self._set_layout(self.layouts[(index + 1) % len(self.layouts)].id)

    def _cycle_borders(self) -> None:
        current = self.state.settings.border_mode
        self.state.settings.border_mode = "hover" if current == "always" else "never" if current == "hover" else "always"
        self._settings_changed()
        self._toast(f"Borders: {self.state.settings.border_mode}")

    def _hide_hover_borders(self) -> None:
        if self.state.settings.border_mode == "hover":
            self.border_visible = False
            self._sync_ui()

    def _toggle_theme(self) -> None:
        self.state.settings.theme = "light" if self.state.settings.theme == "dark" else "dark"
        self.theme = resolve_theme(self.state.settings.theme)
        self._apply_theme()
        self._settings_changed(save_only=True)
        self._toast(f"{self.state.settings.theme.title()} mode")

    def _toggle_play(self) -> None:
        self.state.playing = not self.state.playing
        self.grid.set_playing(self.state.playing)
        self._toast("Playing" if self.state.playing else "Paused")
        self._sync_ui()
        self._refresh_transport()

    def _toggle_mute(self) -> None:
        self.state.muted = not self.state.muted
        self.grid.set_volume_state(self.state.master_volume, self.state.muted)
        self._save_session()
        self._toast("Muted" if self.state.muted else "Unmuted")
        self._sync_ui()

    def _cycle_repeat_mode(self) -> None:
        modes = ["none", "one", "all", "folder"]
        index = modes.index(self.state.repeat_mode) if self.state.repeat_mode in modes else 0
        self.state.repeat_mode = modes[(index + 1) % len(modes)]
        self._apply_repeat_mode_to_cells()
        self._save_session()
        self._toast(f"Repeat: {self._repeat_toast_label()}")
        self._sync_ui()

    def _toggle_shuffle(self) -> None:
        self.state.shuffle = not self.state.shuffle
        self._save_session()
        self._toast("Shuffle on" if self.state.shuffle else "Shuffle off")
        self._sync_ui()

    def _repeat_button_label(self) -> str:
        return {
            "none": "↻",
            "one": "↻1",
            "all": "↻∞",
            "folder": "↻F",
        }.get(self.state.repeat_mode, "↻")

    def _repeat_toast_label(self) -> str:
        return {
            "none": "off",
            "one": "one",
            "all": "all",
            "folder": "folder",
        }.get(self.state.repeat_mode, "off")

    def _skip_video(self, direction: int) -> None:
        cell = self._transport_cell()
        if not cell:
            return
        index = int(getattr(cell, "index", -1))
        video = getattr(cell, "video", None)
        if index < 0 or not video:
            return
        next_video = adjacent_video(video, self.state.library_videos, direction=direction)
        if not next_video:
            return
        self.state.ensure_cell_capacity(index + 1)
        self.state.cell_content[index] = CellContent.video(next_video.id)
        self.state.playing = True
        self._save_session()
        action = "Next" if direction >= 0 else "Previous"
        self._toast(f"{action}: {next_video.title} → Cell {index + 1}")
        self._sync_ui()

    def _stop_video(self) -> None:
        cell = self._transport_cell()
        mpv = getattr(cell, "mpv", None) if cell else None
        if not mpv:
            return
        if hasattr(mpv, "seek_absolute"):
            mpv.seek_absolute(0)
        if hasattr(mpv, "set_pause"):
            mpv.set_pause(True)
        self.state.playing = False
        self.play_button.setText("▶")
        self._refresh_transport()
        self.state.playing = False
        self.play_button.setText("▶")
        self._toast("Stopped")

    def _apply_repeat_mode_to_cells(self) -> None:
        loop_current_file = self.state.repeat_mode == "one"
        for cell in self.grid.cells:
            mpv = getattr(cell, "mpv", None)
            if mpv and hasattr(mpv, "set_loop_file"):
                mpv.set_loop_file(loop_current_file)

    def _set_master_volume(self, value: int) -> None:
        self.state.master_volume = value / 100
        self.state.muted = value == 0
        self.grid.set_volume_state(self.state.master_volume, self.state.muted)
        self._save_session()
        self._sync_ui()

    def _handle_minimized_for_playback(self, minimized: bool) -> None:
        if not self.state.settings.pause_on_minimize:
            return
        if minimized:
            self.resume_after_minimize = self.state.playing
            if self.state.playing:
                self.state.playing = False
                self.grid.set_playing(False)
                self.play_button.setText("▶")
            return
        if self.resume_after_minimize:
            self.state.playing = True
            self.grid.set_playing(True)
            self.play_button.setText("Ⅱ")
        self.resume_after_minimize = False

    def _transport_cell(self):
        candidates = []
        fullscreen_cell = self.grid.fullscreen_cell
        if fullscreen_cell is not None and fullscreen_cell < len(self.grid.cells):
            candidates.append(self.grid.cells[fullscreen_cell])
        if self.hovered_cell is not None and self.hovered_cell < len(self.grid.cells):
            candidates.append(self.grid.cells[self.hovered_cell])
        candidates.extend(self.grid.cells)
        seen: set[int] = set()
        for cell in candidates:
            marker = id(cell)
            if marker in seen:
                continue
            seen.add(marker)
            content = getattr(cell, "content", None)
            if getattr(content, "kind", "") != "video" or not getattr(cell, "mpv", None):
                continue
            if hasattr(cell, "isVisible") and not cell.isVisible():
                continue
            return cell
        return None

    def _refresh_transport(self) -> None:
        self.timeline.set_tracks(self._timeline_tracks())
        cell = self._transport_cell()
        mpv = getattr(cell, "mpv", None) if cell else None
        if not mpv:
            snapshot = TransportSnapshot()
            self._set_transport_snapshot(snapshot, enabled=False)
            return
        snapshot = mpv.transport_snapshot()
        if self._auto_advance_finished_video(cell, snapshot):
            return
        self._set_transport_snapshot(snapshot, enabled=True)

    def _auto_advance_finished_video(self, cell, snapshot: TransportSnapshot) -> bool:
        index = int(getattr(cell, "index", -1))
        video = getattr(cell, "video", None)
        if not snapshot.eof_reached:
            self._auto_advance_eof_keys = {key for key in self._auto_advance_eof_keys if key[0] != index}
            return False
        if index < 0 or not video:
            return False
        key = (index, video.id)
        if key in self._auto_advance_eof_keys:
            return False
        next_video = next_video_for_repeat(
            video,
            self.state.library_videos,
            repeat_mode=self.state.repeat_mode,
            shuffle=self.state.shuffle,
        )
        if not next_video:
            return False
        self._auto_advance_eof_keys.add(key)
        self.state.ensure_cell_capacity(index + 1)
        self.state.cell_content[index] = CellContent.video(next_video.id)
        self.state.playing = True
        self._save_session()
        self._toast(f"{next_video.title} → Cell {index + 1}")
        self._sync_ui()
        return True

    def _set_transport_snapshot(self, snapshot: TransportSnapshot, *, enabled: bool) -> None:
        self.time_left.setText(snapshot.position_text)
        self.time_right.setText(snapshot.duration_text)
        if enabled:
            self.state.playing = not snapshot.paused
            self.play_button.setText("Ⅱ" if self.state.playing else "▶")

    def _timeline_tracks(self) -> list[TimelineTrack]:
        tracks: list[TimelineTrack] = []
        for cell in self.grid.cells:
            content = getattr(cell, "content", None)
            mpv = getattr(cell, "mpv", None)
            if getattr(content, "kind", "") != "video" or not mpv or not hasattr(mpv, "transport_snapshot"):
                continue
            snapshot = mpv.transport_snapshot()
            if snapshot.duration:
                tracks.append(TimelineTrack(int(getattr(cell, "index", 0)) + 1, snapshot.position or 0.0, snapshot.duration))
        return tracks

    def _timeline_seek_requested(self, ratio: float) -> None:
        cell = self._transport_cell()
        mpv = getattr(cell, "mpv", None) if cell else None
        if not mpv:
            return
        snapshot = mpv.transport_snapshot()
        if not snapshot.duration:
            return
        timeline_duration = self.timeline.duration or snapshot.duration
        mpv.seek_absolute(min(snapshot.duration, timeline_duration * max(0.0, min(1.0, ratio))))
        self._refresh_transport()

    def _assign_video(self, video_id: str, index: int) -> None:
        self.browser_load_failures.pop(index, None)
        self.state.cell_content[index] = CellContent.video(video_id)
        self._toast(f"→ Cell {index + 1}")
        self._save_session()
        self._sync_ui()

    def _assign_browser(self, preset: BrowserPreset, index: int) -> None:
        self.browser_load_failures.pop(index, None)
        self.state.cell_content[index] = CellContent.browser(preset.url, preset.name)
        self._toast(f"{preset.name} → Cell {index + 1}")
        self._save_session()
        self._sync_ui()

    def _add_browser_preset(self, preset: BrowserPreset) -> None:
        if any(existing.url == preset.url for existing in self.state.browser_presets):
            self._toast("Browser source already exists")
            return
        preset.id = self._unique_browser_id(preset)
        self.state.browser_presets.append(preset)
        self.store.save_browser_presets(self.state.browser_presets)
        self._toast(f"Added: {preset.name}")
        self._sync_ui()

    def _remove_browser_preset(self, preset_id: str) -> None:
        preset = next((item for item in self.state.browser_presets if item.id == preset_id), None)
        if not preset:
            return
        self.state.browser_presets = [item for item in self.state.browser_presets if item.id != preset_id]
        self.state.cell_content = [
            CellContent.empty() if content.kind == "browser" and content.url == preset.url else content
            for content in self.state.cell_content
        ]
        self.store.save_browser_presets(self.state.browser_presets)
        self._save_session()
        self._toast(f"Removed: {preset.name}")
        self._sync_ui()

    def _clear_cell(self, index: int) -> None:
        self.browser_load_failures.pop(index, None)
        self.state.cell_content[index] = CellContent.empty()
        self._toast(f"Cleared {index + 1}")
        self._save_session()
        self._sync_ui()

    def _hovered_changed(self, index: int | None) -> None:
        self.hovered_cell = index
        if index is not None and index < len(self.grid.cells):
            if getattr(getattr(self.grid.cells[index], "content", None), "kind", "") == "browser":
                self.active_browser_cell = index
        self.grid.set_volume_state(self.state.master_volume, self.state.muted)
        self._sync_browser_toolbar()

    def _browser_url_changed(self, index: int, url: str) -> None:
        if self._browser_control_cell_index() != index:
            return
        self.browser_url.blockSignals(True)
        self.browser_url.setText(url)
        self.browser_url.blockSignals(False)

    def _browser_control_cell_index(self) -> int | None:
        candidates = [self.grid.fullscreen_cell, self.active_browser_cell, self.hovered_cell]
        candidates.extend(range(len(self.grid.cells)))
        seen: set[int] = set()
        for index in candidates:
            if index is None or index in seen or index >= len(self.grid.cells):
                continue
            seen.add(index)
            cell = self.grid.cells[index]
            if not cell.isVisible():
                continue
            if getattr(getattr(cell, "content", None), "kind", "") == "browser":
                return index
        return None

    def _browser_control_cell(self):
        index = self._browser_control_cell_index()
        if index is None:
            return None
        return self.grid.cells[index]

    def _sync_browser_toolbar(self) -> None:
        cell = self._browser_control_cell()
        enabled = bool(cell and getattr(cell, "web_view", None))
        self.browser_toolbar.setVisible(bool(cell))
        if not cell:
            self.browser_url.clear()
            self.browser_notice.hide()
            return
        self.active_browser_cell = cell.index
        self.browser_cell_label.setText(f"Cell {cell.index + 1}")
        url = ""
        if getattr(cell, "web_view", None):
            url = cell.web_view.url().toString()
        elif getattr(getattr(cell, "content", None), "url", None):
            url = cell.content.url or ""
        self.browser_url.blockSignals(True)
        self.browser_url.setText(url)
        self.browser_url.blockSignals(False)
        failure = self.browser_load_failures.get(cell.index)
        notice = None if failure else browser_compatibility_notice(getattr(getattr(cell, "content", None), "url", "") or url)
        if failure:
            self.browser_notice.setText(failure)
            self.browser_notice.setToolTip("This page failed to load in the embedded browser. Try opening it in the system browser.")
            self.browser_notice.show()
        elif notice:
            self.browser_notice.setText(notice.label)
            self.browser_notice.setToolTip(notice.detail)
            self.browser_notice.show()
        else:
            self.browser_notice.clear()
            self.browser_notice.setToolTip("")
            self.browser_notice.hide()
        for control in (self.browser_back, self.browser_forward, self.browser_reload, self.browser_url):
            control.setEnabled(enabled)
        self.browser_external.setEnabled(bool(cell and (url or getattr(getattr(cell, "content", None), "url", ""))))

    def _browser_action(self, action: str) -> None:
        cell = self._browser_control_cell()
        view = getattr(cell, "web_view", None) if cell else None
        if not view:
            return
        if action == "back":
            view.back()
        elif action == "forward":
            view.forward()
        elif action == "reload":
            view.reload()

    def _browser_go(self) -> None:
        cell = self._browser_control_cell()
        view = getattr(cell, "web_view", None) if cell else None
        if not view:
            return
        view.setUrl(QUrl(normalize_browser_url(self.browser_url.text())))

    def _browser_open_external(self) -> None:
        cell = self._browser_control_cell()
        if not cell:
            return
        raw_url = getattr(getattr(cell, "content", None), "url", "") or self.browser_url.text()
        if not raw_url:
            return
        self.open_external_url(QUrl(normalize_browser_url(raw_url)))

    def _browser_load_failed(self, index: int, message: str) -> None:
        self.browser_load_failures[index] = message or "Load failed"
        if self._browser_control_cell_index() == index:
            self._sync_browser_toolbar()

    def _browser_load_succeeded(self, index: int) -> None:
        self.browser_load_failures.pop(index, None)
        if self._browser_control_cell_index() == index:
            self._sync_browser_toolbar()

    def _video_load_failed(self, index: int, message: str) -> None:
        self._log_video_load_failure(index, message)
        self._toast(f"Cell {index + 1}: {message or 'Playback failed'}")

    def _log_video_load_failure(self, index: int, message: str) -> None:
        content = self.state.cell_content[index] if 0 <= index < len(self.state.cell_content) else CellContent.empty()
        video = None
        if content.kind == "video" and content.video_id:
            video = next((item for item in self.state.library_videos if item.id == content.video_id), None)
        self.store.append_playback_diagnostic(
            {
                "kind": "video_load_failed",
                "cell": index + 1,
                "video_id": content.video_id if content.kind == "video" else "",
                "title": video.title if video else "",
                "source": (video.path or video.src) if video else "",
                "message": message or "Playback failed",
            }
        )

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.theme, self.state.settings, self.state.bindings, self)
        dialog.settings_changed.connect(lambda settings: self._settings_changed())
        dialog.bindings_changed.connect(self._bindings_changed)
        dialog.exec()
        self._sync_ui()

    def _open_diagnostics(self) -> None:
        dialog = DiagnosticsDialog(self.theme, self._diagnostics_text(), self)
        dialog.exec()

    def _diagnostics_text(self) -> str:
        from playxls.app import diagnostics_report

        sections = [diagnostics_report(self.store).rstrip()]
        path = self.store.playback_diagnostics_path
        if not path.exists():
            sections.append(f"Playback diagnostics tail:\n{path}\n(no records)")
            return "\n\n".join(sections) + "\n"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()[-40:]
        except OSError as exc:
            sections.append(f"Playback diagnostics tail:\n{path}\nread failed: {exc}")
            return "\n\n".join(sections) + "\n"
        body = "\n".join(lines) if lines else "(no records)"
        sections.append(f"Playback diagnostics tail:\n{path}\n{body}")
        return "\n\n".join(sections) + "\n"

    def _open_grid_editor(self) -> None:
        dialog = GridEditorDialog(self.theme, self._current_layout(), self)
        dialog.layout_saved.connect(self._save_custom_layout)
        dialog.exec()

    def _save_custom_layout(self, layout: LayoutDefinition) -> None:
        custom = LayoutDefinition(id=f"custom-{int(time.time() * 1000)}", label=layout.label, tree=layout.tree, custom=True)
        self.layouts.append(custom)
        self.state.layout_id = custom.id
        self.store.save_layouts([layout for layout in self.layouts if layout.custom])
        self._save_session()
        self._toast(f'Saved "{custom.label}"')
        self._sync_ui()

    def _delete_custom_layout(self, layout_id: str) -> None:
        target = next((layout for layout in self.layouts if layout.id == layout_id and layout.custom), None)
        if target is None:
            return
        self.layouts = [layout for layout in self.layouts if layout.id != layout_id]
        if self.state.layout_id == layout_id:
            self.state.layout_id = self.layouts[0].id
        self.store.save_layouts([layout for layout in self.layouts if layout.custom])
        self._save_session()
        self._toast(f'Deleted "{target.label}"')
        self._sync_ui()

    def _settings_changed(self, save_only: bool = False) -> None:
        self.store.save_settings(self.state.settings)
        new_theme = resolve_theme(self.state.settings.theme)
        if new_theme.name != self.theme.name:
            self.theme = new_theme
            self._apply_theme()
        if not save_only:
            self._sync_ui()

    def _bindings_changed(self, bindings) -> None:
        self.state.bindings = list(bindings)
        self.registry = KeyBindingRegistry(self.state.bindings)
        self._register_keybindings()
        self.store.save_bindings(self.state.bindings)
        self._toast("Binding saved")

    def _save_session(self) -> None:
        if self.state.settings.save_playback_position:
            self._capture_playback_positions()
        self.state.main_splitter_sizes = _valid_main_splitter_sizes(self.main_splitter.sizes())
        self.store.save_session(self.state.to_session())

    def _restore_main_splitter_sizes(self) -> None:
        sizes = _valid_main_splitter_sizes(self.state.main_splitter_sizes) or DEFAULT_MAIN_SPLITTER_SIZES
        self.main_splitter.setSizes(sizes)

    def _folders_changed(self) -> None:
        self.store.save_watch_folders(self.state.folders)

    def _add_folder(self, path: str) -> None:
        if self.folder_scanner:
            self.folder_scanner.stop()
        videos = scan_folder(path)
        folder = FolderEntry(id=f"f{len(self.state.folders) + 1}", name=Path(path).name, path=path, count=len(videos), live=True)
        self.state.folders.append(folder)
        existing = {video.path for video in self.state.library_videos if video.path}
        for video in videos:
            if video.path not in existing:
                self.state.library_videos.append(video)
                self.state.ignored_video_paths.discard(video.path)
                existing.add(video.path)
        self.store.save_watch_folders(self.state.folders)
        self.store.save_ignored_video_paths(self.state.ignored_video_paths)
        self.store.save_library_index(_dedupe_videos(self.state.library_videos))
        self._toast(f"Added: {folder.name}")
        self._sync_ui()
        self._start_folder_scanner()

    def _remove_folder(self, folder_id: str) -> None:
        folder = next((item for item in self.state.folders if item.id == folder_id), None)
        if not folder:
            return
        if self.folder_scanner:
            self.folder_scanner.stop()
        removed_video_ids = {
            video.id
            for video in self.state.library_videos
            if video.path and _is_path_inside(video.path, folder.path)
        }
        self.state.folders[:] = [item for item in self.state.folders if item.id != folder_id]
        self.state.library_videos = [video for video in self.state.library_videos if video.id not in removed_video_ids]
        self._clear_video_cells(removed_video_ids)
        self.state.ignored_video_paths = {
            path for path in self.state.ignored_video_paths if not _is_path_inside(path, folder.path)
        }
        self.state.playback_positions = {
            path: position
            for path, position in self.state.playback_positions.items()
            if not _is_path_inside(path, folder.path)
        }
        self.store.save_watch_folders(self.state.folders)
        self.store.save_ignored_video_paths(self.state.ignored_video_paths)
        self.store.save_library_index(_dedupe_videos(self.state.library_videos))
        self._save_session()
        self._toast(f"Removed: {folder.name}")
        self._sync_ui()
        self._start_folder_scanner()

    def _add_video_files(self, paths: list[Path]) -> None:
        existing = {Path(video.path).expanduser() for video in self.state.library_videos if video.path}
        new_videos: list[VideoItem] = []
        for path in paths:
            expanded = path.expanduser()
            if expanded in existing or not expanded.exists() or expanded.suffix.lower() not in VIDEO_EXTENSIONS:
                continue
            self.state.ignored_video_paths.discard(str(expanded))
            new_videos.append(VideoItem.from_path(expanded, index=len(self.state.library_videos) + len(new_videos)))
            existing.add(expanded)
        if not new_videos:
            return
        self.state.library_videos.extend(new_videos)
        self.store.save_ignored_video_paths(self.state.ignored_video_paths)
        visible_cells = count_cells(self._current_layout().tree)
        for video in new_videos:
            target = next((i for i, content in enumerate(self.state.cell_content[:visible_cells]) if content.kind == "empty"), None)
            if target is None:
                break
            self.state.cell_content[target] = CellContent.video(video.id)
        self._save_session()
        self._toast(f"Added: {len(new_videos)}")
        self._sync_ui()

    def _remove_video(self, video_id: str) -> None:
        video = next((item for item in self.state.library_videos if item.id == video_id), None)
        if not video:
            return
        self.state.library_videos = [item for item in self.state.library_videos if item.id != video_id]
        self._clear_video_cells({video_id})
        if video.path:
            source = str(Path(video.path).expanduser())
            self.state.ignored_video_paths.add(source)
            self.state.playback_positions.pop(source, None)
            self.store.save_ignored_video_paths(self.state.ignored_video_paths)
            self.store.save_library_index(_dedupe_videos([*self.state.library_videos, video]))
        self._save_session()
        self._toast(f"Removed: {video.title}")
        self._sync_ui()

    def _start_folder_scanner(self) -> None:
        if self.folder_scanner:
            self.folder_scanner.stop()
        if not self.state.folders:
            self.folder_scanner = None
            return
        seen_paths = [video.path for video in self.state.library_videos if video.path]
        seen_paths.extend(self.state.ignored_video_paths)
        self.folder_scanner = FolderScanner(
            self.state.folders,
            self.folder_video_detected.emit,
            interval_seconds=DEFAULT_SCAN_INTERVAL_SECONDS,
            seen_paths=seen_paths,
            on_refreshed=self.folder_scan_refreshed.emit,
        )
        self.folder_scanner.start()

    def _folder_video_added(self, video: VideoItem) -> None:
        if video.path in self.state.ignored_video_paths:
            return
        self.state.library_videos.append(video)
        self.store.save_library_index(_dedupe_videos(self.state.library_videos))
        self._toast(f"Added: {video.title}")
        self._sync_ui()

    def _folder_scan_refreshed(self, payload: dict[str, object]) -> None:
        self._handle_folder_scan_errors(payload)
        scanned = [video for video in payload.get("videos", []) if isinstance(video, VideoItem)]
        folder_counts = payload.get("folder_counts", {})
        counts = folder_counts if isinstance(folder_counts, dict) else {}
        scanned_folders = [folder for folder in self.state.folders if folder.id in counts]
        old_counts = {folder.id: folder.count for folder in scanned_folders}
        for folder in scanned_folders:
            try:
                folder.count = int(counts.get(folder.id, folder.count))
            except (TypeError, ValueError):
                pass
        scanned_paths = {video.path for video in scanned if video.path}
        old_paths = {video.path for video in self.state.library_videos if video.path}
        new_visible_scanned_paths = {path for path in scanned_paths if path not in self.state.ignored_video_paths}
        counts_changed = any(folder.count != old_counts.get(folder.id, folder.count) for folder in scanned_folders)
        if not counts_changed and old_paths == new_visible_scanned_paths:
            return
        kept = [
            video
            for video in self.state.library_videos
            if not video.path or not any(_path_is_inside_without_resolve(video.path, folder.path) for folder in scanned_folders)
        ]
        indexed = _dedupe_videos([*kept, *scanned])
        visible = [video for video in indexed if not video.path or video.path not in self.state.ignored_video_paths]
        new_paths = {video.path for video in visible if video.path}
        paths_changed = old_paths != new_paths
        if not paths_changed and not counts_changed:
            return
        self.state.library_videos = visible
        _remove_missing_video_cells(self.state)
        self.store.save_watch_folders(self.state.folders)
        if paths_changed:
            self.store.save_library_index(indexed)
            added_count = len(new_paths - old_paths)
            removed_count = len(old_paths - new_paths)
            if added_count and not removed_count:
                self._toast(f"Library refreshed: +{added_count}")
            elif removed_count and not added_count:
                self._toast(f"Library refreshed: -{removed_count}")
            elif added_count or removed_count:
                self._toast("Library refreshed")
            self._sync_ui()
        elif counts_changed:
            self._sync_ui()

    def _handle_folder_scan_errors(self, payload: dict[str, object]) -> None:
        raw_errors = payload.get("folder_errors", {})
        if not isinstance(raw_errors, dict):
            return
        for folder_id, message in raw_errors.items():
            folder = next((item for item in self.state.folders if item.id == str(folder_id)), None)
            if not folder:
                continue
            error_message = str(message).strip() or "Scan failed"
            self.store.append_playback_diagnostic(
                {
                    "kind": "folder_scan_failed",
                    "folder_id": folder.id,
                    "folder_name": folder.name,
                    "path": folder.path,
                    "message": error_message,
                }
            )
            self._toast(f"Folder scan failed: {folder.name}")

    def _clear_video_cells(self, video_ids: set[str]) -> None:
        self.state.cell_content = [
            CellContent.empty() if content.kind == "video" and content.video_id in video_ids else content
            for content in self.state.cell_content
        ]

    def _capture_playback_positions(self) -> None:
        for cell in self.grid.cells:
            video = getattr(cell, "video", None)
            mpv = getattr(cell, "mpv", None)
            source = (getattr(video, "path", "") or getattr(video, "src", "")) if video else ""
            if not source or not mpv:
                continue
            snapshot = mpv.transport_snapshot()
            if snapshot.position and snapshot.position > 1:
                self.state.playback_positions[source] = snapshot.position

    def _unique_browser_id(self, preset: BrowserPreset) -> str:
        stem = preset.id if preset.id != "custom" else "custom"
        existing = {item.id for item in self.state.browser_presets}
        candidate = f"{stem}-{int(time.time() * 1000)}" if stem == "custom" else stem
        suffix = 2
        while candidate in existing:
            candidate = f"{stem}-{suffix}"
            suffix += 1
        return candidate

    def _toast(self, message: str) -> None:
        self.toast.show_message(message)

    def _apply_theme(self) -> None:
        self.setStyleSheet(app_stylesheet(self.theme))
        self.title_bar.setStyleSheet(f"background:{self.theme.title_bar};border-bottom:1px solid {self.theme.border};")
        self.toolbar.setStyleSheet(f"background:{self.theme.bg};border-bottom:1px solid {self.theme.border};")
        self.transport.setStyleSheet(f"background:{self.theme.surface1};border-top:1px solid {self.theme.border};")
        self.stage_shell.setStyleSheet(f"background:{self.theme.bg};")
        self.stage_frame.setStyleSheet(f"background:{self.theme.bg};padding:20px;")
        self.theme_button.setText("☀" if self.state.settings.theme == "dark" else "☾")
        self.play_button.setStyleSheet(f"border-radius:18px;background:{self.theme.text_primary};color:{self.theme.bg};")
        self.sources.set_theme(self.theme)
        self.grid.set_theme(self.theme)
        self.timeline.set_theme(self.theme)
        self.browser_toolbar.setStyleSheet(f"background:{self.theme.surface1};border-bottom:1px solid {self.theme.border};")
        self.browser_cell_label.setStyleSheet(f'font-family:"JetBrains Mono";font-size:11px;color:{self.theme.text_muted};background:transparent;')
        self.browser_notice.setStyleSheet(f'font-family:"JetBrains Mono";font-size:10px;color:{self.theme.danger};background:transparent;')

    def _video_paths_from_mime(self, mime_data) -> list[Path]:
        if not mime_data.hasUrls():
            return []
        paths: list[Path] = []
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.suffix.lower() in VIDEO_EXTENSIONS:
                paths.append(path)
        return paths

    def _event_combo(self, event: QKeyEvent) -> str:
        pieces: list[str] = []
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            pieces.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            pieces.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            pieces.append("Shift")
        key = event.key()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift, Qt.Key.Key_Meta):
            return ""
        key_text = {
            Qt.Key.Key_Space: "Space",
            Qt.Key.Key_Escape: "Esc",
            Qt.Key.Key_Comma: ",",
        }.get(key, event.text().upper() if event.text() else event.keyCombination().key().name)
        pieces.append(key_text)
        return normalize_combo("+".join(pieces))


def build_state(cli_paths: list[str], store: ConfigStore, *, load_watch_folders: bool = True) -> tuple[AppState, list[LayoutDefinition]]:
    state = AppState()
    state.settings = store.load_settings()
    state.bindings = store.load_bindings()
    state.folders = _prune_missing_prototype_folders(store.load_watch_folders()) if load_watch_folders else []
    state.browser_presets = store.load_browser_presets()
    state.ignored_video_paths = store.load_ignored_video_paths()
    layouts = preset_layouts() + store.load_layouts()
    if cli_paths:
        state.library_videos = [VideoItem.from_path(path, index=i) for i, path in enumerate(cli_paths) if Path(path).expanduser().exists()]
        state.cell_content = [CellContent.empty() for _ in range(20)]
        for i, video in enumerate(state.library_videos[:9]):
            state.cell_content[i] = CellContent.video(video.id)
        count = len(state.library_videos)
        state.layout_id = "1x1" if count <= 1 else "1x2" if count == 2 else "1+2" if count == 3 else "2x2" if count <= 4 else "3x3"
    else:
        state.library_videos = _load_watch_folder_videos(
            state.folders,
            store.load_library_index(),
            state.ignored_video_paths,
        )
        state.apply_session(store.load_session())
        _remove_missing_video_cells(state)
    return state, layouts


def _load_watch_folder_videos(
    folders: list[FolderEntry],
    indexed_videos: list[VideoItem],
    ignored_paths: set[str] | None = None,
) -> list[VideoItem]:
    ignored_paths = ignored_paths or set()
    videos: list[VideoItem] = []
    for folder in folders:
        found = [
            video
            for video in indexed_videos
            if video.path and _path_is_inside_without_resolve(video.path, folder.path)
        ]
        folder.count = len(found)
        videos.extend(video for video in found if video.path not in ignored_paths)
    return _dedupe_videos(videos)


def _prune_missing_prototype_folders(folders: list[FolderEntry]) -> list[FolderEntry]:
    prototype_names = {"Animations", "Trailers", "Sci-Fi"}
    return [
        folder
        for folder in folders
        if folder.name not in prototype_names or Path(folder.path).expanduser().exists()
    ]


def _remove_missing_video_cells(state: AppState) -> None:
    valid_video_ids = {video.id for video in state.library_videos}
    state.cell_content = [
        CellContent.empty() if content.kind == "video" and content.video_id not in valid_video_ids else content
        for content in state.cell_content
    ]


def _dedupe_videos(videos: list[VideoItem]) -> list[VideoItem]:
    out: list[VideoItem] = []
    seen: set[str] = set()
    for video in videos:
        key = video.path or video.src or video.id
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(video)
    return out


def _valid_main_splitter_sizes(sizes: list[int]) -> list[int]:
    if len(sizes) != 2:
        return []
    out: list[int] = []
    for size in sizes:
        try:
            value = int(size)
        except (TypeError, ValueError):
            return []
        if value <= 0:
            return []
        out.append(value)
    return out


def _path_is_inside_without_resolve(path: str, folder: str) -> bool:
    try:
        Path(path).expanduser().relative_to(Path(folder).expanduser())
        return True
    except (OSError, ValueError):
        return False


def _is_path_inside(path: str, folder: str) -> bool:
    try:
        Path(path).expanduser().resolve().relative_to(Path(folder).expanduser().resolve())
        return True
    except (OSError, ValueError):
        return False
