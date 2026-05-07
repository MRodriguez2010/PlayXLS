import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PySide6.QtWidgets import QApplication

from playxls.models import AppSettings, CellContent, VideoItem
from playxls.theme import THEMES
from playxls.ui.panels import LibraryTab, VideoRow


def test_library_tab_passes_preview_settings_to_rows(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    pool = FakePreviewPool()
    settings = AppSettings(preview_mode="lazy", preview_delay=75, preview_mute=False, preview_cache_size=3)
    tab = LibraryTab(THEMES["dark"], preview_pool=pool)
    video = VideoItem(id="v1", title="One", path=str(tmp_path / "one.mp4"), src=str(tmp_path / "one.mp4"))

    tab.set_data([video], [CellContent.empty()], 1, settings)
    row = tab.body.findChildren(VideoRow)[0]

    assert row.preview_pool is pool
    assert row.preview_delay_ms == 75
    assert row.preview_muted is False
    assert row.preview_mode == "lazy"


def test_video_row_starts_preview_after_delay_and_pauses_on_leave(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    pool = FakePreviewPool()
    video = VideoItem(id="v1", title="One", path=str(tmp_path / "one.mp4"), src=str(tmp_path / "one.mp4"))
    row = VideoRow(
        THEMES["dark"],
        video,
        [CellContent.empty()],
        1,
        lambda video_id, index: None,
        lambda video_id: None,
        preview_pool=pool,
        preview_mode="lazy",
        preview_delay_ms=0,
        preview_muted=True,
    )

    row._start_preview()
    row._stop_preview()

    assert pool.started == [(str(tmp_path / "one.mp4"), True)]
    assert pool.paused == [str(tmp_path / "one.mp4")]


def test_video_row_does_not_preview_when_mode_is_off(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    pool = FakePreviewPool()
    video = VideoItem(id="v1", title="One", path=str(tmp_path / "one.mp4"), src=str(tmp_path / "one.mp4"))
    row = VideoRow(
        THEMES["dark"],
        video,
        [CellContent.empty()],
        1,
        lambda video_id, index: None,
        lambda video_id: None,
        preview_pool=pool,
        preview_mode="off",
        preview_delay_ms=0,
        preview_muted=True,
    )

    row._start_preview()

    assert pool.started == []


class FakePreviewPool:
    def __init__(self) -> None:
        self.started: list[tuple[str, bool]] = []
        self.paused: list[str] = []

    def start(self, source: str, *, window_id: int, muted: bool):
        self.started.append((source, muted))
        return object()

    def pause(self, source: str) -> None:
        self.paused.append(source)
