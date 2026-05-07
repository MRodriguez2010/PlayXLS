import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication

from playxls.config import ConfigStore
from playxls.layout import LayoutDefinition, LayoutNode, preset_layouts
from playxls.models import AppState, BrowserPreset, CellContent, FolderEntry, VideoItem
from playxls.transport import TransportSnapshot
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


def test_main_window_diagnostics_text_includes_playback_log_tail(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    store.append_playback_diagnostic({"kind": "video_load_failed", "message": "BadWindow invalid Window parameter"})
    window = MainWindow(AppState(), preset_layouts(), store)

    text = window._diagnostics_text()

    assert "PlayXLS" in text
    assert "libmpv:" in text
    assert "Playback diagnostics tail" in text
    assert "BadWindow invalid Window parameter" in text
    window.close()


def test_main_window_uses_splitter_for_resizable_sources_panel(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    window = MainWindow(AppState(), preset_layouts(), store)

    assert window.main_splitter.widget(0) is window.sources
    assert window.sources.minimumWidth() <= 220
    assert window.sources.maximumWidth() >= 520
    window.close()


def test_main_window_restores_saved_sources_splitter_width(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.main_splitter_sizes = [260, 1020]

    window = MainWindow(state, preset_layouts(), store)
    window.show()
    app.processEvents()

    assert window.main_splitter.sizes()[0] == 260
    window.close()


def test_main_window_saves_current_sources_splitter_width(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    window = MainWindow(state, preset_layouts(), store)
    window.show()
    app.processEvents()
    window.main_splitter.setSizes([240, 1040])
    app.processEvents()
    expected_sizes = window.main_splitter.sizes()

    window._save_session()

    assert expected_sizes[0] == 240
    assert state.main_splitter_sizes == expected_sizes
    assert store.load_session().main_splitter_sizes == expected_sizes
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


def test_main_window_seeds_folder_scanner_from_loaded_library(monkeypatch, tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    calls = []

    class FakeScanner:
        def __init__(self, folders, on_added, interval_seconds, seen_paths=None, on_refreshed=None) -> None:
            calls.append(
                {
                    "folders": folders,
                    "interval_seconds": interval_seconds,
                    "seen_paths": list(seen_paths or []),
                    "on_refreshed": on_refreshed,
                }
            )

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

    monkeypatch.setattr("playxls.ui.main_window.FolderScanner", FakeScanner)
    video_path = tmp_path / "one.mp4"
    ignored_path = tmp_path / "ignored.mp4"
    video_path.write_bytes(b"fake")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.folders = [FolderEntry(id="f1", name="NAS", path=str(tmp_path), count=1, live=True)]
    state.library_videos = [VideoItem.from_path(video_path)]
    state.ignored_video_paths = {str(ignored_path)}

    window = MainWindow(state, preset_layouts(), store)

    assert calls[0]["interval_seconds"] == 30.0
    assert calls[0]["seen_paths"] == [str(video_path), str(ignored_path)]
    assert calls[0]["on_refreshed"] is not None
    window.close()


def test_main_window_seeds_uncached_folder_scanner_without_prime(monkeypatch, tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    calls = []

    class FakeScanner:
        def __init__(self, folders, on_added, interval_seconds, seen_paths=None, on_refreshed=None) -> None:
            calls.append(list(seen_paths or []))

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

    monkeypatch.setattr("playxls.ui.main_window.FolderScanner", FakeScanner)
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.folders = [FolderEntry(id="f1", name="NAS", path=str(tmp_path), count=0, live=True)]

    window = MainWindow(state, preset_layouts(), store)

    assert calls == [[]]
    window.close()


def test_main_window_refreshes_library_index_from_folder_scan(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    video_path = tmp_path / "one.mp4"
    video_path.write_bytes(b"fake")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.folders = [FolderEntry(id="f1", name="NAS", path=str(tmp_path), count=0, live=True)]
    window = MainWindow(state, preset_layouts(), store)

    window._folder_scan_refreshed(
        {
            "videos": [VideoItem.from_path(video_path)],
            "folder_counts": {"f1": 1},
        }
    )

    assert [video.title for video in state.library_videos] == ["one"]
    assert state.folders[0].count == 1
    assert [video.title for video in store.load_library_index()] == ["one"]
    window.close()


def test_main_window_skips_cache_rewrite_when_folder_scan_is_unchanged(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    video_path = tmp_path / "one.mp4"
    video_path.write_bytes(b"fake")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.folders = [FolderEntry(id="f1", name="NAS", path=str(tmp_path), count=1, live=True)]
    video = VideoItem.from_path(video_path)
    state.library_videos = [video]
    window = MainWindow(state, preset_layouts(), store)
    saved_indexes = []
    synced = []
    window.store.save_library_index = saved_indexes.append
    window._sync_ui = lambda: synced.append(True)

    window._folder_scan_refreshed(
        {
            "videos": [video],
            "folder_counts": {"f1": 1},
        }
    )

    assert saved_indexes == []
    assert synced == []
    window.close()


def test_main_window_logs_folder_scan_failures(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.folders = [FolderEntry(id="f1", name="NAS", path=str(tmp_path), count=1, live=True)]
    window = MainWindow(state, preset_layouts(), store)
    toasts = []
    window._toast = toasts.append

    window._folder_scan_refreshed({"videos": [], "folder_counts": {}, "folder_errors": {"f1": "mount unavailable"}})

    records = [json.loads(line) for line in store.playback_diagnostics_path.read_text().splitlines()]
    assert records[0]["kind"] == "folder_scan_failed"
    assert records[0]["folder_id"] == "f1"
    assert records[0]["folder_name"] == "NAS"
    assert records[0]["message"] == "mount unavailable"
    assert toasts == ["Folder scan failed: NAS"]
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


def test_transport_repeat_button_cycles_modes_and_persists(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    window = MainWindow(state, preset_layouts(), store)

    assert callable(getattr(window, "_cycle_repeat_mode", None))
    assert window.repeat_button.text() == "↻"
    window._cycle_repeat_mode()
    assert state.repeat_mode == "one"
    assert window.repeat_button.text() == "↻1"

    window._cycle_repeat_mode()
    assert state.repeat_mode == "all"
    assert window.repeat_button.text() == "↻∞"

    window._cycle_repeat_mode()
    assert state.repeat_mode == "folder"
    assert store.load_session().repeat_mode == "folder"
    window.close()


def test_transport_shuffle_button_toggles_and_persists(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    window = MainWindow(state, preset_layouts(), store)

    assert callable(getattr(window, "_toggle_shuffle", None))
    window._toggle_shuffle()

    assert state.shuffle is True
    assert window.shuffle_button.text() == "⤨"
    assert store.load_session().shuffle is True
    window.close()


def test_transport_next_previous_assign_adjacent_videos(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    first_path = tmp_path / "one.mp4"
    second_path = tmp_path / "two.mp4"
    first_path.write_bytes(b"fake")
    second_path.write_bytes(b"fake")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    first = VideoItem.from_path(first_path, index=1)
    second = VideoItem.from_path(second_path, index=2)
    state.library_videos = [first, second]
    state.cell_content[0] = CellContent.video(first.id)
    window = MainWindow(state, preset_layouts(), store)
    window.grid.cells = [_PlaybackCell(0, first, TransportSnapshot(position=1, duration=10, paused=False))]
    window._sync_ui = lambda: None

    window._skip_video(1)
    assert state.cell_content[0] == CellContent.video(second.id)

    window.grid.cells = [_PlaybackCell(0, second, TransportSnapshot(position=1, duration=10, paused=False))]
    window._skip_video(-1)
    assert state.cell_content[0] == CellContent.video(first.id)
    window.grid.cells = []
    window.close()


def test_transport_stop_pauses_and_rewinds_active_video(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    video_path = tmp_path / "one.mp4"
    video_path.write_bytes(b"fake")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    video = VideoItem.from_path(video_path)
    window = MainWindow(state, preset_layouts(), store)
    mpv = _ControllableMpv()
    window.grid.cells = [_Cell(kind="video", index=0, mpv=mpv)]

    window._stop_video()

    assert state.playing is False
    assert mpv.seeked == [0]
    assert mpv.paused == [True]
    window.grid.cells = []
    window.close()


def test_unified_timeline_tracks_all_local_video_heads(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    first = VideoItem(id="v1", title="One")
    second = VideoItem(id="v2", title="Two")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    window = MainWindow(state, preset_layouts(), store)
    window.grid.cells = [
        _PlaybackCell(0, first, TransportSnapshot(position=60, duration=120, paused=False)),
        _PlaybackCell(1, second, TransportSnapshot(position=30, duration=1440, paused=False)),
        _Cell(kind="browser", index=2),
    ]

    window._refresh_transport()

    assert window.timeline.duration == 1440
    assert [(track.cell, track.position, track.duration) for track in window.timeline.tracks] == [(1, 60, 120), (2, 30, 1440)]
    window.grid.cells = []
    window.close()


def test_delete_custom_layout_removes_it_and_persists_remaining_custom_layouts(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    custom_a = LayoutDefinition("custom-a", "Desk A", LayoutNode.leaf(), custom=True)
    custom_b = LayoutDefinition("custom-b", "Desk B", LayoutNode.leaf(), custom=True)
    window = MainWindow(AppState(), [*preset_layouts(), custom_a, custom_b], store)

    assert callable(getattr(window, "_delete_custom_layout", None))
    window._delete_custom_layout("custom-a")

    assert [layout.id for layout in window.layouts if layout.custom] == ["custom-b"]
    assert [layout.id for layout in store.load_layouts()] == ["custom-b"]
    window.close()


def test_delete_current_custom_layout_falls_back_to_default_layout(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.layout_id = "custom-a"
    custom = LayoutDefinition("custom-a", "Desk A", LayoutNode.leaf(), custom=True)
    window = MainWindow(state, [*preset_layouts(), custom], store)

    window._delete_custom_layout("custom-a")

    assert state.layout_id == preset_layouts()[0].id
    assert store.load_session().layout_id == preset_layouts()[0].id
    assert store.load_layouts() == []
    window.close()


def test_delete_preset_layout_is_ignored(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.layout_id = "2x2"
    layouts = preset_layouts()
    window = MainWindow(state, layouts, store)

    window._delete_custom_layout("2x2")

    assert [layout.id for layout in window.layouts] == [layout.id for layout in layouts]
    assert state.layout_id == "2x2"
    window.close()


def test_finished_video_auto_advances_repeat_all(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    first_path = tmp_path / "one.mp4"
    second_path = tmp_path / "two.mp4"
    first_path.write_bytes(b"fake")
    second_path.write_bytes(b"fake")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    first = VideoItem.from_path(first_path, index=1)
    second = VideoItem.from_path(second_path, index=2)
    state.library_videos = [first, second]
    state.repeat_mode = "all"
    window = MainWindow(state, preset_layouts(), store)
    state.cell_content[0] = CellContent.video(first.id)
    window.grid.cells = [_PlaybackCell(0, first, TransportSnapshot(position=10, duration=10, paused=False, eof_reached=True))]
    window._sync_ui = lambda: None

    window._refresh_transport()

    assert state.cell_content[0] == CellContent.video(second.id)
    assert store.load_session().cell_content[0] == CellContent.video(second.id)
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


class _PlaybackMpv:
    def __init__(self, snapshot: TransportSnapshot) -> None:
        self.snapshot = snapshot

    def transport_snapshot(self) -> TransportSnapshot:
        return self.snapshot


class _ControllableMpv:
    def __init__(self) -> None:
        self.seeked = []
        self.paused = []

    def seek_absolute(self, seconds: float) -> None:
        self.seeked.append(seconds)

    def set_pause(self, paused: bool) -> None:
        self.paused.append(paused)

    def transport_snapshot(self) -> TransportSnapshot:
        return TransportSnapshot(position=4, duration=12, paused=False)


class _PlaybackCell:
    def __init__(self, index: int, video: VideoItem, snapshot: TransportSnapshot) -> None:
        self.index = index
        self.video = video
        self.content = CellContent.video(video.id)
        self.mpv = _PlaybackMpv(snapshot)

    def isVisible(self) -> bool:
        return True

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
