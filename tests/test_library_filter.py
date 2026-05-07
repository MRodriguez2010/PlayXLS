from playxls.models import VideoItem
from playxls.ui.panels import filter_videos, library_folder_filters


def test_library_folder_filters_include_all_and_unique_folders():
    videos = [
        VideoItem(id="v1", title="One", folder="Watch Me"),
        VideoItem(id="v2", title="Two", folder="Watch Me"),
        VideoItem(id="v3", title="Three", folder="Other"),
    ]

    assert library_folder_filters(videos) == ["all", "Other", "Watch Me"]


def test_filter_videos_applies_search_and_folder():
    videos = [
        VideoItem(id="v1", title="Guitarist Playing", folder="Watch Me"),
        VideoItem(id="v2", title="Earth Rotation", folder="Watch Me"),
        VideoItem(id="v3", title="Invoice", folder="Other"),
    ]

    assert [video.title for video in filter_videos(videos, query="earth", folder="Watch Me")] == ["Earth Rotation"]
    assert [video.title for video in filter_videos(videos, query="", folder="Other")] == ["Invoice"]
    assert [video.title for video in filter_videos(videos, query="", folder="all")] == [
        "Guitarist Playing",
        "Earth Rotation",
        "Invoice",
    ]
