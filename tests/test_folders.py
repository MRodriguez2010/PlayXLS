from pathlib import Path

from playxls.folders import FolderScanner
from playxls.models import FolderEntry


def test_folder_scanner_can_skip_startup_prime_when_seen_paths_are_supplied(monkeypatch, tmp_path: Path):
    def fail_if_called(path: str):
        raise AssertionError(f"unexpected synchronous scan of {path}")

    monkeypatch.setattr("playxls.folders._iter_video_files", fail_if_called)
    scanner = FolderScanner(
        [FolderEntry(id="f1", name="NAS", path=str(tmp_path), live=True)],
        lambda video: None,
        interval_seconds=999,
        seen_paths=[tmp_path / "known.mp4"],
    )

    scanner.start()
    scanner.stop()


def test_folder_scanner_refreshes_in_one_batch(monkeypatch, tmp_path: Path):
    video = tmp_path / "one.mp4"
    video.write_bytes(b"fake")
    added = []
    refreshed = []
    monkeypatch.setattr("playxls.folders._iter_video_files", lambda path: [video])
    scanner = FolderScanner(
        [FolderEntry(id="f1", name="NAS", path=str(tmp_path), live=True)],
        added.append,
        on_refreshed=refreshed.append,
    )

    scanner.scan_once()

    assert added == []
    assert refreshed[0]["folder_counts"] == {"f1": 1}
    assert [item.title for item in refreshed[0]["videos"]] == ["one"]
