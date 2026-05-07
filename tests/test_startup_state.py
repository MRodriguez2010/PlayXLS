import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from playxls.config import ConfigStore
from playxls.models import CellContent, FolderEntry, SessionState
from playxls.ui.main_window import build_state


def test_build_state_scans_persisted_watch_folders_without_demo_videos(tmp_path: Path):
    watch_dir = tmp_path / "Watch Me"
    watch_dir.mkdir()
    video = watch_dir / "local-video.mp4"
    video.write_bytes(b"not a real mp4 for metadata tests")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    store.save_watch_folders([FolderEntry(id="f1", name="Watch Me", path=str(watch_dir), count=0, live=True)])

    state, _layouts = build_state([], store)

    assert [item.title for item in state.library_videos] == ["local-video"]
    assert state.folders[0].count == 1


def test_build_state_clears_session_cells_that_reference_missing_videos(tmp_path: Path):
    watch_dir = tmp_path / "Watch Me"
    watch_dir.mkdir()
    (watch_dir / "local-video.mp4").write_bytes(b"not a real mp4")
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    store.save_watch_folders([FolderEntry(id="f1", name="Watch Me", path=str(watch_dir), count=0, live=True)])
    store.save_session(SessionState(layout_id="1x1", cell_content=[CellContent.video("cli-1-bar")]))

    state, _layouts = build_state([], store)

    assert state.cell_content[0] == CellContent.empty()


def test_build_state_prunes_missing_prototype_watch_folders(tmp_path: Path):
    watch_dir = tmp_path / "Watch Me"
    watch_dir.mkdir()
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    store.save_watch_folders(
        [
            FolderEntry(id="f1", name="Animations", path=str(tmp_path / "missing-animations"), count=0, live=True),
            FolderEntry(id="f2", name="Trailers", path=str(tmp_path / "missing-trailers"), count=0, live=True),
            FolderEntry(id="f3", name="Sci-Fi", path=str(tmp_path / "missing-scifi"), count=0, live=False),
            FolderEntry(id="f4", name="Watch Me", path=str(watch_dir), count=0, live=True),
        ]
    )

    state, _layouts = build_state([], store)

    assert [folder.name for folder in state.folders] == ["Watch Me"]
