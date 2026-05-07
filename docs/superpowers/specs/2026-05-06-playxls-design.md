# PlayXLS Native Design

## Source Of Truth

The design source of truth is the supplied build prompt in `Initial_Demo/playxls_codex_prompt.md` and the interactive React prototype in `Initial_Demo/playxls_demo.jsx`. No new visual concept is introduced in this spec; the native app should preserve the prototype's disciplined native-tool aesthetic, compact density, amber accent, title/sidebar/toolbar/stage/transport structure, theme tokens, and interaction timing.

## Build Slice

The initial native build uses Python with PySide6/Qt 6. This is the practical local path because the workspace has Python but does not currently expose GTK4 or libmpv development headers. Video cells use an adapter boundary that can run `mpv` as an embedded subprocess today and can be replaced by libmpv later without changing layout, settings, or UI state code. Browser cells use QtWebEngine when available and fall back to a clear native placeholder when the optional GUI dependency is absent.

## Architecture

Core behavior is pure Python and independently tested:

- `playxls.layout` owns tile-tree layouts, preset geometry, splitting, removing, ratio edits, and serialization.
- `playxls.models` owns settings, keybindings, library items, folders, browser presets, and cell content.
- `playxls.config` persists TOML files under `~/.config/playxls`, with missing keys defaulted and unknown keys ignored.
- `playxls.keybindings` normalizes shortcuts and dispatches configured actions.
- `playxls.video` owns the mpv adapter boundary.
- `playxls.folders` owns watched-folder scanning and event delivery.
- `playxls.ui` composes the PySide6 app shell, panels, grid stage, settings dialog, grid editor, and transport.

## Functional Scope

This build should open local video paths from the CLI, choose a single or multi-cell starting layout based on file count, preserve cell assignments by index across layout switches, support library/folder/browser sidebar tabs, support theme switching via title bar and `Ctrl+T`, support border cycling via toolbar and `B`, support hover expand and hover-volume settings, support cell-confined fullscreen via `F`, support custom layout creation and persistence, persist settings/bindings/folders/layouts, and surface concise toast notifications.

Flatpak packaging, true libmpv embedding, full WebKit/Qt fullscreen API interception, and long-run memory profiling remain documented migration items until the local native toolchain is available.

## Testing

Pure modules get automated tests for tile-tree geometry, settings/layout persistence, and shortcut dispatch. The GUI is manually smoke-tested by launching the app when PySide6 is installed. Optional media and browser adapters degrade gracefully when platform dependencies are missing.
