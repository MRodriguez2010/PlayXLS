from __future__ import annotations

import json
import os
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import tomli_w

from playxls.layout import LayoutDefinition, layout_from_dict, layout_to_dict
from playxls.models import AppSettings, BrowserPreset, DEFAULT_BROWSER_PRESETS, DEFAULT_FOLDERS, DEFAULT_KEYBINDINGS, FolderEntry, KeyBinding, SessionState, VideoItem


class ConfigStore:
    """Persistence for PlayXLS' human-editable config files."""

    def __init__(self, config_dir: Path | None = None, cache_dir: Path | None = None, state_dir: Path | None = None) -> None:
        home = Path.home()
        self.config_dir = config_dir or Path(os.environ.get("PLAYXLS_CONFIG_DIR", home / ".config" / "playxls"))
        self.cache_dir = cache_dir or Path(os.environ.get("PLAYXLS_CACHE_DIR", home / ".cache" / "playxls"))
        self.state_dir = state_dir or Path(os.environ.get("PLAYXLS_STATE_DIR", home / ".local" / "state" / "playxls"))

    @property
    def settings_path(self) -> Path:
        return self.config_dir / "settings.toml"

    @property
    def layouts_path(self) -> Path:
        return self.config_dir / "layouts.toml"

    @property
    def bindings_path(self) -> Path:
        return self.config_dir / "bindings.toml"

    @property
    def watch_folders_path(self) -> Path:
        return self.config_dir / "watch_folders.toml"

    @property
    def browser_presets_path(self) -> Path:
        return self.config_dir / "browser_presets.toml"

    @property
    def ignored_videos_path(self) -> Path:
        return self.config_dir / "ignored_videos.toml"

    @property
    def library_index_path(self) -> Path:
        return self.cache_dir / "library_index.toml"

    @property
    def session_path(self) -> Path:
        return self.config_dir / "sessions" / "default.toml"

    @property
    def log_path(self) -> Path:
        return self.state_dir / "playxls.log"

    @property
    def playback_diagnostics_path(self) -> Path:
        return self.state_dir / "playback-diagnostics.jsonl"

    def ensure_dirs(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        (self.config_dir / "sessions").mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "thumbs").mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "browser").mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def append_playback_diagnostic(self, event: dict[str, Any]) -> bool:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **event,
        }
        try:
            self.ensure_dirs()
            with self.playback_diagnostics_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
        except OSError:
            return False
        return True

    def load_settings(self) -> AppSettings:
        data = self._read_toml(self.settings_path)
        return AppSettings.from_dict(data.get("settings", data))

    def save_settings(self, settings: AppSettings) -> None:
        self._write_toml(self.settings_path, {"settings": settings.to_dict()})

    def load_layouts(self) -> list[LayoutDefinition]:
        data = self._read_toml(self.layouts_path)
        layouts: list[LayoutDefinition] = []
        for item in data.get("layouts", []):
            try:
                tree_data = json.loads(str(item.get("tree_json", "{\"type\":\"leaf\"}")))
                layouts.append(
                    LayoutDefinition(
                        id=str(item.get("id", "")),
                        label=str(item.get("label", "Custom")),
                        tree=layout_from_dict(tree_data),
                        custom=bool(item.get("custom", True)),
                    )
                )
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return [layout for layout in layouts if layout.id]

    def save_layouts(self, layouts: list[LayoutDefinition]) -> None:
        payload = []
        for layout in layouts:
            payload.append(
                {
                    "id": layout.id,
                    "label": layout.label,
                    "custom": layout.custom,
                    "tree_json": json.dumps(layout_to_dict(layout.tree), separators=(",", ":")),
                }
            )
        self._write_toml(self.layouts_path, {"layouts": payload})

    def load_bindings(self) -> list[KeyBinding]:
        data = self._read_toml(self.bindings_path)
        bindings = [KeyBinding.from_dict(item) for item in data.get("bindings", []) if isinstance(item, dict)]
        return bindings or list(DEFAULT_KEYBINDINGS)

    def save_bindings(self, bindings: list[KeyBinding]) -> None:
        self._write_toml(self.bindings_path, {"bindings": [binding.to_dict() for binding in bindings]})

    def load_watch_folders(self) -> list[FolderEntry]:
        data = self._read_toml(self.watch_folders_path)
        folders = [FolderEntry.from_dict(item) for item in data.get("folders", []) if isinstance(item, dict)]
        return folders or list(DEFAULT_FOLDERS)

    def save_watch_folders(self, folders: list[FolderEntry]) -> None:
        self._write_toml(self.watch_folders_path, {"folders": [folder.to_dict() for folder in folders]})

    def load_browser_presets(self) -> list[BrowserPreset]:
        if not self.browser_presets_path.exists():
            return list(DEFAULT_BROWSER_PRESETS)
        data = self._read_toml(self.browser_presets_path)
        return [
            preset
            for preset in (BrowserPreset.from_dict(item) for item in data.get("presets", []) if isinstance(item, dict))
            if preset.id and preset.name and preset.url
        ]

    def save_browser_presets(self, presets: list[BrowserPreset]) -> None:
        self._write_toml(self.browser_presets_path, {"presets": [preset.to_dict() for preset in presets]})

    def load_ignored_video_paths(self) -> set[str]:
        data = self._read_toml(self.ignored_videos_path)
        return {str(path) for path in data.get("paths", []) if str(path).strip()}

    def save_ignored_video_paths(self, paths: set[str]) -> None:
        self._write_toml(self.ignored_videos_path, {"paths": sorted(paths)})

    def load_library_index(self) -> list[VideoItem]:
        data = self._read_toml(self.library_index_path)
        videos: list[VideoItem] = []
        for item in data.get("videos", []):
            if not isinstance(item, dict):
                continue
            video = _video_from_dict(item)
            if video.path or video.src:
                videos.append(video)
        return videos

    def save_library_index(self, videos: list[VideoItem]) -> None:
        self._write_toml(self.library_index_path, {"videos": [_video_to_dict(video) for video in videos]})

    def load_session(self) -> SessionState:
        data = self._read_toml(self.session_path)
        return SessionState.from_dict(data.get("session", data))

    def save_session(self, session: SessionState) -> None:
        self._write_toml(self.session_path, {"session": session.to_dict()})

    def _read_toml(self, path: Path) -> dict[str, Any]:
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except FileNotFoundError:
            return {}
        except tomllib.TOMLDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _write_toml(self, path: Path, data: dict[str, Any]) -> None:
        self.ensure_dirs()
        with path.open("wb") as handle:
            tomli_w.dump(data, handle)


def _video_from_dict(data: dict[str, Any]) -> VideoItem:
    return VideoItem(
        id=str(data.get("id", "")),
        title=str(data.get("title", "")),
        duration=str(data.get("duration", "--:--")),
        folder=str(data.get("folder", "Local")),
        path=str(data.get("path", "")),
        src=str(data.get("src", "")),
    )


def _video_to_dict(video: VideoItem) -> dict[str, Any]:
    return {
        "id": video.id,
        "title": video.title,
        "duration": video.duration,
        "folder": video.folder,
        "path": video.path,
        "src": video.src,
    }
