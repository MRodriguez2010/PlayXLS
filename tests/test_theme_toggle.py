import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PySide6.QtWidgets import QApplication

from playxls.config import ConfigStore
from playxls.layout import preset_layouts
from playxls.models import AppState
from playxls.ui.main_window import MainWindow


def test_toggle_theme_propagates_to_shell_and_sources(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.settings.theme = "dark"
    window = MainWindow(state, preset_layouts(), store)

    window._toggle_theme()

    assert state.settings.theme == "light"
    assert window.theme.name == "light"
    assert window.sources.theme.name == "light"
    assert "#fafaf9" in window.stage_shell.styleSheet()
    window.close()


def test_settings_theme_change_repaints_shell(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(config_dir=tmp_path / "config", cache_dir=tmp_path / "cache", state_dir=tmp_path / "state")
    state = AppState()
    state.settings.theme = "dark"
    window = MainWindow(state, preset_layouts(), store)

    state.settings.theme = "light"
    window._settings_changed()

    assert window.theme.name == "light"
    assert window.sources.theme.name == "light"
    assert "#fafaf9" in window.stage_shell.styleSheet()
    window.close()
