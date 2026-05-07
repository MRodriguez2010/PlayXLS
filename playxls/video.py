from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

from playxls.runtime import find_executable
from playxls.transport import TransportSnapshot


class MpvController:
    """Small mpv subprocess adapter.

    The production target is libmpv. This adapter keeps the rest of the app on
    the same control surface while the local development image lacks libmpv
    headers.
    """

    def __init__(self, window_id: int | None = None, ipc_dir: Path | None = None) -> None:
        self.window_id = window_id
        self.process: subprocess.Popen[str] | None = None
        self.mpv_path = find_executable("mpv")
        base_dir = ipc_dir or default_mpv_ipc_dir(self.mpv_path)
        base_dir.mkdir(parents=True, exist_ok=True)
        self.ipc_path = base_dir / f"playxls-mpv-{os.getpid()}-{id(self)}.sock"

    @property
    def available(self) -> bool:
        return self.mpv_path is not None

    def load(self, source: str, *, paused: bool = False, loop: bool = False, volume: int = 60) -> bool:
        if not self.available:
            return False
        self.stop()
        args = build_mpv_args(
            self.mpv_path or "mpv",
            source,
            ipc_path=self.ipc_path,
            window_id=self.window_id,
            paused=paused,
            loop=loop,
            volume=volume,
        )
        self.process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        return self._wait_for_socket()

    def command(self, command: list[Any]) -> bool:
        if not self.process or self.process.poll() is not None or not self.ipc_path.exists():
            return False
        payload = json.dumps({"command": command}).encode("utf-8") + b"\n"
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                sock.connect(str(self.ipc_path))
                sock.sendall(payload)
            return True
        except OSError:
            return False

    def request(self, command: list[Any]) -> dict[str, Any] | None:
        if not self.process or self.process.poll() is not None or not self.ipc_path.exists():
            return None
        payload = json.dumps({"command": command}).encode("utf-8") + b"\n"
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.25)
                sock.connect(str(self.ipc_path))
                sock.sendall(payload)
                raw = b""
                while not raw.endswith(b"\n"):
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    raw += chunk
            if not raw:
                return None
            first_line = raw.splitlines()[0]
            response = json.loads(first_line.decode("utf-8"))
            return response if isinstance(response, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def get_property(self, name: str) -> Any | None:
        response = self.request(["get_property", name])
        if not response or response.get("error") != "success":
            return None
        return response.get("data")

    def transport_snapshot(self) -> TransportSnapshot:
        return TransportSnapshot(
            position=_float_or_none(self.get_property("time-pos")),
            duration=_float_or_none(self.get_property("duration")),
            paused=bool(self.get_property("pause")),
        )

    def seek_absolute(self, seconds: float) -> None:
        self.command(["seek", max(0.0, float(seconds)), "absolute+exact"])

    def set_volume(self, volume: float) -> None:
        self.command(["set_property", "volume", max(0, min(100, int(volume * 100)))])

    def set_pause(self, paused: bool) -> None:
        self.command(["set_property", "pause", paused])

    def set_loop_file(self, enabled: bool) -> None:
        self.command(["set_property", "loop-file", "inf" if enabled else "no"])

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.command(["quit"])
            try:
                self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
        self.process = None
        try:
            self.ipc_path.unlink()
        except FileNotFoundError:
            pass

    def _wait_for_socket(self) -> bool:
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if self.ipc_path.exists():
                return True
            if self.process and self.process.poll() is not None:
                return False
            time.sleep(0.02)
        return self.ipc_path.exists()

    def __del__(self) -> None:
        self.stop()


def resolve_stream_url(url: str) -> str:
    """Resolve stream URLs through available CLI helpers when possible."""

    streamlink = find_executable("streamlink")
    if streamlink:
        try:
            result = subprocess.run([streamlink, "--stream-url", url, "best"], check=True, text=True, capture_output=True, timeout=12)
            resolved = result.stdout.strip()
            if resolved:
                return resolved
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    ytdlp = find_executable("yt-dlp")
    if ytdlp:
        try:
            result = subprocess.run([ytdlp, "-g", url], check=True, text=True, capture_output=True, timeout=12)
            resolved = result.stdout.splitlines()[0].strip()
            if resolved:
                return resolved
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, IndexError):
            pass
    return url


def build_mpv_args(
    mpv_path: str,
    source: str,
    *,
    ipc_path: Path,
    window_id: int | None,
    paused: bool,
    loop: bool,
    volume: int,
) -> list[str]:
    args = [
        mpv_path,
        "--no-terminal",
        "--force-window=yes",
        "--idle=yes",
        "--osc=no",
        "--osd-level=0",
        "--input-default-bindings=no",
        "--cursor-autohide=always",
        f"--input-ipc-server={ipc_path}",
        f"--volume={volume}",
    ]
    if window_id is not None:
        args.append(f"--wid={window_id}")
    if paused:
        args.append("--pause")
    if loop:
        args.append("--loop-file=inf")
    args.append(source)
    return args


def default_mpv_ipc_dir(mpv_path: str | None) -> Path:
    if mpv_path and Path(mpv_path).as_posix().startswith("/snap/"):
        return Path.home() / "PlayXLS Runtime" / "mpv-ipc"
    return Path.home() / ".cache" / "playxls" / "mpv-ipc"


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
