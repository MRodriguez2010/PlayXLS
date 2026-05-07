from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    bg: str
    surface1: str
    surface2: str
    surface3: str
    title_bar: str
    border: str
    border_strong: str
    text_primary: str
    text_secondary: str
    text_tertiary: str
    text_muted: str
    accent: str
    accent_bg: str
    accent_border: str
    danger: str
    success: str
    cell_bg: str
    cell_empty: str
    on_accent: str


THEMES = {
    "dark": Theme(
        "dark",
        bg="#0a0a0c",
        surface1="#0d0d10",
        surface2="#15151a",
        surface3="#1c1c20",
        title_bar="#0f0f12",
        border="#1c1c20",
        border_strong="#2a2a30",
        text_primary="#e7e5e4",
        text_secondary="#a8a29e",
        text_tertiary="#78716c",
        text_muted="#57534e",
        accent="#fbbf24",
        accent_bg="rgba(251, 191, 36, 0.15)",
        accent_border="rgba(251, 191, 36, 0.40)",
        danger="#f43f5e",
        success="#34d399",
        cell_bg="#000000",
        cell_empty="#0c0c10",
        on_accent="#1c1917",
    ),
    "light": Theme(
        "light",
        bg="#fafaf9",
        surface1="#ffffff",
        surface2="#f5f5f4",
        surface3="#e7e5e4",
        title_bar="#f5f5f4",
        border="#e7e5e4",
        border_strong="#d6d3d1",
        text_primary="#1c1917",
        text_secondary="#44403c",
        text_tertiary="#78716c",
        text_muted="#a8a29e",
        accent="#d97706",
        accent_bg="rgba(217, 119, 6, 0.10)",
        accent_border="rgba(217, 119, 6, 0.40)",
        danger="#e11d48",
        success="#059669",
        cell_bg="#000000",
        cell_empty="#f5f5f4",
        on_accent="#ffffff",
    ),
}


def resolve_theme(name: str) -> Theme:
    return THEMES.get("light" if name == "system" else name, THEMES["dark"])


def app_stylesheet(theme: Theme) -> str:
    return f"""
    QWidget {{
        background: {theme.bg};
        color: {theme.text_primary};
        font-family: Inter, "Segoe UI", system-ui, sans-serif;
        font-size: 12px;
    }}
    QLineEdit, QSpinBox, QComboBox {{
        background: {theme.surface2};
        color: {theme.text_primary};
        border: 1px solid {theme.border};
        border-radius: 5px;
        padding: 5px 7px;
        min-height: 22px;
    }}
    QPushButton {{
        background: {theme.surface2};
        color: {theme.text_secondary};
        border: 1px solid {theme.border};
        border-radius: 5px;
        padding: 5px 9px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background: {theme.surface3};
        color: {theme.text_primary};
    }}
    QPushButton:checked {{
        background: {theme.accent_bg};
        border-color: {theme.accent};
        color: {theme.accent};
    }}
    QPushButton#primaryButton {{
        background: {theme.accent};
        color: {theme.on_accent};
        border-color: {theme.accent};
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {theme.surface3};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        width: 12px;
        margin: -4px 0;
        border-radius: 6px;
        background: {theme.accent};
    }}
    QTabWidget::pane {{
        border: 0;
    }}
    QTabBar::tab {{
        background: {theme.surface2};
        color: {theme.text_tertiary};
        padding: 8px 10px;
        border: 0;
        min-width: 82px;
    }}
    QTabBar::tab:selected {{
        background: {theme.surface1};
        color: {theme.text_primary};
    }}
    QMenu {{
        background: {theme.surface2};
        color: {theme.text_primary};
        border: 1px solid {theme.border};
        padding: 6px;
    }}
    QMenu::item {{
        padding: 6px 18px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background: {theme.surface3};
    }}
    QScrollArea {{
        border: 0;
    }}
    """
