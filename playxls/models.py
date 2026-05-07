from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


ThemeName = Literal["dark", "light", "system"]
BorderMode = Literal["always", "hover", "never"]
HoverVolumeMode = Literal["boost", "duck"]
PreviewMode = Literal["off", "lazy", "thumb"]
SeekSyncMode = Literal["disabled", "soft", "hard"]
BrowserProfileScope = Literal["shared", "per_cell"]
RepeatMode = Literal["none", "one", "all", "folder"]


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".webm",
    ".m4v",
    ".ts",
    ".m2ts",
    ".flv",
    ".wmv",
}


@dataclass(slots=True)
class AppSettings:
    theme: ThemeName = "dark"
    border_mode: BorderMode = "hover"
    expand_on_hover: bool = True
    expand_percent: int = 140
    volume_on_hover: bool = True
    hover_volume_mode: HoverVolumeMode = "boost"
    hover_volume_amount: int = 40
    pause_on_minimize: bool = True
    disable_screensaver: bool = True
    save_playback_position: bool = True
    seek_sync_mode: SeekSyncMode = "disabled"
    preview_mode: PreviewMode = "lazy"
    preview_delay: int = 300
    preview_mute: bool = True
    preview_cache_size: int = 5
    browser_profile_scope: BrowserProfileScope = "shared"
    hw_acceleration: str = "auto"
    logging_level: str = "info"

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AppSettings":
        defaults = asdict(cls())
        if not data:
            return cls()
        clean = {key: data[key] for key in defaults if key in data}
        merged = {**defaults, **clean}
        merged["expand_percent"] = _clamp_int(merged["expand_percent"], 105, 200)
        merged["hover_volume_amount"] = _clamp_int(merged["hover_volume_amount"], 10, 80)
        merged["preview_delay"] = _clamp_int(merged["preview_delay"], 0, 2000)
        merged["preview_cache_size"] = _clamp_int(merged["preview_cache_size"], 1, 20)
        return cls(**merged)

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(slots=True)
class VideoItem:
    id: str
    title: str
    duration: str = "--:--"
    folder: str = "Local"
    path: str = ""
    src: str = ""

    @classmethod
    def from_path(cls, path: str | Path, index: int = 0) -> "VideoItem":
        p = Path(path).expanduser()
        return cls(id=f"cli-{index}-{p.stem}", title=p.stem, folder=p.parent.name or "Local", path=str(p), src=str(p))


