from pathlib import Path
import io
import json
import socket
import subprocess
import threading

import playxls.video as video_module
from playxls.video import MpvController, default_mpv_ipc_dir, probe_video_playback


def test_mpv_controller_uses_supplied_ipc_directory(tmp_path: Path):
    controller = MpvController(ipc_dir=tmp_path)

    assert controller.ipc_path.parent == tmp_path
    assert controller.ipc_path.name.startswith("playxls-mpv-")


def test_default_mpv_ipc_dir_is_snap_accessible():
    path = default_mpv_ipc_dir("/snap/bin/mpv")

    assert path == Path.home() / "PlayXLS Runtime" / "mpv-ipc"


def test_mpv_controller_reads_ipc_response(tmp_path: Path):
    response = controller_response(tmp_path, b'{"error":"success","data":42.5}\n')

    assert response == {"error": "success", "data": 42.5}


def test_mpv_controller_reads_first_ipc_response_line(tmp_path: Path):
    response = controller_response(
        tmp_path,
        b'{"error":"success","data":12}\n{"event":"property-change","name":"time-pos"}\n',
    )

    assert response == {"error": "success", "data": 12}


def test_embedded_mpv_args_disable_per_cell_ui(tmp_path: Path):
    assert callable(getattr(video_module, "build_mpv_args", None))

    args = video_module.build_mpv_args(
        "mpv",
        "movie.mp4",
        ipc_path=tmp_path / "mpv.sock",
        window_id=123,
        paused=False,
        loop=False,
        volume=60,
    )

    assert "--osc=no" in args
    assert "--osd-level=0" in args
    assert "--input-default-bindings=no" in args
    assert "--wid=123" in args


def test_embedded_mpv_args_keep_loader_output_available_for_diagnostics(tmp_path: Path):
    args = video_module.build_mpv_args(
        "mpv",
        "broken://movie",
        ipc_path=tmp_path / "mpv.sock",
        window_id=123,
        paused=False,
        loop=False,
        volume=60,
    )

    assert "--no-terminal" not in args
    assert "--msg-level=all=warn" in args


def test_mpv_controller_captures_output_when_load_exits_before_ipc(monkeypatch, tmp_path: Path):
    popen_calls = []

    class FailedProcess:
        def __init__(self, args, stdout=None, stderr=None, text=None) -> None:
            popen_calls.append({"args": args, "stdout": stdout, "stderr": stderr, "text": text})
            self.stdout = io.StringIO("No protocol handler found\nExiting... (Errors when loading file)\n")

        def poll(self):
            return 2

        def wait(self, timeout=None):
            return 2

        def terminate(self):
            return None

    monkeypatch.setattr(video_module, "find_executable", lambda name: "/usr/bin/mpv")
    monkeypatch.setattr(video_module.subprocess, "Popen", FailedProcess)
    controller = MpvController(ipc_dir=tmp_path)

    loaded = controller.load("broken://video")

    assert loaded is False
    assert popen_calls[0]["stdout"] == video_module.subprocess.PIPE
    assert popen_calls[0]["stderr"] == video_module.subprocess.STDOUT
    assert "No protocol handler found" in controller.last_error


