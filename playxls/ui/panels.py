from __future__ import annotations

from urllib.parse import urlparse

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from playxls.models import AppSettings, BrowserPreset, CellContent, FolderEntry, VideoItem
from playxls.browser import browser_compatibility_notice
from playxls.preview import PreviewPool
from playxls.theme import Theme
from playxls.ui.widgets import MonoLabel, SegmentedControl, action_button, clear_layout, make_section_label


LIBRARY_PAGE_SIZE = 200


class SourcesPanel(QFrame):
    assign_video = Signal(str, int)
    assign_browser = Signal(object, int)
    add_browser_requested = Signal(object)
    remove_video = Signal(str)
    remove_folder = Signal(str)
    remove_browser = Signal(str)
    folders_changed = Signal()
    add_folder_requested = Signal(str)

    def __init__(self, theme: Theme, parent: QWidget | None = None, preview_pool: PreviewPool | None = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.settings = AppSettings()
        self.preview_pool = preview_pool or PreviewPool(self.settings.preview_cache_size)
        self.videos: list[VideoItem] = []
        self.folders: list[FolderEntry] = []
        self.browser_presets: list[BrowserPreset] = []
        self.cell_content: list[CellContent] = []
        self.cell_count = 1
        self.setMinimumWidth(220)
        self.setMaximumWidth(560)
        self.setStyleSheet(f"background:{theme.surface1};border-right:1px solid {theme.border};")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        root.addWidget(make_section_label("Sources", theme))

        self.switcher = SegmentedControl([("library", "Library"), ("folders", "Folders"), ("browser", "Browser")], "library", theme)
        root.addWidget(self.switcher)
        self.tabs = QStackedWidget()
        self.library = LibraryTab(theme, self.preview_pool)
        self.folders_tab = FoldersTab(theme)
        self.browser = BrowserTab(theme)
        self.tabs.addWidget(self.library)
        self.tabs.addWidget(self.folders_tab)
        self.tabs.addWidget(self.browser)
        root.addWidget(self.tabs, 1)
        self.switcher.changed.connect(self._set_tab)

        self.library.assign_video.connect(self.assign_video.emit)
        self.library.remove_video.connect(self.remove_video.emit)
        self.browser.assign_browser.connect(self.assign_browser.emit)
        self.browser.add_browser_requested.connect(self.add_browser_requested.emit)
        self.browser.remove_browser.connect(self.remove_browser.emit)
        self.folders_tab.folders_changed.connect(self.folders_changed.emit)
        self.folders_tab.add_folder_requested.connect(self.add_folder_requested.emit)
        self.folders_tab.remove_folder.connect(self.remove_folder.emit)

    def _set_tab(self, tab: str) -> None:
        self.tabs.setCurrentIndex({"library": 0, "folders": 1, "browser": 2}.get(tab, 0))

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.setStyleSheet(f"background:{theme.surface1};border-right:1px solid {theme.border};")
        self.library.set_theme(theme)
        self.folders_tab.set_theme(theme)
        self.browser.set_theme(theme)
        self.set_data(self.videos, self.folders, self.browser_presets, self.cell_content, self.cell_count, self.settings)

    def set_data(
        self,
        videos: list[VideoItem],
        folders: list[FolderEntry],
        browser_presets: list[BrowserPreset],
        cell_content: list[CellContent],
        cell_count: int,
        settings: AppSettings,
    ) -> None:
        self.videos = videos
        self.folders = folders
        self.browser_presets = browser_presets
        self.cell_content = cell_content
        self.cell_count = cell_count
        self.settings = settings
        if hasattr(self.preview_pool, "configure"):
            self.preview_pool.configure(settings.preview_cache_size)
        self.library.set_data(videos, cell_content, cell_count, settings)
        self.folders_tab.set_data(folders)
        self.browser.set_data(browser_presets, cell_content, cell_count)

    def shutdown(self) -> None:
        self.preview_pool.stop_all()


class LibraryTab(QWidget):
    assign_video = Signal(str, int)
    remove_video = Signal(str)

    def __init__(self, theme: Theme, preview_pool: PreviewPool | None = None) -> None:
        super().__init__()
        self.theme = theme
        self.preview_pool = preview_pool or PreviewPool()
        self.settings = AppSettings()
        self.videos: list[VideoItem] = []
        self.cell_content: list[CellContent] = []
        self.cell_count = 1
        self.folder_filter = "all"
        self.visible_limit = LIBRARY_PAGE_SIZE
        self.show_more_button: QPushButton | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search library")
        self.search.textChanged.connect(self._search_changed)
        root.addWidget(self.search)
        self.filter_row = QFrame()
        self.filter_layout = QHBoxLayout(self.filter_row)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_layout.setSpacing(4)
        root.addWidget(self.filter_row)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(6)
        self.scroll.setWidget(self.body)
        root.addWidget(self.scroll, 1)

    def set_data(self, videos: list[VideoItem], cell_content: list[CellContent], cell_count: int, settings: AppSettings) -> None:
        self.videos = videos
        self.cell_content = cell_content
        self.cell_count = cell_count
        self.settings = settings
        self._rebuild()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._rebuild()

    def _rebuild(self) -> None:
        if hasattr(self.preview_pool, "configure"):
            self.preview_pool.configure(self.settings.preview_cache_size)
        self._rebuild_filters()
        clear_layout(self.body_layout)
        self.show_more_button = None
        filtered = filter_videos(self.videos, self.search.text(), self.folder_filter)
        visible = filtered[: self.visible_limit]
        for video in visible:
            self.body_layout.addWidget(
                VideoRow(
                    self.theme,
                    video,
                    self.cell_content,
                    self.cell_count,
                    self.assign_video.emit,
                    self.remove_video.emit,
                    preview_pool=self.preview_pool,
                    preview_mode=self.settings.preview_mode,
                    preview_delay_ms=self.settings.preview_delay,
                    preview_muted=self.settings.preview_mute,
                )
            )
        remaining = len(filtered) - len(visible)
        if remaining > 0:
            count = min(LIBRARY_PAGE_SIZE, remaining)
            self.show_more_button = QPushButton(f"Show {count} more")
            self.show_more_button.setToolTip(f"{len(visible)} of {len(filtered)} videos shown")
            self.show_more_button.clicked.connect(self._show_more)
            self.body_layout.addWidget(self.show_more_button)
        self.body_layout.addStretch(1)

    def _rebuild_filters(self) -> None:
        clear_layout(self.filter_layout)
        filters = library_folder_filters(self.videos)
        if self.folder_filter not in filters:
            self.folder_filter = "all"
        for folder in filters:
            label = "All" if folder == "all" else folder
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(folder == self.folder_filter)
            button.clicked.connect(lambda _=False, value=folder: self._set_folder_filter(value))
            self.filter_layout.addWidget(button)
        self.filter_layout.addStretch(1)

    def _set_folder_filter(self, folder: str) -> None:
        self.folder_filter = folder
        self.visible_limit = LIBRARY_PAGE_SIZE
        self._rebuild()

    def _search_changed(self) -> None:
        self.visible_limit = LIBRARY_PAGE_SIZE
        self._rebuild()

    def _show_more(self) -> None:
        self.visible_limit += LIBRARY_PAGE_SIZE
        self._rebuild()


class VideoRow(QFrame):
    def __init__(
        self,
        theme: Theme,
        video: VideoItem,
        cell_content: list[CellContent],
        cell_count: int,
        assign,
        remove,
        *,
        preview_pool: PreviewPool | None = None,
        preview_mode: str = "lazy",
        preview_delay_ms: int = 300,
        preview_muted: bool = True,
    ) -> None:
        super().__init__()
        self.video = video
        self.preview_pool = preview_pool
        self.preview_mode = preview_mode
        self.preview_delay_ms = max(0, int(preview_delay_ms))
        self.preview_muted = preview_muted
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._start_preview)
        self.destroyed.connect(lambda: self._stop_preview())
        self.setStyleSheet(f"QFrame{{background:{theme.surface2};border:1px solid {theme.border};border-radius:6px;}}")
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        row = QHBoxLayout()
        self.thumb = QFrame()
        self.thumb.setFixedSize(48, 32)
        if preview_mode == "lazy":
            self.thumb.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
            self.thumb.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True)
        self.thumb.setStyleSheet(f"background:{theme.cell_bg};border-radius:4px;")
        thumb_layout = QVBoxLayout(self.thumb)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        self.thumb_label = QLabel("▶")
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet(f"background:transparent;color:{theme.text_secondary};")
        thumb_layout.addWidget(self.thumb_label)
        row.addWidget(self.thumb)
        meta = QVBoxLayout()
        title = QLabel(video.title)
        title.setWordWrap(True)
        title.setToolTip(video.title)
        title.setStyleSheet(f"font-weight:600;color:{theme.text_primary};background:transparent;")
        detail = MonoLabel(f"{video.folder} · {video.duration}")
        detail.setStyleSheet(f'font-family:"JetBrains Mono";font-size:10px;color:{theme.text_tertiary};background:transparent;')
        meta.addWidget(title)
        meta.addWidget(detail)
        row.addLayout(meta, 1)
        assigned = [i + 1 for i, content in enumerate(cell_content[:cell_count]) if content.kind == "video" and content.video_id == video.id]
        badges = MonoLabel(" ".join(str(i) for i in assigned))
        badges.setStyleSheet(f'font-family:"JetBrains Mono";font-size:10px;color:{theme.accent};background:transparent;')
        row.addWidget(badges)
        remove_button = small_remove_button(theme, "Remove from library")
        remove_button.clicked.connect(lambda: remove(video.id))
        row.addWidget(remove_button)
        root.addLayout(row)
        root.addWidget(cell_picker(cell_count, lambda index: assign(video.id, index), theme, disabled_numbers=set(assigned)))

    def enterEvent(self, event) -> None:  # type: ignore[override]
        if self.preview_mode == "lazy" and self.preview_source:
            self.preview_timer.start(self.preview_delay_ms)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._stop_preview()
        super().leaveEvent(event)

    @property
    def preview_source(self) -> str:
        return self.video.path or self.video.src

    def _start_preview(self) -> None:
        if self.preview_mode != "lazy" or not self.preview_pool or not self.preview_source:
            return
        controller = self.preview_pool.start(
            self.preview_source,
            window_id=int(self.thumb.winId()),
            muted=self.preview_muted,
        )
        if controller:
            self.thumb_label.setVisible(False)

    def _stop_preview(self) -> None:
        self.preview_timer.stop()
        if self.preview_mode == "lazy" and self.preview_pool and self.preview_source:
            self.preview_pool.pause(self.preview_source)
        self.thumb_label.setVisible(True)


