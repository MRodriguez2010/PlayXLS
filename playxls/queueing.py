from __future__ import annotations

import random
from collections.abc import Callable, Sequence

from playxls.models import RepeatMode, VideoItem


def next_video_for_repeat(
    current: VideoItem,
    videos: Sequence[VideoItem],
    *,
    repeat_mode: RepeatMode,
    shuffle: bool,
    choose: Callable[[Sequence[VideoItem]], VideoItem] = random.choice,
) -> VideoItem | None:
    if repeat_mode == "folder":
        scope = [video for video in videos if video.folder == current.folder]
    elif repeat_mode == "all":
        scope = list(videos)
    else:
        return None
    candidates = [video for video in scope if video.id != current.id]
    if not candidates:
        return None
    if shuffle:
        return choose(candidates)
    current_index = next((index for index, video in enumerate(scope) if video.id == current.id), -1)
    if current_index == -1:
        return scope[0]
    return scope[(current_index + 1) % len(scope)]
