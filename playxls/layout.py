from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Sequence


SplitDirection = Literal["v", "h"]


@dataclass(frozen=True, slots=True)
class LayoutNode:
    kind: Literal["leaf", "split"]
    direction: SplitDirection | None = None
    ratio: float = 0.5
    a: "LayoutNode | None" = None
    b: "LayoutNode | None" = None

    @classmethod
    def leaf(cls) -> "LayoutNode":
        return cls("leaf")

    @classmethod
    def split(cls, direction: SplitDirection, ratio: float, a: "LayoutNode", b: "LayoutNode") -> "LayoutNode":
        return cls("split", direction=direction, ratio=clamp_ratio(ratio), a=a, b=b)


@dataclass(frozen=True, slots=True)
class CellRect:
    x: float
    y: float
    w: float
    h: float
    path: tuple[str, ...] = ()

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (round(self.x, 3), round(self.y, 3), round(self.w, 3), round(self.h, 3))


@dataclass(frozen=True, slots=True)
class SplitHandle:
    path: tuple[str, ...]
    direction: SplitDirection
    x: float
    y: float
    length: float
    container: CellRect


@dataclass(frozen=True, slots=True)
class LayoutDefinition:
    id: str
    label: str
    tree: LayoutNode
    custom: bool = False


def clamp_ratio(ratio: float) -> float:
    return max(0.1, min(0.9, float(ratio)))


def split_v(a: LayoutNode | None = None, b: LayoutNode | None = None, ratio: float = 0.5) -> LayoutNode:
    return LayoutNode.split("v", ratio, a or LayoutNode.leaf(), b or LayoutNode.leaf())


def split_h(a: LayoutNode | None = None, b: LayoutNode | None = None, ratio: float = 0.5) -> LayoutNode:
    return LayoutNode.split("h", ratio, a or LayoutNode.leaf(), b or LayoutNode.leaf())


def build_3x3() -> LayoutNode:
    def row() -> LayoutNode:
        return split_v(split_v(LayoutNode.leaf(), LayoutNode.leaf(), 2 / 3), LayoutNode.leaf(), 2 / 3)

    return split_h(split_h(row(), row(), 2 / 3), row(), 2 / 3)


def preset_layouts() -> list[LayoutDefinition]:
    return [
        LayoutDefinition("1x1", "Single", LayoutNode.leaf()),
        LayoutDefinition("1x2", "1 x 2", split_v()),
        LayoutDefinition("1x3", "1 x 3", split_v(split_v(LayoutNode.leaf(), LayoutNode.leaf(), 2 / 3), LayoutNode.leaf(), 2 / 3)),
        LayoutDefinition("2x2", "2 x 2", split_h(split_v(), split_v())),
        LayoutDefinition("3x3", "3 x 3", build_3x3()),
        LayoutDefinition("1+2", "1 + 2 stack", split_v(LayoutNode.leaf(), split_h(), 0.6)),
    ]


def count_cells(node: LayoutNode) -> int:
    if node.kind == "leaf":
        return 1
    assert node.a is not None and node.b is not None
    return count_cells(node.a) + count_cells(node.b)


def collect_cells(node: LayoutNode, x: float = 0.0, y: float = 0.0, w: float = 100.0, h: float = 100.0) -> list[CellRect]:
    out: list[CellRect] = []
    _collect_cells(node, x, y, w, h, (), out)
    return out


def _collect_cells(node: LayoutNode, x: float, y: float, w: float, h: float, path: tuple[str, ...], out: list[CellRect]) -> None:
    if node.kind == "leaf":
        out.append(CellRect(x, y, w, h, path))
        return

    assert node.a is not None and node.b is not None and node.direction is not None
    if node.direction == "v":
        w_a = w * node.ratio
        _collect_cells(node.a, x, y, w_a, h, (*path, "a"), out)
        _collect_cells(node.b, x + w_a, y, w - w_a, h, (*path, "b"), out)
    else:
        h_a = h * node.ratio
        _collect_cells(node.a, x, y, w, h_a, (*path, "a"), out)
        _collect_cells(node.b, x, y + h_a, w, h - h_a, (*path, "b"), out)