class FoldersTab(QWidget):
    folders_changed = Signal()
    add_folder_requested = Signal(str)
    remove_folder = Signal(str)

    def __init__(self, theme: Theme) -> None:
        super().__init__()
        self.theme = theme
        self.folders: list[FolderEntry] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(8)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(6)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.body)
        root.addWidget(scroll, 1)
        root.addWidget(action_button("+ Add folder", self._choose_folder, theme, primary=True))

    def set_data(self, folders: list[FolderEntry]) -> None:
        self.folders = folders
        self._rebuild()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._rebuild()

    def _rebuild(self) -> None:
        clear_layout(self.body_layout)
        for folder in self.folders:
            row = QFrame()
            row.setStyleSheet(f"QFrame{{background:{self.theme.surface2};border:1px solid {self.theme.border};border-radius:6px;}}")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(8, 8, 8, 8)
            label = QLabel(f"{folder.name}\n{folder.path}\n{folder.count} files")
            label.setStyleSheet(f"background:transparent;color:{self.theme.text_secondary};")
            layout.addWidget(label, 1)
            live = QPushButton("live" if folder.live else "paused")
            live.setCheckable(True)
            live.setChecked(folder.live)
            live.clicked.connect(lambda _=False, f=folder: self._toggle(f))
            layout.addWidget(live)
            remove = small_remove_button(self.theme, "Remove watched folder")
            remove.clicked.connect(lambda _=False, folder_id=folder.id: self.remove_folder.emit(folder_id))
            layout.addWidget(remove)
            self.body_layout.addWidget(row)
        self.body_layout.addStretch(1)

    def _toggle(self, folder: FolderEntry) -> None:
        folder.live = not folder.live
        self.folders_changed.emit()
        self._rebuild()

    def _choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Add watched folder")
        if path:
            self.add_folder_requested.emit(path)


