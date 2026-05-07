from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from playxls.models import VIDEO_EXTENSIONS, FolderEntry, VideoItem


class FolderScanner:
    def __init__(self, folders: list[FolderEntry], on_added: Callable[[VideoItem], None], interval_seconds: float = 5.0) -> None:
        self.folders = folders
        self.on_added = on_added
        self.interval_seconds = interval_seconds
        self._seen: set[Path] = set()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
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

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            for folder in self.folders:
                if not folder.live:
                    continue
                current = set(_iter_video_files(folder.path))
                folder.count = len(current)
                added = sorted(current - self._seen)
                self._seen.update(current)
                for idx, path in enumerate(added):
                    self.on_added(VideoItem.from_path(path, index=int(time.time()) + idx))


def scan_folder(path: str) -> list[VideoItem]:
    return [VideoItem.from_path(file, index=i) for i, file in enumerate(sorted(_iter_video_files(path)))]


def _iter_video_files(path: str) -> list[Path]:
    root = Path(path).expanduser()
    if not root.exists() or not root.is_dir():
        return []
    return [item for item in root.iterdir() if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS]
