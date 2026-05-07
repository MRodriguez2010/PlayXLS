import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

from pathlib import Path

from PySide6.QtWebEngineCore import QWebEngineLoadingInfo
from PySide6.QtWidgets import QApplication

from playxls.models import AppSettings, CellContent
from playxls.theme import THEMES
from playxls.ui.grid import CellWidget


def test_browser_cell_uses_shared_profile_paths_by_default(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    cell = CellWidget(1, THEMES["dark"], tmp_path)

    cell.set_content(CellContent.browser("https://example.com", "Example"), None, AppSettings())

    assert cell.browser_profile is not None
    assert cell.browser_profile.storageName() == "playxls-shared"
    assert cell.browser_profile.persistentStoragePath() == str(tmp_path / "browser" / "shared" / "storage")
    assert cell.browser_profile.cachePath() == str(tmp_path / "browser" / "shared" / "cache")
    cell._clear_body()


def test_browser_cells_reuse_one_shared_profile_instance(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    first = CellWidget(0, THEMES["dark"], tmp_path)
    second = CellWidget(1, THEMES["dark"], tmp_path)

    first.set_content(CellContent.browser("https://example.com", "Example"), None, AppSettings())
    second.set_content(CellContent.browser("https://youtube.com", "YouTube"), None, AppSettings())

    assert first.browser_profile is second.browser_profile
    first._clear_body()
    assert second.browser_profile is not None
    assert second.browser_profile.storageName() == "playxls-shared"
    second._clear_body()


def test_browser_cell_can_use_per_cell_profile_paths(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    cell = CellWidget(1, THEMES["dark"], tmp_path)

    cell.set_content(CellContent.browser("https://example.com", "Example"), None, AppSettings(browser_profile_scope="per_cell"))

    assert cell.browser_profile is not None
    assert cell.browser_profile.storageName() == "playxls-cell-2"
    assert cell.browser_profile.persistentStoragePath() == str(tmp_path / "browser" / "cell-2" / "storage")
    assert cell.browser_profile.cachePath() == str(tmp_path / "browser" / "cell-2" / "cache")
    cell._clear_body()


def test_browser_cell_rebuilds_when_profile_scope_changes(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    cell = CellWidget(1, THEMES["dark"], tmp_path)
    content = CellContent.browser("https://example.com", "Example")

    cell.set_content(content, None, AppSettings())
    cell.set_content(content, None, AppSettings(browser_profile_scope="per_cell"))

    assert cell.browser_profile is not None
    assert cell.browser_profile.storageName() == "playxls-cell-2"
    cell._clear_body()


def test_browser_cell_has_no_in_cell_browser_toolbar(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    cell = CellWidget(1, THEMES["dark"], tmp_path)

    cell.set_content(CellContent.browser("https://example.com", "Example"), None, AppSettings())
    assert not hasattr(cell, "browser_chrome")
    assert not hasattr(cell, "browser_back")
    assert not hasattr(cell, "chrome_url")
    cell._clear_body()


def test_browser_web_view_fills_cell_without_layout_managed_chrome(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    cell = CellWidget(1, THEMES["dark"], tmp_path)

    cell.set_content(CellContent.browser("https://example.com", "Example"), None, AppSettings())
    cell.resize(640, 360)
    cell.show()
    app.processEvents()

    assert cell.web_view is not None
    assert cell.root.indexOf(cell.web_view) == -1
    assert cell.web_view.geometry().x() == 0
    assert cell.web_view.geometry().y() == 0
    assert cell.web_view.geometry().width() == 640
    assert cell.web_view.geometry().height() == 360
    cell._clear_body()


def test_browser_cell_positions_overlays_at_cell_edges_after_resize(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    cell = CellWidget(1, THEMES["dark"], tmp_path)

    cell.set_content(CellContent.browser("https://example.com", "Example"), None, AppSettings())
    cell.resize(640, 360)
    cell.show()
    app.processEvents()

    assert cell.badge.y() == 8
    assert cell.fullscreen_button.y() == 8
    cell._clear_body()


def test_browser_cell_positions_overlays_when_content_is_assigned_after_resize(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    cell = CellWidget(1, THEMES["dark"], tmp_path)

    cell.resize(640, 360)
    cell.show()
    app.processEvents()
    cell.set_content(CellContent.browser("https://example.com", "Example"), None, AppSettings())
    app.processEvents()

    assert cell.badge.y() == 8
    assert cell.fullscreen_button.y() == 8
    cell._clear_body()


def test_browser_page_fullscreen_stays_inside_cell(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    cell = CellWidget(1, THEMES["dark"], tmp_path)
    fullscreen_requests = []
    cell.fullscreen_requested.connect(fullscreen_requests.append)
    cell.set_content(CellContent.browser("https://example.com", "Example"), None, AppSettings())

    cell._browser_fullscreen_requested(True)

    assert fullscreen_requests == []
    assert cell.browser_page_fullscreen is True

    cell._browser_fullscreen_requested(False)

    assert fullscreen_requests == []
    assert cell.browser_page_fullscreen is False
    cell._clear_body()


def test_browser_cell_reports_failed_page_load(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    cell = CellWidget(1, THEMES["dark"], tmp_path)
    failures = []
    assert hasattr(cell, "browser_load_failed")
    cell.browser_load_failed.connect(lambda index, message: failures.append((index, message)))
    cell.set_content(CellContent.browser("https://example.invalid", "Broken"), None, AppSettings())

    assert callable(getattr(cell, "_browser_load_finished", None))
    cell._browser_load_finished(False)

    assert failures == [(1, "Load failed")]
    cell._clear_body()


def test_browser_cell_reports_loading_changed_error_detail(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    cell = CellWidget(1, THEMES["dark"], tmp_path)
    failures = []
    cell.browser_load_failed.connect(lambda index, message: failures.append((index, message)))
    cell.set_content(CellContent.browser("https://example.invalid", "Broken"), None, AppSettings())

    cell._browser_loading_changed(FakeLoadingInfo("net::ERR_NAME_NOT_RESOLVED", -105, "https://example.invalid"))

    assert failures == [(1, "net::ERR_NAME_NOT_RESOLVED (-105)")]
    cell._clear_body()


def test_browser_cell_does_not_overwrite_loading_error_with_generic_load_finished(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    cell = CellWidget(1, THEMES["dark"], tmp_path)
    failures = []
    cell.browser_load_failed.connect(lambda index, message: failures.append((index, message)))
    cell.set_content(CellContent.browser("https://example.invalid", "Broken"), None, AppSettings())

    cell._browser_loading_changed(FakeLoadingInfo("net::ERR_NAME_NOT_RESOLVED", -105, "https://example.invalid"))
    cell._browser_load_finished(False)

    assert failures == [(1, "net::ERR_NAME_NOT_RESOLVED (-105)")]
    cell._clear_body()


def test_browser_cell_resets_loading_error_state_when_content_changes(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    cell = CellWidget(1, THEMES["dark"], tmp_path)
    failures = []
    cell.browser_load_failed.connect(lambda index, message: failures.append((index, message)))
    cell.set_content(CellContent.browser("https://example.invalid", "Broken"), None, AppSettings())

    cell._browser_loading_changed(FakeLoadingInfo("net::ERR_NAME_NOT_RESOLVED", -105, "https://example.invalid"))
    cell.set_content(CellContent.browser("https://other.invalid", "Other"), None, AppSettings())
    cell._browser_load_finished(False)

    assert failures == [(1, "net::ERR_NAME_NOT_RESOLVED (-105)"), (1, "Load failed")]
    cell._clear_body()


class FakeLoadingInfo:
    def __init__(self, error: str, code: int, url: str) -> None:
        self._error = error
        self._code = code
        self._url = _FakeUrl(url)

    def status(self):
        if QWebEngineLoadingInfo is None:
            return "failed"
        return QWebEngineLoadingInfo.LoadStatus.LoadFailedStatus

    def errorString(self) -> str:
        return self._error

    def errorCode(self) -> int:
        return self._code

    def url(self):
        return self._url


class _FakeUrl:
    def __init__(self, value: str) -> None:
        self.value = value

    def toString(self) -> str:
        return self.value
