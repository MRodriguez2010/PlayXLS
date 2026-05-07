from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

from playxls.video import MpvController


@dataclass(slots=True)
class PreviewEntry:
    source: str
    window_id: int
    controller: MpvController


class PreviewPool:
    """Small LRU pool for muted library hover previews."""

    def __init__(self, max_size: int = 5, mpv_factory: Callable[..., MpvController] = MpvController) -> None:
        self.max_size = max(0, int(max_size))
        self.mpv_factory = mpv_factory
        self._entries: OrderedDict[str, PreviewEntry] = OrderedDict()

    def configure(self, max_size: int) -> None:
        self.max_size = max(0, int(max_size))
        self._evict_over_limit()

    def start(self, source: str, *, window_id: int, muted: bool = True) -> MpvController | None:
        if self.max_size <= 0 or not source:
            return None
        entry = self._entries.get(source)
        if entry and entry.window_id == window_id:
            self._entries.move_to_end(source)
            entry.controller.set_volume(0.0 if muted else 0.6)
            entry.controller.set_pause(False)
            return entry.controller
        if entry:
            entry.controller.stop()
            del self._entries[source]

        controller = self.mpv_factory(window_id=window_id)
        if not controller.available:
            return None
        loaded = controller.load(source, paused=False, loop=True, volume=0 if muted else 60)
        if not loaded:
            controller.stop()
            return None
        self._entries[source] = PreviewEntry(source, window_id, controller)
        self._evict_over_limit()
        return controller

    def pause(self, source: str) -> None:
        entry = self._entries.get(source)
        if entry:
            entry.controller.set_pause(True)

    def stop(self, source: str) -> None:
        entry = self._entries.pop(source, None)
        if entry:
            entry.controller.stop()

    def stop_all(self) -> None:
        for entry in self._entries.values():
            entry.controller.stop()
        self._entries.clear()

    def sources(self) -> list[str]:
        return list(self._entries.keys())

    def _evict_over_limit(self) -> None:
        while len(self._entries) > self.max_size:
            _, entry = self._entries.popitem(last=False)
            entry.controller.stop()
