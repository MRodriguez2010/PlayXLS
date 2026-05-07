from __future__ import annotations

import argparse
import ctypes.util
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping
from zipfile import ZIP_DEFLATED, ZipFile

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
    parser.add_argument(
        "--export-diagnostics",
        nargs="?",
        const="",
        metavar="ZIP",
        help="Write a PlayXLS diagnostics zip and exit. Defaults to the PlayXLS state directory.",
    )
    parser.add_argument("--version", action="version", version=f"PlayXLS {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = ConfigStore()
    store.ensure_dirs()
    if args.diagnose:
        return diagnose(store)
    if args.export_diagnostics is not None:
        output = Path(args.export_diagnostics).expanduser() if args.export_diagnostics else None
        bundle = export_diagnostics(store, output)
        print(f"Diagnostics exported: {bundle}")
        return 0

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
    print(diagnostics_report(store))
    return 0


def diagnostics_report(store: ConfigStore) -> str:
    lines = [
        f"PlayXLS {__version__}",
        f"config: {store.config_dir}",
        f"cache:  {store.cache_dir}",
        f"state:  {store.state_dir}",
        f"mpv:    {find_executable('mpv') or 'missing'}",
        f"streamlink: {find_executable('streamlink') or 'missing'}",
        f"yt-dlp:     {find_executable('yt-dlp') or 'missing'}",
        f"xcb-cursor: {ctypes.util.find_library('xcb-cursor') or 'missing'}",
        f"wayland-client: {ctypes.util.find_library('wayland-client') or 'missing'}",
    ]
    decision = choose_qt_platform(os.environ)
    lines.append(f"Qt platform: {decision.platform or 'unavailable'}")
    if not decision.ok:
        lines.append(decision.message)
    try:
        import PySide6  # noqa: F401

        lines.append("PySide6: installed")
    except ModuleNotFoundError:
        lines.append("PySide6: missing")
    try:
        import PySide6.QtWebEngineWidgets  # noqa: F401

        lines.append("QtWebEngine: installed")
    except ModuleNotFoundError:
        lines.append("QtWebEngine: missing")
    return "\n".join(lines) + "\n"


def export_diagnostics(store: ConfigStore, output_path: Path | None = None) -> Path:
    store.ensure_dirs()
    target = output_path or _default_diagnostics_bundle_path(store)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
        "config_dir": str(store.config_dir),
        "cache_dir": str(store.cache_dir),
        "state_dir": str(store.state_dir),
        "notes": "Cache indexes and browser profile data are intentionally excluded.",
    }
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        archive.writestr("diagnose.txt", diagnostics_report(store))
        for path, archive_name in _diagnostics_file_map(store):
            if path.exists() and path.is_file():
                archive.write(path, archive_name)
    return target


def _default_diagnostics_bundle_path(store: ConfigStore) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return store.state_dir / f"playxls-diagnostics-{stamp}.zip"


def _diagnostics_file_map(store: ConfigStore) -> list[tuple[Path, str]]:
    return [
        (store.settings_path, "config/settings.toml"),
        (store.layouts_path, "config/layouts.toml"),
        (store.bindings_path, "config/bindings.toml"),
        (store.watch_folders_path, "config/watch_folders.toml"),
        (store.browser_presets_path, "config/browser_presets.toml"),
        (store.ignored_videos_path, "config/ignored_videos.toml"),
        (store.session_path, "config/sessions/default.toml"),
        (store.log_path, "state/playxls.log"),
        (store.playback_diagnostics_path, "state/playback-diagnostics.jsonl"),
    ]


if __name__ == "__main__":
    raise SystemExit(main())
