from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from playxls.layout import LayoutNode, collect_cells
from playxls.theme import Theme


def clear_layout(layout: QHBoxLayout | QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child_layout = item.layout()
        if widget:
            widget.deleteLater()
        if child_layout:
            clear_layout(child_layout)


class MonoLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet('font-family: "JetBrains Mono", monospace;')


class SegmentedControl(QFrame):
    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str]], active: str, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self.setStyleSheet(f"background:{theme.surface2};border-radius:5px;")
        for value, label in options:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(value == active)
            button.setProperty("value", value)
            button.setMinimumHeight(28)
            self.group.addButton(button)
            layout.addWidget(button)
        self.group.buttonClicked.connect(lambda button: self.changed.emit(str(button.property("value"))))

    def set_active(self, value: str) -> None:
        for button in self.group.buttons():
            button.setChecked(button.property("value") == value)


class ToastHost(QLabel):
    def __init__(self, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setVisible(False)
        self.setFixedHeight(30)
        self.setStyleSheet(
            f'font-family:"JetBrains Mono", monospace;font-size:12px;'
            f"background:{theme.text_primary};color:{theme.bg};border-radius:15px;padding:6px 12px;"
        )
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.hide)

    def show_message(self, message: str) -> None:
        self.setText(message)
        self.adjustSize()
        parent = self.parentWidget()
        if parent:
            self.move((parent.width() - self.width()) // 2, 56)
        self.setVisible(True)
        self.raise_()
        self.timer.start(2200)


class LayoutThumbnailWidget(QWidget):
    def __init__(self, tree: LayoutNode, theme: Theme, active: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tree = tree
        self.theme = theme
        self.active = active
        self.setMinimumSize(70, 40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.theme.bg)
        pen = QPen(self.theme.accent if self.active else self.theme.border_strong)
        pen.setWidth(1)
        painter.setPen(pen)
        margin = 4
        bounds = self.rect().adjusted(margin, margin, -margin, -margin)
        for cell in collect_cells(self.tree):
            rect = QRect(
                int(bounds.x() + bounds.width() * cell.x / 100),
                int(bounds.y() + bounds.height() * cell.y / 100),
                max(2, int(bounds.width() * cell.w / 100) - 2),
                max(2, int(bounds.height() * cell.h / 100) - 2),
            )
            painter.fillRect(rect, self.theme.accent_bg if self.active else self.theme.surface2)
            painter.drawRoundedRect(rect, 2, 2)


def animate_geometry(widget: QWidget, rect: QRect) -> None:
    animation = QPropertyAnimation(widget, b"geometry", widget)
    animation.setDuration(350)
    animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
    animation.setStartValue(widget.geometry())
    animation.setEndValue(rect)
    animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


def make_section_label(text: str, theme: Theme) -> MonoLabel:
    label = MonoLabel(text.upper())
    label.setStyleSheet(
        f'font-family:"JetBrains Mono", monospace;font-size:10px;'
        f"letter-spacing:1px;color:{theme.text_muted};background:transparent;"
    )
    return label


def action_button(text: str, callback: Callable[[], None], theme: Theme, *, primary: bool = False) -> QPushButton:
    button = QPushButton(text)
    if primary:
        button.setObjectName("primaryButton")
    button.clicked.connect(callback)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button
