import json
import zipfile

from playxls.app import QtLaunchDecision, choose_qt_platform, main
from playxls.config import ConfigStore


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
