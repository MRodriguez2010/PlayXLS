import json
import zipfile

from playxls.app import QtLaunchDecision, build_parser, choose_qt_platform, main
from playxls.config import ConfigStore
from playxls.video import VideoProbeResult


def test_choose_qt_platform_keeps_explicit_platform():
    decision = choose_qt_platform(
        {"QT_QPA_PLATFORM": "offscreen", "DISPLAY": ":1", "XDG_SESSION_TYPE": "x11"},
        find_library=lambda name: None,
    )

    assert decision == QtLaunchDecision(ok=True, platform="offscreen", message="")


def test_choose_qt_platform_blocks_x11_without_xcb_cursor():
    decision = choose_qt_platform(
        {"DISPLAY": ":1", "XDG_SESSION_TYPE": "x11"},
        find_library=lambda name: "libxcb.so.1" if name == "xcb" else None,
    )

    assert decision.ok is False
    assert decision.platform == "xcb"
    assert "libxcb-cursor0" in decision.message


def test_choose_qt_platform_prefers_xcb_on_wayland_when_available_for_mpv_embedding():
    decision = choose_qt_platform(
        {"DISPLAY": ":1", "WAYLAND_DISPLAY": "wayland-0", "XDG_SESSION_TYPE": "wayland"},
        find_library=lambda name: {
            "xcb-cursor": "libxcb-cursor.so.0",
            "wayland-client": "libwayland-client.so.0",
        }.get(name),
    )

    assert decision == QtLaunchDecision(ok=True, platform="xcb", message="")


def test_choose_qt_platform_prefers_wayland_when_available_and_xcb_cursor_missing():
    decision = choose_qt_platform(
        {"DISPLAY": ":1", "WAYLAND_DISPLAY": "wayland-0", "XDG_SESSION_TYPE": "wayland"},
        find_library=lambda name: "libwayland-client.so.0" if name == "wayland-client" else None,
    )

    assert decision == QtLaunchDecision(ok=True, platform="wayland", message="")


def test_export_diagnostics_writes_zip_without_starting_gui(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PLAYXLS_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("PLAYXLS_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PLAYXLS_STATE_DIR", str(tmp_path / "state"))
    store = ConfigStore()
    store.save_settings(store.load_settings())
    store.append_playback_diagnostic({"kind": "video_load_failed", "message": "BadWindow"})
    output = tmp_path / "playxls-diagnostics.zip"

    result = main(["--export-diagnostics", str(output)])

    assert result == 0
    assert str(output) in capsys.readouterr().out
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "diagnose.txt" in names
        assert "manifest.json" in names
        assert "config/settings.toml" in names
        assert "state/playback-diagnostics.jsonl" in names
        assert "cache/library_index.toml" not in names
        assert "PlayXLS" in archive.read("diagnose.txt").decode()
        playback_records = [json.loads(line) for line in archive.read("state/playback-diagnostics.jsonl").decode().splitlines()]
        assert playback_records[0]["message"] == "BadWindow"


def test_probe_video_cli_reports_success_without_starting_gui(monkeypatch, capsys):
    monkeypatch.setattr(
        "playxls.app.probe_video_playback",
        lambda source: VideoProbeResult(ok=True, source=source, mpv_path="/usr/bin/mpv", returncode=0, message="mpv accepted the source"),
    )

    result = main(["--probe-video", "/nas/movie.mkv"])

    assert result == 0
    output = capsys.readouterr().out
    assert "Playback probe: OK" in output
    assert "mpv accepted the source" in output


def test_probe_video_cli_reports_failure_without_starting_gui(monkeypatch, capsys):
    monkeypatch.setattr(
        "playxls.app.probe_video_playback",
        lambda source: VideoProbeResult(ok=False, source=source, mpv_path="/usr/bin/mpv", returncode=2, message="No playable streams"),
    )

    result = main(["--probe-video", "/nas/broken.mkv"])

    assert result == 1
    output = capsys.readouterr().out
    assert "Playback probe: FAILED" in output
    assert "No playable streams" in output


def test_parser_accepts_safe_mode_for_recovery_launches():
    args = build_parser().parse_args(["--safe-mode"])

    assert args.safe_mode is True