class BrowserTab(QWidget):
    assign_browser = Signal(object, int)
    add_browser_requested = Signal(object)
    remove_browser = Signal(str)

    def __init__(self, theme: Theme) -> None:
        super().__init__()
        self.theme = theme
        self.presets: list[BrowserPreset] = []
        self.cell_content: list[CellContent] = []
        self.cell_count = 1
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(8)
        url_row = QHBoxLayout()
        self.url = QLineEdit()
        self.url.setPlaceholderText("example.com")
        add = QPushButton("+")
        add.clicked.connect(self._custom_url)
        url_row.addWidget(self.url, 1)
        url_row.addWidget(add)
        root.addLayout(url_row)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(6)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.body)
        root.addWidget(scroll, 1)

    def set_data(self, presets: list[BrowserPreset], cell_content: list[CellContent], cell_count: int) -> None:
        self.presets = presets
        self.cell_content = cell_content
        self.cell_count = cell_count
        self._rebuild()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._rebuild()

    def _rebuild(self) -> None:
        clear_layout(self.body_layout)
        for preset in self.presets:
            self.body_layout.addWidget(BrowserRow(self.theme, preset, self.cell_content, self.cell_count, self.assign_browser.emit, self.remove_browser.emit))
        self.body_layout.addStretch(1)

    def _custom_url(self) -> None:
        raw = self.url.text().strip()
        if not raw:
            return
        url = raw if "://" in raw else f"https://{raw}"
        host = urlparse(url).netloc or url
        self.add_browser_requested.emit(BrowserPreset("custom", host, url, "#fbbf24"))
        self.url.clear()


