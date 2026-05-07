from playxls.models import VideoItem
from playxls.queueing import next_video_for_repeat


def test_repeat_all_advances_and_wraps_in_library_order():
    videos = [
        VideoItem(id="v1", title="One", folder="A"),
        VideoItem(id="v2", title="Two", folder="B"),
        VideoItem(id="v3", title="Three", folder="A"),
    ]

    assert next_video_for_repeat(videos[0], videos, repeat_mode="all", shuffle=False) == videos[1]
    assert next_video_for_repeat(videos[2], videos, repeat_mode="all", shuffle=False) == videos[0]


def test_repeat_folder_advances_only_within_current_folder():
    videos = [
        VideoItem(id="v1", title="One", folder="A"),
        VideoItem(id="v2", title="Two", folder="B"),
        VideoItem(id="v3", title="Three", folder="A"),
    ]

    assert next_video_for_repeat(videos[0], videos, repeat_mode="folder", shuffle=False) == videos[2]
    assert next_video_for_repeat(videos[2], videos, repeat_mode="folder", shuffle=False) == videos[0]


def test_shuffle_chooses_from_distinct_videos_in_repeat_scope():
    videos = [
        VideoItem(id="v1", title="One", folder="A"),
        VideoItem(id="v2", title="Two", folder="A"),
        VideoItem(id="v3", title="Three", folder="B"),
    ]

    chosen = next_video_for_repeat(
        videos[0],
        videos,
        repeat_mode="folder",
        shuffle=True,
        choose=lambda options: options[-1],
    )

    assert chosen == videos[1]


def test_no_auto_advance_without_repeat_scope_or_distinct_candidate():
    videos = [VideoItem(id="v1", title="One", folder="A")]

    assert next_video_for_repeat(videos[0], videos, repeat_mode="none", shuffle=False) is None
    assert next_video_for_repeat(videos[0], videos, repeat_mode="one", shuffle=False) is None
    assert next_video_for_repeat(videos[0], videos, repeat_mode="all", shuffle=False) is None
