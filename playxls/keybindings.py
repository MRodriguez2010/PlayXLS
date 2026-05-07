from __future__ import annotations

from collections.abc import Callable

from playxls.models import KeyBinding


MODIFIER_ORDER = ("Ctrl", "Alt", "Shift", "Meta")


def normalize_combo(combo: str) -> str:
    pieces = [piece.strip() for piece in combo.replace(" + ", "+").split("+") if piece.strip()]
    modifiers: list[str] = []
    key = ""
    aliases = {
        "CONTROL": "Ctrl",
        "CTRL": "Ctrl",
        "ALT": "Alt",
        "OPTION": "Alt",
        "SHIFT": "Shift",
        "META": "Meta",
        "CMD": "Meta",
        "COMMAND": "Meta",
    }
    for piece in pieces:
        upper = piece.upper()
        mapped = aliases.get(upper)
        if mapped:
            if mapped not in modifiers:
                modifiers.append(mapped)
        else:
            key = _normalize_key(piece)
    ordered = [modifier for modifier in MODIFIER_ORDER if modifier in modifiers]
    if key:
        ordered.append(key)
    return "+".join(ordered)


def _normalize_key(key: str) -> str:
    if key == " " or key.lower() == "space":
        return "Space"
    if len(key) == 1:
        return key.upper()
    if key.lower() == "escape":
        return "Esc"
    return key[0].upper() + key[1:]


class KeyBindingRegistry:
    def __init__(self, bindings: list[KeyBinding]) -> None:
        self.bindings = bindings
        self.handlers: dict[str, Callable[[], None]] = {}

    def register(self, action: str, handler: Callable[[], None]) -> None:
        self.handlers[action] = handler

    def rebind(self, binding_id: str, combo: str) -> list[KeyBinding]:
        normalized = normalize_combo(combo)
        self.bindings = [
            KeyBinding(binding.id, binding.action, normalized if binding.id == binding_id else binding.combo, binding.type)
            for binding in self.bindings
        ]
        return self.bindings

    def dispatch(self, combo: str) -> bool:
        normalized = normalize_combo(combo)
        for binding in self.bindings:
            if binding.type == "key" and normalize_combo(binding.combo) == normalized:
                handler = self.handlers.get(binding.action)
                if handler:
                    handler()
                return True
        return False
