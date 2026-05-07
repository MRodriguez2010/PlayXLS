from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGO_PACK = PROJECT_ROOT / "playxls-logo-pack"


def app_icon_path(size: int = 256) -> Path:
    return LOGO_PACK / "app-icons" / f"playxls-icon-{size}.png"


def title_mark_path() -> Path:
    return LOGO_PACK / "mark-primary" / "playxls-mark-primary.svg"
