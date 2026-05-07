from pathlib import Path

import playxls.browser as browser
from playxls.browser import BrowserFullscreenBridge, browser_profile_paths, normalize_browser_url


class FakeFullscreenRequest:
    def __init__(self, enabled: bool) -> None:
        self._enabled = enabled
        self.accepted = False

    def toggleOn(self) -> bool:
        return self._enabled

    def accept(self) -> None:
        self.accepted = True


def test_browser_fullscreen_bridge_accepts_and_reports_state():
    states = []
    bridge = BrowserFullscreenBridge(lambda active: states.append(active))
    request = FakeFullscreenRequest(True)

    bridge.handle(request)

    assert request.accepted is True
    assert states == [True]


def test_browser_fullscreen_bridge_accepts_exit_state():
    states = []
    bridge = BrowserFullscreenBridge(lambda active: states.append(active))
    request = FakeFullscreenRequest(False)

    bridge.handle(request)

    assert request.accepted is True
    assert states == [False]


def test_normalize_browser_url_adds_https_when_scheme_missing():
    assert normalize_browser_url("example.com/watch") == "https://example.com/watch"
    assert normalize_browser_url("https://example.com") == "https://example.com"
    assert normalize_browser_url("http://localhost:8080") == "http://localhost:8080"


def test_browser_profile_paths_are_shared_by_default(tmp_path: Path):
    paths = browser_profile_paths(tmp_path, 2)

    assert paths.profile_name == "playxls-shared"
    assert paths.storage_path == tmp_path / "browser" / "shared" / "storage"
    assert paths.cache_path == tmp_path / "browser" / "shared" / "cache"


def test_browser_profile_paths_can_be_per_cell(tmp_path: Path):
    paths = browser_profile_paths(tmp_path, 2, profile_scope="per_cell")

    assert paths.profile_name == "playxls-cell-2"
    assert paths.storage_path == tmp_path / "browser" / "cell-2" / "storage"
    assert paths.cache_path == tmp_path / "browser" / "cell-2" / "cache"


def test_browser_compatibility_notice_flags_drm_heavy_services():
    assert callable(getattr(browser, "browser_compatibility_notice", None))
    for url in ("netflix.com", "https://disneyplus.com", "https://www.primevideo.com", "https://play.max.com"):
        notice = browser.browser_compatibility_notice(url)

        assert notice is not None
        assert notice.level == "warning"
        assert "DRM" in notice.label


def test_browser_compatibility_notice_allows_standard_video_sites():
    assert browser.browser_compatibility_notice("https://youtube.com") is None
    assert browser.browser_compatibility_notice("https://twitch.tv") is None
    assert browser.browser_compatibility_notice("https://example.com") is None
