import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from playxls.models import AppSettings, KeyBinding
from playxls.theme import THEMES
from playxls.ui.dialogs import SettingsDialog


def test_settings_dialog_records_next_keypress_for_binding():
    app = QApplication.instance() or QApplication([])
    bindings = [KeyBinding(id="kb1", action="Play / Pause", combo="Space", type="key")]
    dialog = SettingsDialog(THEMES["dark"], AppSettings(), bindings)
    changes = []
    dialog.bindings_changed.connect(lambda updated: changes.append(updated))

    button = next(widget for widget in dialog.findChildren(QPushButton) if widget.text() == "Space")
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    QTest.keyClick(dialog, Qt.Key.Key_K)

    assert bindings[0].combo == "K"
    assert button.text() == "K"
    assert changes[-1][0].combo == "K"


def test_settings_dialog_updates_browser_profile_scope():
    app = QApplication.instance() or QApplication([])
    settings = AppSettings()
    dialog = SettingsDialog(THEMES["dark"], settings, [])
    changes = []
    dialog.settings_changed.connect(lambda updated: changes.append(updated))

    button = next(widget for widget in dialog.findChildren(QPushButton) if widget.property("value") == "per_cell")
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)

    assert settings.browser_profile_scope == "per_cell"
    assert changes[-1].browser_profile_scope == "per_cell"
