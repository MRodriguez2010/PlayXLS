from __future__ import annotations

import threading
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Callable

from playxls.models import VIDEO_EXTENSIONS, FolderEntry, VideoItem


DEFAULT_SCAN_INTERVAL_SECONDS = 30.0
DEFAULT_INITIAL_SCAN_DELAY_SECONDS = 1.0


class FolderScanner:
    def __init__(
        self,
        folders: list[FolderEntry],
        on_added: Callable[[VideoItem], None],
        interval_seconds: float = DEFAULT_SCAN_INTERVAL_SECONDS,
        seen_paths: Iterable[str | Path] | None = None,
        on_refreshed: Callable[[dict[str, object]], None] | None = None,
        initial_delay_seconds: float = DEFAULT_INITIAL_SCAN_DELAY_SECONDS,
    ) -> None:
        self.folders = folders
        self.on_added = on_added
        self.on_refreshed = on_refreshed
        self.interval_seconds = interval_seconds
        self.initial_delay_seconds = initial_delay_seconds
        self._seen: set[Path] = {Path(path).expanduser() for path in seen_paths or []}
        self._prime_on_start = seen_paths is None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if self._prime_on_start:
            self._prime_seen()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="playxls-folder-scanner", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        self._thread = None

    def _prime_seen(self) -> None:
        for folder in self.folders:
            self._seen.update(_iter_video_files(folder.path))

    def scan_once(self) -> None:
        refreshed: list[VideoItem] = []
        counts: dict[str, int] = {}
        errors: dict[str, str] = {}
        for folder in self.folders:
            if not folder.live:
                continue
            try:
                current = set(_iter_video_files(folder.path))
            except OSError as exc:
                errors[folder.id] = str(exc) or exc.__class__.__name__
                continue
            folder.count = len(current)
            counts[folder.id] = len(current)
            refreshed.extend(VideoItem.from_path(path, index=len(refreshed)) for path in sorted(current))
            added = sorted(current - self._seen)
            self._seen.update(current)
            if self.on_refreshed is None:
                for idx, path in enumerate(added):
                    self.on_added(VideoItem.from_path(path, index=int(time.time()) + idx))
        if self.on_refreshed is not None:
            self.on_refreshed({"videos": refreshed, "folder_counts": counts, "folder_errors": errors})

    def _run(self) -> None:
        if self._stop.wait(self.initial_delay_seconds):
            return
        while not self._stop.is_set():
            self.scan_once()
            if self._stop.wait(self.interval_seconds):
                return


def scan_folder(path: str) -> list[VideoItem]:
    return [VideoItem.from_path(file, index=i) for i, file in enumerate(sorted(_iter_video_files(path)))]


def _iter_video_files(path: str) -> list[Path]:
    root = Path(path).expanduser()
    if not root.exists() or not root.is_dir():
        return []
    return [item for item in root.iterdir() if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS]