@dataclass(slots=True)
class FolderEntry:
    id: str
    name: str
    path: str
    count: int = 0
    live: bool = True
    polled_seconds_ago: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FolderEntry":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            path=str(data.get("path", "")),
            count=int(data.get("count", 0)),
            live=bool(data.get("live", True)),
            polled_seconds_ago=int(data.get("polled_seconds_ago", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(slots=True)
class BrowserPreset:
    id: str
    name: str
    url: str
    color: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrowserPreset":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            url=str(data.get("url", "")),
            color=str(data.get("color", "#fbbf24")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class KeyBinding:
    id: str
    action: str
    combo: str
    type: str = "key"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KeyBinding":
        return cls(
            id=str(data.get("id", "")),
            action=str(data.get("action", "")),
            combo=str(data.get("combo", "")),
            type=str(data.get("type", "key")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CellContent:
    kind: Literal["empty", "video", "browser"] = "empty"
    video_id: str | None = None
    url: str | None = None
    name: str | None = None

    @classmethod
    def empty(cls) -> "CellContent":
        return cls("empty")

    @classmethod
    def video(cls, video_id: str) -> "CellContent":
        return cls("video", video_id=video_id)

    @classmethod
    def browser(cls, url: str, name: str) -> "CellContent":
        return cls("browser", url=url, name=name)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CellContent":
        kind = str(data.get("kind", "empty"))
        if kind == "video":
            return cls.video(str(data.get("video_id", "")))
        if kind == "browser":
            return cls.browser(str(data.get("url", "")), str(data.get("name", "")))
        return cls.empty()

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(slots=True)
class SessionState:
    layout_id: str = "2x2"
    cell_content: list[CellContent] = field(default_factory=lambda: [CellContent.empty() for _ in range(20)])
    master_volume: float = 0.6
    muted: bool = False
    repeat_mode: RepeatMode = "none"
    shuffle: bool = False
    playback_positions: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SessionState":
        if not data:
            return cls()
        raw_cells = data.get("cell_content", [])
        cells = [CellContent.from_dict(item) for item in raw_cells if isinstance(item, dict)]
        if not cells:
            cells = [CellContent.empty() for _ in range(20)]
        try:
            master_volume = float(data.get("master_volume", 0.6))
        except (TypeError, ValueError):
            master_volume = 0.6
        raw_positions = data.get("playback_positions", {})
        playback_positions: dict[str, float] = {}
        if isinstance(raw_positions, dict):
            for key, value in raw_positions.items():
                try:
                    seconds = float(value)
                except (TypeError, ValueError):
                    continue
                if seconds > 0:
                    playback_positions[str(key)] = seconds
        return cls(
            layout_id=str(data.get("layout_id", "2x2")),
            cell_content=cells,
            master_volume=max(0.0, min(1.0, master_volume)),
            muted=bool(data.get("muted", False)),
            repeat_mode=_coerce_repeat_mode(data.get("repeat_mode")),
            shuffle=bool(data.get("shuffle", False)),
            playback_positions=playback_positions,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "layout_id": self.layout_id,
            "cell_content": [content.to_dict() for content in self.cell_content],
            "master_volume": self.master_volume,
            "muted": self.muted,
            "repeat_mode": self.repeat_mode,
            "shuffle": self.shuffle,
            "playback_positions": self.playback_positions,
        }


@dataclass(slots=True)
class AppState:
    settings: AppSettings = field(default_factory=AppSettings)
    layout_id: str = "2x2"
    cell_content: list[CellContent] = field(default_factory=lambda: [CellContent.empty() for _ in range(20)])
    library_videos: list[VideoItem] = field(default_factory=list)
    folders: list[FolderEntry] = field(default_factory=lambda: list(DEFAULT_FOLDERS))
    browser_presets: list[BrowserPreset] = field(default_factory=lambda: list(DEFAULT_BROWSER_PRESETS))
    ignored_video_paths: set[str] = field(default_factory=set)
    playback_positions: dict[str, float] = field(default_factory=dict)
    bindings: list[KeyBinding] = field(default_factory=lambda: list(DEFAULT_KEYBINDINGS))
    playing: bool = True
    master_volume: float = 0.6
    muted: bool = False
    repeat_mode: RepeatMode = "none"
    shuffle: bool = False

    def ensure_cell_capacity(self, count: int) -> None:
        if len(self.cell_content) < count:
            self.cell_content.extend(CellContent.empty() for _ in range(count - len(self.cell_content)))

    def apply_session(self, session: SessionState) -> None:
        self.layout_id = session.layout_id
        self.cell_content = list(session.cell_content)
        self.ensure_cell_capacity(20)
        self.master_volume = session.master_volume
        self.muted = session.muted
        self.repeat_mode = session.repeat_mode
        self.shuffle = session.shuffle
        self.playback_positions = dict(session.playback_positions)

    def to_session(self) -> SessionState:
        return SessionState(
            layout_id=self.layout_id,
            cell_content=list(self.cell_content),
            master_volume=self.master_volume,
            muted=self.muted,
            repeat_mode=self.repeat_mode,
            shuffle=self.shuffle,
            playback_positions=dict(self.playback_positions),
        )


DEFAULT_BROWSER_PRESETS = [
    BrowserPreset("yt", "YouTube", "https://youtube.com", "#ff0000"),
    BrowserPreset("tw", "Twitch", "https://twitch.tv", "#9146ff"),
    BrowserPreset("nf", "Netflix", "https://netflix.com", "#e50914"),
    BrowserPreset("pr", "Prime Video", "https://primevideo.com", "#00a8e1"),
    BrowserPreset("dp", "Disney+", "https://disneyplus.com", "#0e47ba"),
    BrowserPreset("hb", "HBO Max", "https://max.com", "#9b50ff"),
    BrowserPreset("ku", "Kick", "https://kick.com", "#53fc18"),
    BrowserPreset("vm", "Vimeo", "https://vimeo.com", "#1ab7ea"),
]


DEFAULT_KEYBINDINGS = [
    KeyBinding("kb1", "Play / Pause", "Space", "key"),
    KeyBinding("kb2", "Toggle Grid Borders", "B", "key"),
    KeyBinding("kb3", "Cycle Grid Layout", "G", "key"),
    KeyBinding("kb4", "Mute Hovered", "M", "key"),
    KeyBinding("kb5", "Open Grid Editor", "Ctrl+E", "key"),
    KeyBinding("kb6", "Open Settings", "Ctrl+,", "key"),
    KeyBinding("kb7", "Cell Fullscreen", "F", "key"),
    KeyBinding("kb8", "Toggle Theme", "Ctrl+T", "key"),
]


SAMPLE_VIDEOS = [
    VideoItem("v1", "Big Buck Bunny", "9:56", "Animations", src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"),
    VideoItem("v2", "Elephant Dream", "10:53", "Animations", src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4"),
    VideoItem("v3", "For Bigger Blazes", "0:15", "Trailers", src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"),
    VideoItem("v4", "For Bigger Escape", "0:15", "Trailers", src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"),
    VideoItem("v5", "For Bigger Fun", "1:00", "Trailers", src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4"),
    VideoItem("v6", "For Bigger Joyrides", "0:15", "Trailers", src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4"),
    VideoItem("v7", "For Bigger Meltdowns", "0:15", "Trailers", src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4"),
    VideoItem("v8", "Sintel", "14:48", "Animations", src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4"),
    VideoItem("v9", "Tears of Steel", "12:14", "Sci-Fi", src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4"),
]


DEFAULT_FOLDERS: list[FolderEntry] = []


def _clamp_int(value: Any, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = low
    return max(low, min(high, number))


def _coerce_repeat_mode(value: Any) -> RepeatMode:
    mode = str(value or "none")
    if mode in {"none", "one", "all", "folder"}:
        return mode  # type: ignore[return-value]
    return "none"
