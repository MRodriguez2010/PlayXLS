import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from playxls.models import BrowserPreset, CellContent
from playxls.theme import THEMES
from playxls.ui.panels import BrowserRow


def test_browser_row_shows_drm_limited_notice_for_protected_services():
    app = QApplication.instance() or QApplication([])
    row = BrowserRow(
        THEMES["dark"],
        BrowserPreset(id="nf", name="Netflix", url="https://netflix.com", color="#e50914"),
        [CellContent.empty()],
        1,
        lambda preset, index: None,
        lambda preset_id: None,
    )

    assert row.compatibility_notice.isHidden() is False
    assert row.compatibility_notice.text() == "DRM limited"
    assert "system browser" in row.compatibility_notice.toolTip()


def test_browser_row_hides_notice_for_standard_services():
    app = QApplication.instance() or QApplication([])
    row = BrowserRow(
        THEMES["dark"],
        BrowserPreset(id="yt", name="YouTube", url="https://youtube.com", color="#ff0000"),
        [CellContent.empty()],
        1,
        lambda preset, index: None,
        lambda preset_id: None,
    )

    assert row.compatibility_notice.isHidden() is True