def test_mpv_controller_treats_idle_after_loader_error_as_load_failure(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(video_module, "find_executable", lambda name: "/usr/bin/mpv")
    controller = MpvController(ipc_dir=tmp_path)
    controller.process = _RunningProcess()
    controller.ipc_path.touch()
    controller._output_tail = ["No protocol handler found to open URL broken://video"]

    def fake_request(command):
        if command == ["get_property", "idle-active"]:
            return {"error": "success", "data": True}
        return {"error": "property unavailable"}

    controller.request = fake_request

    assert controller._wait_for_socket() is False
    assert "No protocol handler found" in controller.last_error


def test_mpv_controller_filters_noisy_ipc_output_from_diagnostics(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(video_module, "find_executable", lambda name: "/usr/bin/mpv")
    controller = MpvController(ipc_dir=tmp_path)
    controller.process = _RunningProcess()
    controller.ipc_path.touch()
    controller._record_output_line("No protocol handler found")
    controller._record_output_line("[ipc_0] Write error (Broken pipe)")
    controller._record_output_line("(process:1): GLib-GIO-CRITICAL **: g_dbus_connection_emit_signal failed")

    def fake_request(command):
        if command == ["get_property", "idle-active"]:
            return {"error": "success", "data": True}
        return {"error": "property unavailable"}

    controller.request = fake_request

    assert controller._wait_for_socket() is False
    assert controller.last_error == "No protocol handler found"


def test_mpv_controller_stop_kills_process_that_ignores_graceful_shutdown(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(video_module, "find_executable", lambda name: "/usr/bin/mpv")
    controller = MpvController(ipc_dir=tmp_path)
    process = _StubbornProcess()
    controller.process = process
    controller.ipc_path.touch()

    controller.stop()

    assert process.terminate_calls == 1
    assert process.kill_calls == 1
    assert process.wait_timeouts == [0.5, 0.5, 0.5]
    assert controller.process is None
    assert not controller.ipc_path.exists()


def test_probe_video_playback_runs_mpv_without_gui_or_audio(monkeypatch):
    calls = []

    def fake_run(args, *, capture_output, text, timeout):
        calls.append({"args": args, "capture_output": capture_output, "text": text, "timeout": timeout})
        return subprocess.CompletedProcess(args, 0, stdout="loaded\n", stderr="")

    monkeypatch.setattr(video_module, "find_executable", lambda name: "/usr/bin/mpv")
    monkeypatch.setattr(video_module.subprocess, "run", fake_run)

    result = probe_video_playback("/nas/movie.mkv", timeout=4)

    assert result.ok is True
    assert result.message == "mpv accepted the source"
    assert calls == [
        {
            "args": [
                "/usr/bin/mpv",
                "--no-config",
                "--msg-level=all=warn",
                "--force-window=no",
                "--vo=null",
                "--ao=null",
                "--frames=1",
                "--",
                "/nas/movie.mkv",
            ],
            "capture_output": True,
            "text": True,
            "timeout": 4,
        }
    ]


def test_probe_video_playback_reports_clean_mpv_failure(monkeypatch):
    def fake_run(args, *, capture_output, text, timeout):
        return subprocess.CompletedProcess(
            args,
            2,
            stdout="",
            stderr="No video or audio streams selected.\n(process:1): GLib-GIO-CRITICAL **: ignored\n",
        )

    monkeypatch.setattr(video_module, "find_executable", lambda name: "/usr/bin/mpv")
    monkeypatch.setattr(video_module.subprocess, "run", fake_run)

    result = probe_video_playback("/nas/broken.mkv")

    assert result.ok is False
    assert result.returncode == 2
    assert result.message == "No video or audio streams selected."


def controller_response(tmp_path: Path, response_payload: bytes):
    ipc_path = tmp_path / "mpv.sock"
    received: list[dict] = []
    ready = threading.Event()

    def server() -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.bind(str(ipc_path))
            sock.listen(1)
            ready.set()
            connection, _ = sock.accept()
            with connection:
                received.append(json.loads(connection.recv(4096).decode("utf-8")))
                connection.sendall(response_payload)

    thread = threading.Thread(target=server)
    thread.start()
    assert ready.wait(timeout=1)
    controller = MpvController(ipc_dir=tmp_path)
    controller.process = _RunningProcess()
    controller.ipc_path = ipc_path

    response = controller.request(["get_property", "time-pos"])
    assert received == [{"command": ["get_property", "time-pos"]}]
    thread.join(timeout=1)
    return response


class _RunningProcess:
    def poll(self):
        return None

    def wait(self, timeout=None):
        return 0

    def terminate(self):
        return None


class _StubbornProcess:
    def __init__(self) -> None:
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_timeouts = []

    def poll(self):
        return None

    def wait(self, timeout=None):
        self.wait_timeouts.append(timeout)
        raise video_module.subprocess.TimeoutExpired(cmd="mpv", timeout=timeout)

    def terminate(self):
        self.terminate_calls += 1

    def kill(self):
        self.kill_calls += 1
