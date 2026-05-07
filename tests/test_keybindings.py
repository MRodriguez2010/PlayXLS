from playxls.keybindings import KeyBindingRegistry, normalize_combo
from playxls.models import KeyBinding


def test_normalize_combo_is_stable_for_modifiers_and_spacing():
    assert normalize_combo(" ctrl + t ") == "Ctrl+T"
    assert normalize_combo("Shift + Ctrl + Space") == "Ctrl+Shift+Space"
    assert normalize_combo("b") == "B"


def test_registry_dispatches_rebound_action():
    calls = []
    registry = KeyBindingRegistry(
        [
            KeyBinding(id="kb1", action="Play / Pause", combo="K", type="key"),
            KeyBinding(id="kb2", action="Toggle Theme", combo="Ctrl+T", type="key"),
        ]
    )

    registry.register("Play / Pause", lambda: calls.append("play"))
    registry.register("Toggle Theme", lambda: calls.append("theme"))

    assert registry.dispatch("k") is True
    assert registry.dispatch("Ctrl + T") is True
    assert registry.dispatch("Ctrl + B") is False
    assert calls == ["play", "theme"]
