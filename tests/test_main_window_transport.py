import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PySide6.QtWidgets import QApplication

from playxls.config import ConfigStore
from playxls.layout import preset_layouts
from playxls.models import AppState, BrowserPreset, CellContent, FolderEntry, VideoItem
from playxls.ui.main_window import MainWindow


def test_main_window_prefers_fullscreen_then_hovered_video_cell_for_transport(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    window = MainWindow(state, preset_layouts(), store)

    window.grid.cells = [
        _Cell(kind="browser"),
        _Cell(kind="video", mpv=object()),
        _Cell(kind="video", mpv=object()),
    ]
    window.grid.fullscreen_cell = 2
    window.hovered_cell = 1

    assert window._transport_cell() is window.grid.cells[2]

    window.grid.fullscreen_cell = None

    assert window._transport_cell() is window.grid.cells[1]
    window.grid.cells = []
    window.close()


def test_main_window_uses_logo_icon_in_shell(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()

    window = MainWindow(state, preset_layouts(), store)

    assert not window.windowIcon().isNull()
    assert window.logo_label.pixmap() is not None
    assert not window.logo_label.pixmap().isNull()
    window.close()


def test_main_window_uses_splitter_for_resizable_sources_panel(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    window = MainWindow(AppState(), preset_layouts(), store)

    assert window.main_splitter.widget(0) is window.sources
    assert window.sources.minimumWidth() <= 220
    assert window.sources.maximumWidth() >= 520
    window.close()


def test_remove_video_from_library_clears_cells_and_persists_ignore(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    video_path = tmp_path / "one.mp4"
    video_path.write_bytes(b"fake")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    video = VideoItem.from_path(video_path)
    state.library_videos = [video]
    state.cell_content[0] = CellContent.video(video.id)
    window = MainWindow(state, preset_layouts(), store)

    window._remove_video(video.id)

    assert state.library_videos == []
    assert state.cell_content[0] == CellContent.empty()
    assert str(video_path) in state.ignored_video_paths
    assert store.load_ignored_video_paths() == {str(video_path)}
    window.close()


def test_remove_folder_removes_folder_videos_and_clears_cells(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    folder_path = tmp_path / "Watch Me"
    folder_path.mkdir()
    video_path = folder_path / "one.mp4"
    video_path.write_bytes(b"fake")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.folders = [FolderEntry(id="f1", name="Watch Me", path=str(folder_path), count=1)]
    video = VideoItem.from_path(video_path)
    state.library_videos = [video]
    state.cell_content[0] = CellContent.video(video.id)
    window = MainWindow(state, preset_layouts(), store)

    window._remove_folder("f1")

    assert state.folders == []
    assert state.library_videos == []
    assert state.cell_content[0] == CellContent.empty()
    assert store.load_watch_folders() == []
    window.close()


def test_remove_browser_preset_clears_matching_cells_and_persists(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    preset = BrowserPreset(id="ex", name="Example", url="https://example.com", color="#fbbf24")
    state.browser_presets = [preset]
    state.cell_content[0] = CellContent.browser(preset.url, preset.name)
    window = MainWindow(state, preset_layouts(), store)

    window._remove_browser_preset(preset.id)

    assert state.browser_presets == []
    assert state.cell_content[0] == CellContent.empty()
    assert store.load_browser_presets() == []
    window.close()


def test_browser_toolbar_controls_active_browser_cell_outside_grid(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    window = MainWindow(AppState(), preset_layouts(), store)
    first = _Cell(kind="browser", index=0, web_view=_WebView("https://example.com"))
    second = _Cell(kind="browser", index=1, web_view=_WebView("https://youtube.com"))
    window.grid.cells = [first, second]

    window._hovered_changed(1)

    assert window.browser_toolbar.isHidden() is False
    assert window.browser_cell_label.text() == "Cell 2"
    assert window.browser_url.text() == "https://youtube.com"

    window.browser_url.setText("example.org/watch")
    window._browser_go()
    window._browser_action("back")
    window._browser_action("forward")
    window._browser_action("reload")

    assert second.web_view.last_url == "https://example.org/watch"
    assert second.web_view.actions == ["back", "forward", "reload"]
    window.grid.cells = []
    window.close()


def test_browser_toolbar_hides_without_browser_cells(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    window = MainWindow(AppState(), preset_layouts(), store)
    window.grid.cells = [_Cell(kind="video", index=0, mpv=object())]

    window._sync_browser_toolbar()

    assert window.browser_toolbar.isHidden() is True
    window.grid.cells = []
    window.close()


def test_browser_toolbar_shows_limited_notice_for_drm_browser_cell(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    window = MainWindow(AppState(), preset_layouts(), store)
    window.grid.cells = [_Cell(kind="browser", index=0, web_view=_WebView("https://netflix.com"), url="https://netflix.com")]

    window._sync_browser_toolbar()

    assert window.browser_notice.isHidden() is False
    assert "DRM" in window.browser_notice.text()
    window.grid.cells = []
    window.close()


def test_browser_toolbar_hides_limited_notice_for_standard_browser_cell(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    window = MainWindow(AppState(), preset_layouts(), store)
    window.grid.cells = [_Cell(kind="browser", index=0, web_view=_WebView("https://youtube.com"), url="https://youtube.com")]

    window._sync_browser_toolbar()

    assert window.browser_notice.isHidden() is True
    window.grid.cells = []
    window.close()


def test_browser_toolbar_opens_active_browser_cell_in_system_browser(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    window = MainWindow(AppState(), preset_layouts(), store)
    opened = []
    window.open_external_url = lambda url: opened.append(url.toString())
    window.grid.cells = [_Cell(kind="browser", index=0, web_view=_WebView("netflix.com"), url="https://netflix.com")]

    window._sync_browser_toolbar()
    window._browser_open_external()

    assert window.browser_external.isEnabled() is True
    assert opened == ["https://netflix.com"]
    window.grid.cells = []
    window.close()


def test_browser_toolbar_prefers_load_failure_notice_for_active_cell(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    window = MainWindow(AppState(), preset_layouts(), store)
    window.grid.cells = [_Cell(kind="browser", index=0, web_view=_WebView("https://netflix.com"), url="https://netflix.com")]

    assert callable(getattr(window, "_browser_load_failed", None))
    window._browser_load_failed(0, "Load failed")

    assert window.browser_notice.isHidden() is False
    assert window.browser_notice.text() == "Load failed"
    assert "system browser" in window.browser_notice.toolTip()
    window.grid.cells = []
    window.close()


def test_browser_toolbar_clears_load_failure_after_successful_cell_load(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    window = MainWindow(AppState(), preset_layouts(), store)
    window.grid.cells = [_Cell(kind="browser", index=0, web_view=_WebView("https://example.com"), url="https://example.com")]

    window._browser_load_failed(0, "Load failed")
    assert callable(getattr(window, "_browser_load_succeeded", None))
    window._browser_load_succeeded(0)

    assert window.browser_notice.isHidden() is True
    window.grid.cells = []
    window.close()


class _Content:
    def __init__(self, kind: str, url: str = "") -> None:
        self.kind = kind
        self.url = url


class _Cell:
    def __init__(self, *, kind: str, index: int = 0, mpv=None, web_view=None, url: str = "") -> None:
        self.index = index
        self.content = _Content(kind, url)
        self.mpv = mpv
        self.web_view = web_view

    def isVisible(self) -> bool:
        return True

    def set_volume(self, volume: float) -> None:
        self.volume = volume

    def _clear_body(self) -> None:
        pass


class _Url:
    def __init__(self, value: str) -> None:
        self.value = value

    def toString(self) -> str:
        return self.value


class _WebView:
    def __init__(self, url: str) -> None:
        self._url = url
        self.last_url = ""
        self.actions: list[str] = []

    def url(self) -> _Url:
        return _Url(self._url)

    def setUrl(self, url) -> None:
        self.last_url = url.toString()
        self._url = self.last_url

    def back(self) -> None:
        self.actions.append("back")

    def forward(self) -> None:
        self.actions.append("forward")

    def reload(self) -> None:
        self.actions.append("reload")
