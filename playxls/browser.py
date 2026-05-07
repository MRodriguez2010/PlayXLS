from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse


class FullscreenRequest(Protocol):
    def toggleOn(self) -> bool: ...

    def accept(self) -> None: ...


class BrowserFullscreenBridge:
    """Accept page fullscreen requests and report cell-local fullscreen state."""

    def __init__(self, on_state: Callable[[bool], None]) -> None:
        self.on_state = on_state

    def handle(self, request: FullscreenRequest) -> None:
        active = bool(request.toggleOn())
        request.accept()
        self.on_state(active)


@dataclass(frozen=True, slots=True)
class BrowserProfilePaths:
    profile_name: str
    storage_path: Path
    cache_path: Path


@dataclass(frozen=True, slots=True)
class BrowserCompatibilityNotice:
    level: str
    label: str
    detail: str


DRM_LIMITED_DOMAINS = {
    "disneyplus.com",
    "hbomax.com",
    "max.com",
    "netflix.com",
    "primevideo.com",
}


def browser_profile_paths(cache_dir: Path, cell_number: int, *, profile_scope: str = "shared") -> BrowserProfilePaths:
    if profile_scope != "per_cell":
        shared_dir = cache_dir / "browser" / "shared"
        return BrowserProfilePaths(
            profile_name="playxls-shared",
            storage_path=shared_dir / "storage",
            cache_path=shared_dir / "cache",
        )
    cell_dir = cache_dir / "browser" / f"cell-{cell_number}"
    return BrowserProfilePaths(
        profile_name=f"playxls-cell-{cell_number}",
        storage_path=cell_dir / "storage",
        cache_path=cell_dir / "cache",
    )


def normalize_browser_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        return "about:blank"
    parsed = urlparse(value)
    if parsed.scheme:
        return value
    return f"https://{value}"


def browser_compatibility_notice(raw_url: str) -> BrowserCompatibilityNotice | None:
    parsed = urlparse(normalize_browser_url(raw_url))
    host = (parsed.hostname or "").casefold()
    if host.startswith("www."):
        host = host[4:]
    if any(host == domain or host.endswith(f".{domain}") for domain in DRM_LIMITED_DOMAINS):
        return BrowserCompatibilityNotice(
            level="warning",
            label="DRM limited",
            detail="Protected video may not play inside QtWebEngine. Use the system browser if playback is blocked.",
        )
    return None