def collect_splits(node: LayoutNode, x: float = 0.0, y: float = 0.0, w: float = 100.0, h: float = 100.0) -> list[SplitHandle]:
    out: list[SplitHandle] = []
    _collect_splits(node, x, y, w, h, (), out)
    return out


def _collect_splits(node: LayoutNode, x: float, y: float, w: float, h: float, path: tuple[str, ...], out: list[SplitHandle]) -> None:
    if node.kind == "leaf":
        return
    assert node.a is not None and node.b is not None and node.direction is not None
    if node.direction == "v":
        w_a = w * node.ratio
        out.append(SplitHandle(path, "v", x + w_a, y, h, CellRect(x, y, w, h, path)))
        _collect_splits(node.a, x, y, w_a, h, (*path, "a"), out)
        _collect_splits(node.b, x + w_a, y, w - w_a, h, (*path, "b"), out)
    else:
        h_a = h * node.ratio
        out.append(SplitHandle(path, "h", x, y + h_a, w, CellRect(x, y, w, h, path)))
        _collect_splits(node.a, x, y, w, h_a, (*path, "a"), out)
        _collect_splits(node.b, x, y + h_a, w, h - h_a, (*path, "b"), out)


def split_leaf_at(node: LayoutNode, path: Sequence[str], direction: SplitDirection) -> LayoutNode:
    if not path:
        if node.kind != "leaf":
            return node
        return LayoutNode.split(direction, 0.5, LayoutNode.leaf(), LayoutNode.leaf())
    head, *rest = path
    if node.kind != "split" or head not in {"a", "b"}:
        return node
    assert node.a is not None and node.b is not None and node.direction is not None
    return LayoutNode.split(
        node.direction,
        node.ratio,
        split_leaf_at(node.a, rest, direction) if head == "a" else node.a,
        split_leaf_at(node.b, rest, direction) if head == "b" else node.b,
    )


def remove_leaf_at(node: LayoutNode, path: Sequence[str]) -> LayoutNode:
    if node.kind == "leaf" or not path:
        return node
    head, *rest = path
    assert node.a is not None and node.b is not None and node.direction is not None
    if not rest:
        return node.b if head == "a" else node.a
    return LayoutNode.split(
        node.direction,
        node.ratio,
        remove_leaf_at(node.a, rest) if head == "a" else node.a,
        remove_leaf_at(node.b, rest) if head == "b" else node.b,
    )


def set_ratio_at(node: LayoutNode, path: Sequence[str], ratio: float) -> LayoutNode:
    if node.kind != "split":
        return node
    assert node.a is not None and node.b is not None and node.direction is not None
    if not path:
        return LayoutNode.split(node.direction, clamp_ratio(ratio), node.a, node.b)
    head, *rest = path
    return LayoutNode.split(
        node.direction,
        node.ratio,
        set_ratio_at(node.a, rest, ratio) if head == "a" else node.a,
        set_ratio_at(node.b, rest, ratio) if head == "b" else node.b,
    )


def layout_to_dict(node: LayoutNode) -> dict[str, Any]:
    if node.kind == "leaf":
        return {"type": "leaf"}
    assert node.a is not None and node.b is not None and node.direction is not None
    return {
        "type": "split",
        "direction": node.direction,
        "ratio": node.ratio,
        "a": layout_to_dict(node.a),
        "b": layout_to_dict(node.b),
    }


def layout_from_dict(data: dict[str, Any]) -> LayoutNode:
    if data.get("type") == "split":
        direction = "h" if data.get("direction") == "h" else "v"
        return LayoutNode.split(
            direction,
            float(data.get("ratio", 0.5)),
            layout_from_dict(data.get("a", {"type": "leaf"})),
            layout_from_dict(data.get("b", {"type": "leaf"})),
        )
    return LayoutNode.leaf()
