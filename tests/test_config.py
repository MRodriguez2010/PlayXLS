from pathlib import Path

from playxls.config import ConfigStore
from playxls.layout import LayoutDefinition, LayoutNode, layout_to_dict
from playxls.models import AppSettings, BrowserPreset, CellContent, FolderEntry, KeyBinding, SessionState, VideoItem


def test_settings_round_trip_defaults_missing_values(tmp_path: Path):
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")

    settings = AppSettings(theme="light", border_mode="never", expand_percent=160, browser_profile_scope="per_cell")
    store.save_settings(settings)
    loaded = store.load_settings()

    assert loaded.theme == "light"
    assert loaded.border_mode == "never"
    assert loaded.expand_percent == 160
    assert loaded.browser_profile_scope == "per_cell"
    assert loaded.preview_cache_size == AppSettings().preview_cache_size


def test_layouts_round_trip_custom_tree(tmp_path: Path):
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    tree = LayoutNode.split("v", 0.6, LayoutNode.leaf(), LayoutNode.split("h", 0.5, LayoutNode.leaf(), LayoutNode.leaf()))

    store.save_layouts([LayoutDefinition(id="custom-1", label="Desk", tree=tree, custom=True)])
    loaded = store.load_layouts()

    assert len(loaded) == 1
    assert loaded[0].id == "custom-1"
    assert loaded[0].label == "Desk"
    assert loaded[0].custom is True
    assert layout_to_dict(loaded[0].tree) == layout_to_dict(tree)


def test_bindings_and_watch_folders_round_trip(tmp_path: Path):
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")

    store.save_bindings([KeyBinding(id="kb1", action="Play / Pause", combo="K", type="key")])
    store.save_watch_folders([FolderEntry(id="f1", name="Animations", path="~/Videos/Animations", count=3, live=False)])

    assert store.load_bindings()[0].combo == "K"
    assert store.load_watch_folders()[0].live is False


def test_browser_presets_and_ignored_videos_round_trip(tmp_path: Path):
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    presets = [BrowserPreset(id="custom-1", name="Example", url="https://example.com", color="#fbbf24")]

    store.save_browser_presets(presets)
    store.save_ignored_video_paths({"/videos/hidden.mp4"})

    assert store.load_browser_presets() == presets
    assert store.load_ignored_video_paths() == {"/videos/hidden.mp4"}


def test_library_index_round_trip(tmp_path: Path):
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    videos = [VideoItem(id="v1", title="One", folder="NAS", path="/nas/one.mp4", src="/nas/one.mp4")]

    store.save_library_index(videos)

    assert store.load_library_index() == videos


def test_session_round_trip_preserves_layout_and_cells(tmp_path: Path):
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    session = SessionState(
        layout_id="1+2",
        cell_content=[
            CellContent.video("v1"),
            CellContent.browser("https://youtube.com", "YouTube"),
            CellContent.empty(),
        ],
        master_volume=0.45,
        muted=True,
    )

    store.save_session(session)
    loaded = store.load_session()

    assert loaded.layout_id == "1+2"
    assert loaded.cell_content[0] == CellContent.video("v1")
    assert loaded.cell_content[1] == CellContent.browser("https://youtube.com", "YouTube")
    assert loaded.cell_content[2] == CellContent.empty()
    assert loaded.master_volume == 0.45
    assert loaded.muted is True


def test_session_round_trip_preserves_repeat_and_shuffle(tmp_path: Path):
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    session = SessionState(repeat_mode="folder", shuffle=True)

    store.save_session(session)
    loaded = store.load_session()

    assert loaded.repeat_mode == "folder"
    assert loaded.shuffle is True


def test_session_round_trip_preserves_main_splitter_sizes(tmp_path: Path):
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    session = SessionState(main_splitter_sizes=[280, 1000])

    store.save_session(session)
    loaded = store.load_session()

    assert loaded.main_splitter_sizes == [280, 1000]
