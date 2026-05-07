import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from playxls.layout import preset_layouts
from playxls.models import AppSettings, CellContent
from playxls.theme import THEMES
from playxls.ui.grid import GridStage


def test_hovered_expanded_cell_is_stacked_above_overlapping_cells(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    stage = GridStage(THEMES["dark"], tmp_path)
    stage.resize(400, 400)
    layout = next(item for item in preset_layouts() if item.id == "2x2")
    settings = AppSettings(expand_on_hover=True, expand_percent=140, volume_on_hover=False)

    stage.set_data(layout, [CellContent.empty() for _ in range(4)], [], settings, False)
    stage.show()
    app.processEvents()

    stage._set_hovered(0)
    stage.reposition(animated=False)
    app.processEvents()

    top_widget = stage.childAt(QPoint(250, 250))

    assert getattr(top_widget, "index", None) == 0
    stage.close()
