# PlayXLS

PlayXLS is a native Linux multi-stream video player prototype built from the supplied `Initial_Demo` React reference. The current build uses Python + PySide6/Qt 6 with tested pure modules for tile-tree layouts, TOML persistence, keybindings, settings, and folder scanning.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[gui,watch,streams,test]'
.venv/bin/playxls --diagnose
.venv/bin/playxls ~/Videos/foo.mp4 ~/Videos/bar.mp4
```

Without file arguments, PlayXLS opens the persisted session and scans configured watch folders. With one to four file arguments, it chooses Single, 1 x 2, 1 + 2 stack, or 2 x 2 automatically. Five or more files start in 3 x 3.

## What Works In This Build

- Native title/sidebar/toolbar/stage/transport shell matching the supplied prototype structure.
- PlayXLS logo pack integration for the application/window icon and title-bar mark.
- Resizable Sources panel via the main splitter.
- Theme tokens for dark/light mode, title-bar toggle, and `Ctrl+T`.
- Required preset tile-tree layouts plus custom layout save flow.
- Cell assignment by index across layout changes.
- Library, folders, and browser source tabs.
- Remove actions for library videos, watched folders, and browser sources.
- Startup scanning for persisted watched folders, without prototype demo videos.
- Library folder filters so watched folder videos can be isolated quickly.
- Lazy hover previews in library rows through a bounded mpv LRU preview pool.
- Drag/drop local video files into the window to add and assign them to empty visible cells.
- mpv subprocess adapter for local video cells when `mpv` is installed.
- QtWebEngine browser cells when the PySide6 WebEngine wheel is present.
- Shared QtWebEngine browser profile by default with one reused `QWebEngineProfile` and persistent storage/cache under `~/.cache/playxls/browser/shared/`.
- Advanced setting to switch browser cells between shared login/cookie storage and isolated per-cell profiles under `~/.cache/playxls/browser/cell-N/`.
- App-level browser toolbar above the stage controls the active/hovered browser cell, avoiding unreliable X11 stacking between Qt controls and embedded QtWebEngine surfaces.
- Browser cell back/forward/reload buttons and editable URL bar.
- Browser toolbar compatibility notice for DRM-heavy services whose protected video may not play inside QtWebEngine.
- Browser toolbar handoff to open the active browser cell URL in the system browser for sites that block embedded playback or login.
- Compact fixed-height browser cell toolbar for small cells.
- Live bottom transport for the active video cell, including mpv-backed position, duration, play/pause state, and seek slider.
- Playback position persistence/resume when the setting is enabled.
- Pause-on-minimize with resume only when playback was active before minimize.
- Hover expand, hover-volume calculations, border modes, and cell-confined fullscreen.
- Settings dialog with the five required sections and autosave.
- Shortcut recording from the Settings dialog with TOML persistence.
- QtWebEngine page fullscreen requests are accepted without expanding beyond the current browser cell.
- TOML persistence in `~/.config/playxls/`.
- Session persistence for layout, cell assignments, volume, and mute state.
- Folder scanner fallback that discovers new video files and raises PlayXLS toasts on the Qt main thread.
- Core tests for layout geometry, config round trips, keybinding dispatch, playback state, and preview pooling.

## Test

```bash
.venv/bin/pytest -q
python -m compileall playxls
```

## Native Dependency Notes

This machine currently has `/snap/bin/mpv` but does not expose GTK4/libmpv development headers. The app therefore uses an mpv subprocess embedding adapter for the first runnable native slice. See `MIGRATION_FROM_PROTOTYPE.md` for remaining native gaps and the migration path to libmpv/WebKitGTK/Flatpak.

Development is currently Ubuntu-first. The finished app should also be usable on macOS and Windows, so platform-specific integration should stay isolated behind adapters. Packaging is intentionally the final build phase after backend, browser, and performance behavior are settled.

### Ubuntu Qt X11 Dependency

If launch fails with Qt's `Could not load the Qt platform plugin "xcb"` message, install the missing runtime package:

```bash
sudo apt install libxcb-cursor0
```

PlayXLS now checks for this before creating `QApplication` and exits with that command instead of aborting. On a real Wayland session, this may also work:

```bash
QT_QPA_PLATFORM=wayland .venv/bin/playxls
```
