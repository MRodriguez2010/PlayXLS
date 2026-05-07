from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from playxls.runtime import find_executable
from playxls.transport import TransportSnapshot


@dataclass(frozen=True, slots=True)
class VideoProbeResult:
    ok: bool
    source: str
    mpv_path: str
    returncode: int | None
    message: str


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
        self.last_error = ""
        self._output_tail: list[str] = []
        self._output_thread: threading.Thread | None = None
        base_dir = ipc_dir or default_mpv_ipc_dir(self.mpv_path)
        base_dir.mkdir(parents=True, exist_ok=True)
        self.ipc_path = base_dir / f"playxls-mpv-{os.getpid()}-{id(self)}.sock"

    @property
    def available(self) -> bool:
        return self.mpv_path is not None

    def load(self, source: str, *, paused: bool = False, loop: bool = False, volume: int = 60, audio_normalize: bool = False) -> bool:
        self.last_error = ""
        self._output_tail = []
        if not self.available:
            self.last_error = "mpv executable not found"
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
            audio_normalize=audio_normalize,
        )
        try:
            self.process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        except OSError as exc:
            self.last_error = str(exc)
            return False
        self._start_output_reader()
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
            eof_reached=_bool_or_false(self.get_property("eof-reached")),
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
        process = self.process
        if process and process.poll() is None:
            self.command(["quit"])
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    try:
                        process.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        pass
        self._join_output_reader()
        self.process = None
        try:
            self.ipc_path.unlink()
        except FileNotFoundError:
            pass

    def _wait_for_socket(self) -> bool:
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if self.ipc_path.exists():
                return self._wait_for_load_result(deadline)
            if self.process and self.process.poll() is not None:
                self._join_output_reader()
                self.last_error = self._failure_message("mpv exited before playback started")
                return False
            time.sleep(0.02)
        ready = self.ipc_path.exists()
        if not ready:
            self.last_error = self._failure_message("Timed out waiting for mpv IPC")
        return ready

    def _wait_for_load_result(self, deadline: float) -> bool:
        while time.monotonic() < deadline:
            if self.process and self.process.poll() is not None:
                self._join_output_reader()
                self.last_error = self._failure_message("mpv exited before playback started")
                return False
            if _response_succeeded(self.request(["get_property", "path"])):
                return True
            if _response_succeeded(self.request(["get_property", "duration"])):
                return True
            idle = self.request(["get_property", "idle-active"])
            if idle and idle.get("error") == "success" and idle.get("data") is True and self._output_tail:
                self.last_error = self._failure_message("mpv did not start playback")
                return False
            time.sleep(0.05)
        self.last_error = self._failure_message("Timed out waiting for mpv playback")
        return False

    def _start_output_reader(self) -> None:
        if not self.process or self.process.stdout is None:
            return
        self._output_thread = threading.Thread(
            target=self._collect_output,
            args=(self.process.stdout,),
            name="playxls-mpv-output",
            daemon=True,
        )
        self._output_thread.start()

    def _collect_output(self, stream: TextIO) -> None:
        try:
            for line in stream:
                self._record_output_line(line)
        except ValueError:
            return

    def _record_output_line(self, line: str) -> None:
        line = line.strip()
        if not line or _is_noisy_output_line(line):
            return
        self._output_tail.append(line)
        del self._output_tail[:-80]

    def _join_output_reader(self) -> None:
        if self._output_thread and self._output_thread.is_alive():
            self._output_thread.join(timeout=0.2)
        self._output_thread = None

    def _failure_message(self, fallback: str) -> str:
        if not self._output_tail:
            return fallback
        return "\n".join(self._output_tail[-6:])

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


def probe_video_playback(source: str, *, timeout: float = 12) -> VideoProbeResult:
    mpv_path = find_executable("mpv")
    if not mpv_path:
        return VideoProbeResult(False, source, "", None, "mpv executable not found")
    args = build_mpv_probe_args(mpv_path, source)
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        message = _clean_probe_output(_timeout_output(exc)) or f"Timed out after {timeout:g}s"
        return VideoProbeResult(False, source, mpv_path, None, message)
    message = _clean_probe_output(f"{result.stdout}\n{result.stderr}")
    if result.returncode == 0:
        return VideoProbeResult(True, source, mpv_path, result.returncode, "mpv accepted the source")
    return VideoProbeResult(False, source, mpv_path, result.returncode, message or f"mpv exited with code {result.returncode}")


def build_mpv_probe_args(mpv_path: str, source: str) -> list[str]:
    return [
        mpv_path,
        "--no-config",
        "--msg-level=all=warn",
        "--force-window=no",
        "--vo=null",
        "--ao=null",
        "--frames=1",
        "--",
        source,
    ]


def build_mpv_args(
    mpv_path: str,
    source: str,
    *,
    ipc_path: Path,
    window_id: int | None,
    paused: bool,
    loop: bool,
    volume: int,
    audio_normalize: bool = False,
) -> list[str]:
    args = [
        mpv_path,
        "--msg-level=all=warn",
        "--force-window=yes",
        "--idle=yes",
        "--osc=no",
        "--osd-level=0",
        "--input-default-bindings=no",
        "--cache=yes",
        "--demuxer-max-bytes=256MiB",
        "--demuxer-readahead-secs=20",
        "--hwdec=auto-safe",
        "--scale=bilinear",
        "--dscale=bilinear",
        "--cscale=bilinear",
        "--correct-downscaling=no",
        "--linear-downscaling=no",
        "--cursor-autohide=always",
        f"--input-ipc-server={ipc_path}",
        f"--volume={volume}",
    ]
    if audio_normalize:
        args.append("--af=lavfi=[dynaudnorm=f=150:g=15]")
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


def _bool_or_false(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.casefold() in {"1", "true", "yes"}
    return bool(value)


def _response_succeeded(response: dict[str, Any] | None) -> bool:
    return bool(response and response.get("error") == "success" and response.get("data") not in (None, ""))


def _is_noisy_output_line(line: str) -> bool:
    if line.startswith("[ipc_") and "Write error" in line:
        return True
    return "GLib-GIO-CRITICAL" in line


def _clean_probe_output(output: str) -> str:
    lines = []
    for line in output.splitlines():
        line = line.strip()
        if line and not _is_noisy_output_line(line):
            lines.append(line)
    return "\n".join(lines[-6:])


def _timeout_output(exc: subprocess.TimeoutExpired) -> str:
    parts = []
    for value in (exc.stdout, exc.stderr):
        if isinstance(value, bytes):
            parts.append(value.decode("utf-8", errors="replace"))
        elif value:
            parts.append(str(value))
    return "\n".join(parts)
