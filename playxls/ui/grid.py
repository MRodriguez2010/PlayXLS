from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QMenu, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from shiboken6 import delete as delete_qobject, isValid as is_valid_qobject

from playxls.layout import CellRect, LayoutDefinition, collect_cells
from playxls.browser import BrowserFullscreenBridge, browser_profile_paths, normalize_browser_url
from playxls.models import AppSettings, CellContent, VideoItem
from playxls.theme import Theme
from playxls.ui.widgets import MonoLabel, animate_geometry
from playxls.video import MpvController

try:
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - depends on optional QtWebEngine wheel.
    QWebEnginePage = None
    QWebEngineProfile = None
    QWebEngineView = None


_SHARED_BROWSER_PROFILES = {}


class GridStage(QFrame):
    hovered_changed = Signal(object)
    fullscreen_changed = Signal(object)
    cell_cleared = Signal(int)
    browser_url_changed = Signal(int, str)

    def __init__(self, theme: Theme, cache_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.cache_dir = cache_dir
        self.layout_def: LayoutDefinition | None = None
        self.settings = AppSettings()
        self.playback_positions: dict[str, float] = {}
        self.cell_content: list[CellContent] = []
        self.videos: list[VideoItem] = []
        self.cells: list[CellWidget] = []
        self.hovered_cell: int | None = None
        self.fullscreen_cell: int | None = None
        self.show_borders = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setStyleSheet(f"background:{theme.bg};")

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.setStyleSheet(f"background:{theme.bg};")
        for cell in self.cells:
            cell.set_theme(theme)
        self.reposition()

    def set_data(
        self,
        layout_def: LayoutDefinition,
        cell_content: list[CellContent],
        videos: list[VideoItem],
        settings: AppSettings,
        show_borders: bool,
        playback_positions: dict[str, float] | None = None,
    ) -> None:
        self.layout_def = layout_def
        self.cell_content = cell_content
        self.videos = videos
        self.settings = settings
        self.playback_positions = playback_positions or {}
        self.show_borders = show_borders
        rects = collect_cells(layout_def.tree)
        while len(self.cells) < len(rects):
            index = len(self.cells)
            cell = CellWidget(index, self.theme, self.cache_dir, self)
            cell.hovered.connect(self._set_hovered)
            cell.unhovered.connect(lambda idx=index: self._clear_hovered(idx))
            cell.fullscreen_requested.connect(self.toggle_fullscreen)
            cell.clear_requested.connect(self._clear_cell)
            cell.browser_url_changed.connect(self.browser_url_changed.emit)
            self.cells.append(cell)
        for index, cell in enumerate(self.cells):
            cell.setVisible(index < len(rects))
            if index < len(rects):
                content = cell_content[index] if index < len(cell_content) else CellContent.empty()
                cell.set_content(content, self._video_for(content), settings, self.playback_positions)
                cell.set_border_visible(show_borders)
                cell.set_fullscreen(index == self.fullscreen_cell)
        self.reposition(animated=self.isVisible() and self.width() > 200 and self.height() > 200)
        QTimer.singleShot(0, lambda: self.reposition(animated=False))

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.reposition(animated=False)

    def reposition(self, animated: bool = True) -> None:
        if not self.layout_def:
            return
        rects = collect_cells(self.layout_def.tree)
        for index, cell in enumerate(self.cells[: len(rects)]):
            target = self._target_rect(index, rects[index])
            if animated:
                animate_geometry(cell, target)
            else:
                cell.setGeometry(target)
            cell.raise_()
        if self.fullscreen_cell is not None and self.fullscreen_cell < len(self.cells):
            self.cells[self.fullscreen_cell].raise_()

    def toggle_fullscreen(self, index: int | None = None) -> None:
        if index is None:
            index = self.hovered_cell
        if index is None:
            return
        self.fullscreen_cell = None if self.fullscreen_cell == index else index
        for i, cell in enumerate(self.cells):
            cell.set_fullscreen(i == self.fullscreen_cell)
            cell.setEnabled(self.fullscreen_cell is None or i == self.fullscreen_cell)
            cell.setVisible(self.fullscreen_cell is None or i == self.fullscreen_cell)
        self.fullscreen_changed.emit(self.fullscreen_cell)
        self.reposition()

    def set_playing(self, playing: bool) -> None:
        for cell in self.cells:
            cell.set_playing(playing)

    def set_volume_state(self, master: float, muted: bool) -> None:
        for index, cell in enumerate(self.cells):
            volume = 0.0 if muted else self._effective_volume(index, master)
            cell.set_volume(volume)

    def shutdown(self) -> None:
        for cell in self.cells:
            cell._clear_body()

    def _target_rect(self, index: int, cell: CellRect) -> QRect:
        if self.fullscreen_cell == index:
            return self.rect()
        gap_x = self.width() * 0.004 if self.show_borders else 0
        gap_y = self.height() * 0.004 if self.show_borders else 0
        x = int(self.width() * cell.x / 100 + gap_x)
        y = int(self.height() * cell.y / 100 + gap_y)
        w = int(self.width() * cell.w / 100 - gap_x * 2)
        h = int(self.height() * cell.h / 100 - gap_y * 2)
        rect = QRect(x, y, max(20, w), max(20, h))
        if self.fullscreen_cell is None and self.hovered_cell == index and self.settings.expand_on_hover:
            scale = self.settings.expand_percent / 100
            grown_w = int(rect.width() * scale)
            grown_h = int(rect.height() * scale)
            dx = self._anchor_offset(cell.x, cell.w, rect.width(), grown_w)
            dy = self._anchor_offset(cell.y, cell.h, rect.height(), grown_h)
            rect = QRect(rect.x() + dx, rect.y() + dy, grown_w, grown_h)
        return rect

    def _anchor_offset(self, start_percent: float, size_percent: float, old: int, new: int) -> int:
        center = start_percent + size_percent / 2
        diff = old - new
        if center < 33:
            return 0
        if center > 66:
            return diff
        return diff // 2

    def _set_hovered(self, index: int) -> None:
        if self.fullscreen_cell is not None:
            return
        self.hovered_cell = index
        for i, cell in enumerate(self.cells):
            cell.set_dimmed(i != index and self.settings.expand_on_hover)
            cell.set_hovered(i == index)
        self.hovered_changed.emit(index)
        self.reposition()

    def _clear_hovered(self, index: int) -> None:
        if self.hovered_cell != index:
            return
        self.hovered_cell = None
        for cell in self.cells:
            cell.set_dimmed(False)
            cell.set_hovered(False)
        self.hovered_changed.emit(None)
        self.reposition()

    def _clear_cell(self, index: int) -> None:
        self.cell_cleared.emit(index)

    def _video_for(self, content: CellContent) -> VideoItem | None:
        if content.kind != "video" or not content.video_id:
            return None
        return next((video for video in self.videos if video.id == content.video_id), None)

    def _effective_volume(self, index: int, master: float) -> float:
        if not self.settings.volume_on_hover or self.hovered_cell is None:
            return master
        delta = self.settings.hover_volume_amount / 100
        if self.settings.hover_volume_mode == "boost":
            return max(0.0, min(1.0, master + delta if index == self.hovered_cell else master - delta))
        return max(0.0, min(1.0, master - delta if index == self.hovered_cell else master))


class CellWidget(QFrame):
    hovered = Signal(int)
    unhovered = Signal(int)
    fullscreen_requested = Signal(int)
    clear_requested = Signal(int)
    browser_url_changed = Signal(int, str)
    mpv_factory = MpvController

    def __init__(self, index: int, theme: Theme, cache_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.index = index
        self.theme = theme
        self.cache_dir = cache_dir
        self.content = CellContent.empty()
        self.video: VideoItem | None = None
        self.mpv: MpvController | None = None
        self.web_view = None
        self.browser_profile = None
        self.browser_profile_owned = False
        self.browser_profile_scope: str | None = None
        self.browser_page = None
        self.browser_placeholder: QLabel | None = None
        self.browser_page_fullscreen = False
        self.is_fullscreen = False
        self.browser_fullscreen_bridge = BrowserFullscreenBridge(self._browser_fullscreen_requested)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)
        self.badge = MonoLabel(str(index + 1), self)
        self.badge.setFixedHeight(20)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.move(8, 8)
        self.fullscreen_button = QPushButton("□", self)
        self.fullscreen_button.setFixedSize(28, 28)
        self.fullscreen_button.clicked.connect(lambda: self.fullscreen_requested.emit(self.index))
        self.overlay = QLabel("", self)
        self.overlay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self.overlay.setWordWrap(True)
        self.overlay.setStyleSheet("background:rgba(0,0,0,0.55);color:white;padding:8px;")
        self.set_theme(theme)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.setStyleSheet(f"QFrame{{background:{theme.cell_bg};border-radius:6px;border:1px solid {theme.border};}}")
        self.badge.setStyleSheet(
            f'font-family:"JetBrains Mono";font-size:11px;border-radius:4px;'
            f"background:rgba(0,0,0,0.60);color:{theme.text_primary};padding:2px 7px;"
        )
        self.fullscreen_button.setStyleSheet(f"background:{theme.surface2};color:{theme.text_primary};border-radius:5px;")

    def set_content(
        self,
        content: CellContent,
        video: VideoItem | None,
        settings: AppSettings,
        playback_positions: dict[str, float] | None = None,
    ) -> None:
        profile_scope_changed = content.kind == "browser" and self.browser_profile_scope != settings.browser_profile_scope
        if content.to_dict() == self.content.to_dict() and self.video == video and not profile_scope_changed:
            return
        self._clear_body()
        self.content = content
        self.video = video
        self.browser_profile_scope = settings.browser_profile_scope if content.kind == "browser" else None
        if content.kind == "video" and video:
            self._set_video(video, settings, playback_positions or {})
        elif content.kind == "browser" and content.url:
            self._set_browser(content, settings)
        else:
            self._set_empty()
        self._position_overlays()

    def set_border_visible(self, visible: bool) -> None:
        border = self.theme.border if visible else self.theme.cell_bg
        self.setStyleSheet(f"QFrame{{background:{self.theme.cell_bg};border-radius:6px;border:1px solid {border};}}")

    def set_fullscreen(self, active: bool) -> None:
        self.is_fullscreen = active
        self.badge.setStyleSheet(
            f'font-family:"JetBrains Mono";font-size:11px;border-radius:4px;'
            f"background:{self.theme.danger if active else 'rgba(0,0,0,0.60)'};"
            f"color:{'#ffffff' if active else self.theme.text_primary};padding:2px 7px;"
        )
        self.fullscreen_button.setText("×" if active else "□")

    def set_hovered(self, active: bool) -> None:
        if active:
            self.badge.setStyleSheet(
                f'font-family:"JetBrains Mono";font-size:11px;border-radius:4px;'
                f"background:{self.theme.accent};color:{self.theme.on_accent};padding:2px 7px;"
            )
        elif self.badge.styleSheet().find(self.theme.danger) == -1:
            self.set_fullscreen(False)
        self.fullscreen_button.setVisible(active)
        self.overlay.setVisible(active and self.content.kind == "video")

    def set_dimmed(self, dimmed: bool) -> None:
        self.setWindowOpacity(0.55 if dimmed else 1.0)

    def set_playing(self, playing: bool) -> None:
        if self.mpv:
            self.mpv.set_pause(not playing)

    def set_volume(self, volume: float) -> None:
        if self.mpv:
            self.mpv.set_volume(volume)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._position_overlays()

    def _position_overlays(self) -> None:
        self.badge.adjustSize()
        self.badge.move(8, 8)
        self.fullscreen_button.move(self.width() - 36, 8)
        self.overlay.setGeometry(0, max(0, self.height() - 62), self.width(), 62)
        self._layout_browser_widgets()

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self.hovered.emit(self.index)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self.unhovered.emit(self.index)
        super().leaveEvent(event)

    def _set_empty(self) -> None:
        label = QLabel("Empty cell")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"background:transparent;color:{self.theme.text_muted};")
        self.root.addWidget(label, 1)
        self.overlay.setText("")

    def _set_video(self, video: VideoItem, settings: AppSettings, playback_positions: dict[str, float]) -> None:
        surface = QFrame()
        surface.setStyleSheet("background:#000000;")
        self.root.addWidget(surface, 1)
        source = video.path or video.src
        surface.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        surface.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True)
        source_key = video.path or video.src
        self.mpv = type(self).mpv_factory(window_id=int(surface.winId()))
        if source and self.mpv.available:
            self.mpv.load(source, paused=False, loop=False, volume=60)
            if settings.save_playback_position:
                resume_position = playback_positions.get(source_key, 0.0)
                if resume_position > 1:
                    self.mpv.seek_absolute(resume_position)
        else:
            label = QLabel("mpv unavailable\n" + source)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(f"background:#000;color:{self.theme.text_secondary};")
            QVBoxLayout(surface).addWidget(label)
        self.overlay.setText(f"{video.title}\n{video.folder} · {video.duration}")

    def _set_browser(self, content: CellContent, settings: AppSettings) -> None:
        if QWebEngineView and QWebEngineProfile and QWebEnginePage:
            profile, owned = self._browser_profile(settings)
            view = QWebEngineView(self)
            page = QWebEnginePage(profile, view)
            self.web_view = view
            self.browser_profile = profile
            self.browser_profile_owned = owned
            self.browser_page = page
            view.setPage(page)
            page.settings().setAttribute(page.settings().WebAttribute.FullScreenSupportEnabled, True)
            page.fullScreenRequested.connect(self.browser_fullscreen_bridge.handle)
            page.urlChanged.connect(lambda url: self.browser_url_changed.emit(self.index, url.toString()))
            view.setUrl(QUrl(normalize_browser_url(content.url)))
            view.show()
            self._layout_browser_widgets()
        else:
            label = QLabel(f"QtWebEngine not installed\n{content.url}", self)
            self.browser_placeholder = label
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(f"background:{self.theme.cell_empty};color:{self.theme.text_secondary};")
            label.show()
            self._layout_browser_widgets()

    def _layout_browser_widgets(self) -> None:
        if self.web_view:
            self.web_view.setGeometry(0, 0, self.width(), self.height())
        if self.browser_placeholder:
            self.browser_placeholder.setGeometry(0, 0, self.width(), self.height())

    def _browser_profile(self, settings: AppSettings):
        profile_paths = browser_profile_paths(self.cache_dir, self.index + 1, profile_scope=settings.browser_profile_scope)
        profile_paths.storage_path.mkdir(parents=True, exist_ok=True)
        profile_paths.cache_path.mkdir(parents=True, exist_ok=True)
        if settings.browser_profile_scope != "per_cell":
            key = (profile_paths.profile_name, str(profile_paths.storage_path), str(profile_paths.cache_path))
            profile = _SHARED_BROWSER_PROFILES.get(key)
            if profile is None or not is_valid_qobject(profile):
                profile = self._new_browser_profile(profile_paths, QApplication.instance() or self)
                _SHARED_BROWSER_PROFILES[key] = profile
            return profile, False
        return self._new_browser_profile(profile_paths, self), True

    def _new_browser_profile(self, profile_paths, parent):
        profile = QWebEngineProfile(profile_paths.profile_name, parent)
        profile.setPersistentStoragePath(str(profile_paths.storage_path))
        profile.setCachePath(str(profile_paths.cache_path))
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        return profile

    def _clear_body(self) -> None:
        if self.mpv:
            self.mpv.stop()
            self.mpv = None
        if self.browser_page is not None and is_valid_qobject(self.browser_page):
            delete_qobject(self.browser_page)
        self.browser_page = None
        if self.web_view is not None and is_valid_qobject(self.web_view):
            delete_qobject(self.web_view)
        self.web_view = None
        if self.browser_placeholder is not None and is_valid_qobject(self.browser_placeholder):
            delete_qobject(self.browser_placeholder)
        self.browser_placeholder = None
        if self.browser_profile_owned and self.browser_profile is not None and is_valid_qobject(self.browser_profile):
            delete_qobject(self.browser_profile)
        self.browser_profile = None
        self.browser_profile_owned = False
        while self.root.count():
            item = self.root.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.browser_page_fullscreen = False
        self.browser_profile_scope = None

    def _context_menu(self, point: QPoint) -> None:
        menu = QMenu(self)
        title = QAction(f"Cell {self.index + 1}", self)
        title.setEnabled(False)
        menu.addAction(title)
        fullscreen = menu.addAction("Fullscreen\tF")
        clear = menu.addAction("Clear cell")
        action = menu.exec(self.mapToGlobal(point))
        if action == fullscreen:
            self.fullscreen_requested.emit(self.index)
        elif action == clear:
            self.clear_requested.emit(self.index)

    def _browser_fullscreen_requested(self, active: bool) -> None:
        self.browser_page_fullscreen = active
        self._layout_browser_widgets()
        self._position_overlays()
