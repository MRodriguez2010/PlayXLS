from pathlib import Path
import json
import socket
import threading

import playxls.video as video_module
from playxls.video import MpvController, default_mpv_ipc_dir


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
