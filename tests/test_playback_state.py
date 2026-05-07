import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PySide6.QtWidgets import QApplication

from playxls.config import ConfigStore
from playxls.layout import preset_layouts
from playxls.models import AppSettings, AppState, CellContent, SessionState, VideoItem
from playxls.theme import THEMES
from playxls.transport import TransportSnapshot
from playxls.ui.grid import CellWidget
from playxls.ui.main_window import MainWindow, build_state


def test_session_round_trip_preserves_playback_positions(tmp_path: Path):
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    session = SessionState(playback_positions={"/videos/one.mp4": 12.5})

    store.save_session(session)

    assert store.load_session().playback_positions == {"/videos/one.mp4": 12.5}


def test_video_cell_resumes_saved_position_when_setting_enabled(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    video_path = tmp_path / "one.mp4"
    video_path.write_bytes(b"fake")
    fake = FakeMpvController()
    original_factory = CellWidget.mpv_factory
    CellWidget.mpv_factory = lambda window_id=None: fake
    cell = CellWidget(0, THEMES["dark"], tmp_path)

    try:
        cell.set_content(
            CellContent.video("v1"),
            VideoItem(id="v1", title="One", path=str(video_path), src=str(video_path)),
            AppSettings(save_playback_position=True),
            {str(video_path): 12.5},
        )
    finally:
        CellWidget.mpv_factory = original_factory
        cell._clear_body()

    assert fake.loaded_source == str(video_path)
    assert fake.seeked_seconds == 12.5


def test_main_window_captures_playback_positions_before_saving_session(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    video_path = tmp_path / "one.mp4"
    video_path.write_bytes(b"fake")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    video = VideoItem.from_path(video_path)
    state.library_videos = [video]
    window = MainWindow(state, preset_layouts(), store)
    window.grid.cells = [_FakeCell(video, 9.25)]

    window._save_session()

    assert store.load_session().playback_positions == {str(video_path): 9.25}
    window.grid.cells = []
    window.close()


def test_main_window_pauses_when_minimized_and_resumes_only_if_it_was_playing(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.settings.pause_on_minimize = True
    state.playing = True
    window = MainWindow(state, preset_layouts(), store)

    window._handle_minimized_for_playback(True)
    assert state.playing is False

    window._handle_minimized_for_playback(False)
    assert state.playing is True

    state.playing = False
    window._handle_minimized_for_playback(True)
    window._handle_minimized_for_playback(False)

    assert state.playing is False
    window.close()


def test_build_state_loads_persisted_playback_positions(tmp_path: Path):
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    store.save_session(SessionState(playback_positions={"/videos/one.mp4": 7.0}))

    state, _ = build_state([], store)

    assert state.playback_positions == {"/videos/one.mp4": 7.0}


class FakeMpvController:
    available = True

    def __init__(self) -> None:
        self.loaded_source = ""
        self.seeked_seconds = None

    def load(self, source: str, *, paused: bool = False, loop: bool = False, volume: int = 60) -> bool:
        self.loaded_source = source
        return True

    def seek_absolute(self, seconds: float) -> None:
        self.seeked_seconds = seconds

    def stop(self) -> None:
        return None


class _FakeMpv:
    def __init__(self, position: float) -> None:
        self.position = position

    def transport_snapshot(self) -> TransportSnapshot:
        return TransportSnapshot(position=self.position, duration=20, paused=False)


class _FakeCell:
    def __init__(self, video: VideoItem, position: float) -> None:
        self.video = video
        self.mpv = _FakeMpv(position)
