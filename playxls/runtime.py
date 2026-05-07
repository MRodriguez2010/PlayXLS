from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def find_executable(name: str, *, executable: str | Path | None = None, path: str | None = None) -> str | None:
    exe = Path(executable or sys.executable)
    sibling = exe.parent / name
    if os.name == "nt":
        sibling = sibling.with_suffix(".exe")
    if sibling.exists() and os.access(sibling, os.X_OK):
        return str(sibling)
    return shutil.which(name, path=path)
