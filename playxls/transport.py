from __future__ import annotations

import math
from dataclasses import dataclass


def format_timestamp(seconds: float | int | None) -> str:
    value = _seconds_or_none(seconds)
    if value is None:
        return "--:--"
    total = int(value + 0.5)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


@dataclass(frozen=True, slots=True)
class TransportSnapshot:
    position: float | None = None
    duration: float | None = None
    paused: bool = False
    eof_reached: bool = False

    @property
    def progress_percent(self) -> float:
        duration = _seconds_or_none(self.duration)
        if not duration:
            return 0.0
        position = _seconds_or_none(self.position) or 0.0
        return max(0.0, min(100.0, position / duration * 100))

    @property
    def position_text(self) -> str:
        return format_timestamp(self.position)

    @property
    def duration_text(self) -> str:
        return format_timestamp(self.duration)


def _seconds_or_none(seconds: float | int | None) -> float | None:
    if seconds is None:
        return None
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return max(0.0, value)
