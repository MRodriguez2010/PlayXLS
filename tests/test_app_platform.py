from playxls.app import QtLaunchDecision, choose_qt_platform


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