class BrowserRow(QFrame):
    def __init__(self, theme: Theme, preset: BrowserPreset, cell_content: list[CellContent], cell_count: int, assign, remove) -> None:
        super().__init__()
        self.compatibility_notice = QLabel("")
        self.setStyleSheet(f"QFrame{{background:{theme.surface2};border:1px solid {theme.border};border-radius:6px;}}")
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        head = QHBoxLayout()
        tile = QLabel(preset.name[:2].upper())
        tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile.setFixedSize(32, 32)
        tile.setStyleSheet(f"background:{preset.color};color:white;border-radius:5px;font-weight:700;")
        head.addWidget(tile)
        meta = QLabel(f"{preset.name}\n{preset.url}")
        meta.setStyleSheet(f"background:transparent;color:{theme.text_secondary};")
        head.addWidget(meta, 1)
        remove_button = small_remove_button(theme, "Remove browser source")
        remove_button.clicked.connect(lambda: remove(preset.id))
        head.addWidget(remove_button)
        root.addLayout(head)
        notice = browser_compatibility_notice(preset.url)
        if notice:
            self.compatibility_notice.setText(notice.label)
            self.compatibility_notice.setToolTip(notice.detail)
            self.compatibility_notice.setStyleSheet(f'font-family:"JetBrains Mono";font-size:10px;color:{theme.danger};background:transparent;')
            root.addWidget(self.compatibility_notice)
        else:
            self.compatibility_notice.hide()
        root.addWidget(cell_picker(cell_count, lambda index: assign(preset, index), theme))


def cell_picker(cell_count: int, assign, theme: Theme, disabled_numbers: set[int] | None = None) -> QWidget:
    disabled_numbers = disabled_numbers or set()
    container = QWidget()
    container.setStyleSheet("background:transparent;")
    layout = QGridLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(6)
    layout.setVerticalSpacing(4)
    for index in range(cell_count):
        button = QPushButton(str(index + 1))
        button.setFixedSize(28, 24)
        button.setEnabled(index + 1 not in disabled_numbers)
        button.clicked.connect(lambda _=False, idx=index: assign(idx))
        layout.addWidget(button, index // 5, index % 5)
    columns = min(5, max(1, cell_count))
    rows = max(1, (cell_count + 4) // 5)
    container.setFixedSize(columns * 34 - 6, rows * 28)
    return container


def small_remove_button(theme: Theme, tooltip: str) -> QPushButton:
    button = QPushButton("×")
    button.setFixedSize(22, 22)
    button.setToolTip(tooltip)
    button.setStyleSheet(
        f"background:{theme.surface3};color:{theme.text_secondary};border:1px solid {theme.border};"
        "border-radius:4px;padding:0;font-weight:700;"
    )
    return button


def library_folder_filters(videos: list[VideoItem]) -> list[str]:
    return ["all", *sorted({video.folder for video in videos if video.folder})]


def filter_videos(videos: list[VideoItem], query: str, folder: str) -> list[VideoItem]:
    normalized_query = query.casefold().strip()
    out: list[VideoItem] = []
    for video in videos:
        if folder != "all" and video.folder != folder:
            continue
        if normalized_query and normalized_query not in video.title.casefold() and normalized_query not in video.folder.casefold():
            continue
        out.append(video)
    return out
