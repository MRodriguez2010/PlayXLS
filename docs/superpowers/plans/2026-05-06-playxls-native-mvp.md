# PlayXLS Native MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable native PlayXLS desktop app scaffold with tested tile-tree, settings, keybinding, persistence, sidebar, grid, fullscreen, hover, and theme behavior.

**Architecture:** Keep behavior in pure Python modules and place PySide6 code behind a GUI boundary. The grid stage consumes tile-tree cell rectangles and cell content state, while persistence adapters round-trip user settings and custom layouts.

**Tech Stack:** Python 3.12, PySide6/Qt 6 optional GUI dependency, TOML persistence, pytest for core tests, mpv subprocess adapter for local playback until libmpv headers are available.

---

### Task 1: Core Models And Layouts

**Files:**
- Create: `playxls/models.py`
- Create: `playxls/layout.py`
- Test: `tests/test_layout.py`

- [ ] Define dataclasses for settings, cell content, videos, folders, keybindings, and tile-tree layout nodes.
- [ ] Implement preset layouts: Single, 1 x 2, 1 x 3, 2 x 2, 3 x 3, and 1 + 2 stack.
- [ ] Implement cell collection, split collection, split leaf, remove leaf, set ratio, count cells, clone, and serialization helpers.
- [ ] Test preset counts, 1 + 2 geometry, ratio clamping, split/remove behavior, and serialization round trip.

### Task 2: Persistence And Keybindings

**Files:**
- Create: `playxls/config.py`
- Create: `playxls/keybindings.py`
- Test: `tests/test_config.py`
- Test: `tests/test_keybindings.py`

- [ ] Implement TOML settings, layouts, bindings, and watched folders under configurable root paths.
- [ ] Ignore unknown keys and default missing keys.
- [ ] Implement shortcut normalization, matching, rebinding, and dispatch.
- [ ] Test settings/layout/binding/folder round trips and keybinding dispatch.

### Task 3: Native App Shell

**Files:**
- Create: `pyproject.toml`
- Create: `playxls/__init__.py`
- Create: `playxls/__main__.py`
- Create: `playxls/app.py`
- Create: `playxls/theme.py`
- Create: `playxls/ui/main_window.py`
- Create: `playxls/ui/widgets.py`

- [ ] Add package metadata and optional GUI/test dependencies.
- [ ] Parse CLI video paths and seed initial cells/layout.
- [ ] Create the title bar, unified sidebar, toolbar, stage area, transport bar, toast layer, and theme application.

### Task 4: Panels, Grid, Dialogs, And Adapters

**Files:**
- Create: `playxls/video.py`
- Create: `playxls/folders.py`
- Create: `playxls/ui/grid.py`
- Create: `playxls/ui/panels.py`
- Create: `playxls/ui/dialogs.py`

- [ ] Implement mpv subprocess adapter with JSON IPC volume/pause/load commands.
- [ ] Implement library, folders, and browser sidebar panels with cell assignment.
- [ ] Implement absolute-positioned tile-tree grid, hover expand, border modes, context menu, and cell-confined fullscreen.
- [ ] Implement layout picker, grid editor, settings dialog, and shortcut recording.
- [ ] Implement watched-folder polling fallback and toast on new file discovery.

### Task 5: Verification And Documentation

**Files:**
- Create: `README.md`
- Create: `MIGRATION_FROM_PROTOTYPE.md`

- [ ] Run pytest for pure modules.
- [ ] Run package import and CLI help checks.
- [ ] Launch GUI smoke test when PySide6 is installed or document the missing optional dependency.
- [ ] Document implemented scope, launch commands, and native migration gaps.
