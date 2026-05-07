import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PySide6.QtCore import Qt
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


def test_library_tab_limits_large_initial_render(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    pool = FakePreviewPool()
    settings = AppSettings(preview_mode="thumb")
    tab = LibraryTab(THEMES["dark"], preview_pool=pool)
    videos = [
        VideoItem(id=f"v{index}", title=f"Video {index:03}", path=str(tmp_path / f"video-{index:03}.mp4"))
        for index in range(205)
    ]

    tab.set_data(videos, [CellContent.empty()], 1, settings)

    assert len(tab.body.findChildren(VideoRow)) == 200

    tab._show_more()

    assert len(tab.body.findChildren(VideoRow)) == 205


def test_video_row_uses_native_thumbnail_only_for_live_preview(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    video = VideoItem(id="v1", title="One", path=str(tmp_path / "one.mp4"), src=str(tmp_path / "one.mp4"))

    thumb_row = VideoRow(
        THEMES["dark"],
        video,
        [CellContent.empty()],
        1,
        lambda video_id, index: None,
        lambda video_id: None,
        preview_pool=FakePreviewPool(),
        preview_mode="thumb",
    )
    lazy_row = VideoRow(
        THEMES["dark"],
        video,
        [CellContent.empty()],
        1,
        lambda video_id, index: None,
        lambda video_id: None,
        preview_pool=FakePreviewPool(),
        preview_mode="lazy",
    )

    assert thumb_row.thumb.testAttribute(Qt.WidgetAttribute.WA_NativeWindow) is False
    assert lazy_row.thumb.testAttribute(Qt.WidgetAttribute.WA_NativeWindow) is True


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


def test_video_row_does_not_pause_preview_pool_when_preview_mode_is_static(tmp_path: Path):
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
        preview_mode="thumb",
        preview_delay_ms=0,
        preview_muted=True,
    )

    row._stop_preview()

    assert pool.paused == []


class FakePreviewPool:
    def __init__(self) -> None:
        self.started: list[tuple[str, bool]] = []
        self.paused: list[str] = []

    def start(self, source: str, *, window_id: int, muted: bool):
        self.started.append((source, muted))
        return object()

    def pause(self, source: str) -> None:
        self.paused.append(source)
