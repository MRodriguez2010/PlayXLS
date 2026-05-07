from pathlib import Path

from playxls.runtime import find_executable


def test_find_executable_prefers_interpreter_bin(tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tool = bin_dir / "streamlink"
    tool.write_text("#!/bin/sh\n")
    tool.chmod(0o755)

    found = find_executable("streamlink", executable=bin_dir / "python", path="")

    assert found == str(tool)
