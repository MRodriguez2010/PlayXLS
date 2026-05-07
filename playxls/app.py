from __future__ import annotations

import argparse
import ctypes.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from playxls import __version__
from playxls.config import ConfigStore
from playxls.runtime import find_executable


@dataclass(frozen=True, slots=True)
class QtLaunchDecision:
    ok: bool
    platform: str
    message: str = ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="playxls", description="PlayXLS native multi-stream video player.")
    parser.add_argument("videos", nargs="*", help="Video files or stream URLs to load at startup.")
    parser.add_argument("--diagnose", action="store_true", help="Print local dependency diagnostics and exit.")
    parser.add_argument("--version", action="version", version=f"PlayXLS {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = ConfigStore()
    store.ensure_dirs()
    if args.diagnose:
        return diagnose(store)

    decision = choose_qt_platform(os.environ)
    if not decision.ok:
        print(decision.message, file=sys.stderr)
        return 2
    if decision.platform and "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = decision.platform

    try:
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication

        from playxls.assets import app_icon_path
        from playxls.ui.main_window import MainWindow, build_state
    except ModuleNotFoundError as exc:
        missing = exc.name or "PySide6"
        print(
            f"PlayXLS GUI dependency is missing: {missing}\n"
            "Install it with: .venv/bin/pip install -e '.[gui]'\n"
            "Core modules and tests do not require the GUI extra.",
            file=sys.stderr,
        )
        return 2

    app = QApplication(sys.argv[:1] + (argv or sys.argv[1:]))
    app.setApplicationName("PlayXLS")
    app.setOrganizationName("PlayXLS")
    icon_path = app_icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    state, layouts = build_state(args.videos, store)
    window = MainWindow(state, layouts, store)
    window.show()
    return app.exec()


def choose_qt_platform(
    env: Mapping[str, str],
    find_library: Callable[[str], str | None] = ctypes.util.find_library,
) -> QtLaunchDecision:
    explicit = env.get("QT_QPA_PLATFORM")
    if explicit:
        return QtLaunchDecision(True, explicit)

    wayland_available = bool(env.get("WAYLAND_DISPLAY")) and bool(find_library("wayland-client"))
    if env.get("DISPLAY"):
        if find_library("xcb-cursor"):
            return QtLaunchDecision(True, "xcb")
        if wayland_available:
            return QtLaunchDecision(True, "wayland")
        return QtLaunchDecision(
            False,
            "xcb",
            "PlayXLS cannot start the Qt X11 backend because libxcb-cursor0 is missing.\n"
            "Install the system package, then launch again:\n"
            "  sudo apt install libxcb-cursor0\n"
            "Alternative for Wayland sessions:\n"
            "  QT_QPA_PLATFORM=wayland .venv/bin/playxls",
        )

    if wayland_available:
        return QtLaunchDecision(True, "wayland")

    return QtLaunchDecision(
        False,
        "",
        "PlayXLS could not find a graphical display. Start it from an X11/Wayland session, "
        "or run with QT_QPA_PLATFORM=offscreen only for non-interactive smoke tests.",
    )


def diagnose(store: ConfigStore) -> int:
    print(f"PlayXLS {__version__}")
    print(f"config: {store.config_dir}")
    print(f"cache:  {store.cache_dir}")
    print(f"state:  {store.state_dir}")
    print(f"mpv:    {find_executable('mpv') or 'missing'}")
    print(f"streamlink: {find_executable('streamlink') or 'missing'}")
    print(f"yt-dlp:     {find_executable('yt-dlp') or 'missing'}")
    print(f"xcb-cursor: {ctypes.util.find_library('xcb-cursor') or 'missing'}")
    print(f"wayland-client: {ctypes.util.find_library('wayland-client') or 'missing'}")
    decision = choose_qt_platform(os.environ)
    print(f"Qt platform: {decision.platform or 'unavailable'}")
    if not decision.ok:
        print(decision.message)
    try:
        import PySide6  # noqa: F401

        print("PySide6: installed")
    except ModuleNotFoundError:
        print("PySide6: missing")
    try:
        import PySide6.QtWebEngineWidgets  # noqa: F401

        print("QtWebEngine: installed")
    except ModuleNotFoundError:
        print("QtWebEngine: missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
