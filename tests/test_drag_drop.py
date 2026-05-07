import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PySide6.QtWidgets import QApplication

from playxls.config import ConfigStore
from playxls.models import AppState, CellContent
from playxls.ui.main_window import MainWindow
from playxls.layout import preset_layouts


def test_add_video_files_adds_library_items_and_assigns_visible_cells(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    file_a = tmp_path / "one.mp4"
    file_b = tmp_path / "two.mov"
    file_a.write_bytes(b"fake")
    file_b.write_bytes(b"fake")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.layout_id = "1x2"
    window = MainWindow(state, preset_layouts(), store)

    window._add_video_files([file_a, file_b])

    assert [video.title for video in state.library_videos] == ["one", "two"]
    assert state.cell_content[0] == CellContent.video(state.library_videos[0].id)
    assert state.cell_content[1] == CellContent.video(state.library_videos[1].id)
    window.close()
