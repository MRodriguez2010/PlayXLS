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

To collect dependency output, config files, and playback failure logs without launching the GUI:

```bash
.venv/bin/playxls --export-diagnostics ~/playxls-diagnostics.zip
```

To check whether mpv can decode a local video or URL without launching the GUI:

```bash
.venv/bin/playxls --probe-video ~/Videos/foo.mp4
```

If a watched folder or NAS path is causing startup trouble, launch once without watched-folder loading or scanning:

```bash
.venv/bin/playxls --safe-mode
```

## What Works In This Build

- Native title/sidebar/toolbar/stage/transport shell matching the supplied prototype structure.
- PlayXLS logo pack integration for the application/window icon and title-bar mark.
- Resizable Sources panel via the main splitter, with the Sources/stage split restored from the last session.
- Theme tokens for dark/light mode, title-bar toggle, and `Ctrl+T`.
- Required preset tile-tree layouts plus custom layout save flow.
- Delete affordance for saved custom layouts while protecting built-in presets.
- Cell assignment by index across layout changes.
- Library, folders, and browser source tabs.
- Remove actions for library videos, watched folders, and browser sources.
- Cached watched-folder startup index under `~/.cache/playxls/library_index.toml`; background scans refresh the index after launch.
- Recovery safe mode for launching without watched-folder cache loading or background folder scanning.
- Background watched-folder scan failures are surfaced as toasts and appended to the diagnostics log instead of killing the scanner thread.
- Library folder filters so watched folder videos can be isolated quickly.
- Large library rendering is bounded to the first 200 matching rows with an explicit show-more action, avoiding thousands of startup widgets for NAS folders.
- Lazy hover previews in library rows through a bounded mpv LRU preview pool.
- Static thumbnail mode avoids native thumbnail windows and does not touch the live preview pool during row rebuilds.
- Drag/drop local video files into the window to add and assign them to empty visible cells.
- mpv subprocess adapter for local video cells when `mpv` is installed.
- GUI-free `--probe-video` command to test whether mpv can decode a local file or URL before debugging embedded playback.
- Embedded mpv cells launch with mpv OSC/OSD/default bindings disabled so local-video controls stay in the app-level transport and do not interfere with hover expansion.
- Embedded mpv cells launch with cache/readahead, safe hardware decode, and faster downscale filters to reduce HD/NAS playback pressure in small cells.
- Optional local-video audio normalization is available in Playback settings.
- mpv subprocess shutdown escalates from quit to terminate to kill so failed local-video loads cannot leave stuck child processes behind.
- Local-video load failures now surface mpv diagnostics in the cell and toast instead of failing silently.
- Local-video load failures are also appended to `~/.local/state/playxls/playback-diagnostics.jsonl` for post-run debugging.
- Diagnostics can be exported from the CLI before GUI startup; cache indexes and browser profile data are intentionally excluded.
- `playxls --diagnose` and the in-app Diagnostics dialog report `libmpv` availability and tail the playback diagnostics log.
- QtWebEngine browser cells when the PySide6 WebEngine wheel is present.
- Shared QtWebEngine browser profile by default with one reused `QWebEngineProfile` and persistent storage/cache under `~/.cache/playxls/browser/shared/`.
- Advanced setting to switch browser cells between shared login/cookie storage and isolated per-cell profiles under `~/.cache/playxls/browser/cell-N/`.
- App-level browser toolbar above the stage controls the active/hovered browser cell, avoiding unreliable X11 stacking between Qt controls and embedded QtWebEngine surfaces.
- Browser cell back/forward/reload buttons and editable URL bar.
- Browser source-list and toolbar compatibility notices for DRM-heavy or playback-limited services whose video may not play inside QtWebEngine.
- Browser toolbar handoff to open the active browser cell URL in the system browser for sites that block embedded playback or login.
- Browser load failures from QtWebEngine are surfaced in the app-level toolbar with Qt error details when available and the system-browser handoff still available.
- Compact fixed-height browser cell toolbar for small cells.
- Browser cells follow app mute/unmute and try to set standard page media element volume through JavaScript when the site allows it.
- Live bottom transport for local video cells, including previous, play/pause, stop, next, mpv-backed timing, and a unified timeline that draws one numbered playhead per local-video cell against the longest active duration.
- App-level symbolic repeat and shuffle transport controls with persisted state; `repeat 1` toggles mpv single-file looping, while `repeat all`, `repeat folder`, and shuffle auto-advance finished local videos.
- Playback position persistence/resume when the setting is enabled.
- Pause-on-minimize with resume only when playback was active before minimize.
- Hover expand, hover-volume calculations, border modes, and cell-confined fullscreen. Hover enter/leave repositioning avoids native-window geometry animation to reduce flicker with embedded local/browser video surfaces.
- Settings dialog with the five required sections and autosave.
- Shortcut recording from the Settings dialog with TOML persistence.
- QtWebEngine page fullscreen requests are accepted without expanding beyond the current browser cell.
- TOML persistence in `~/.config/playxls/`.
- Session persistence for layout, cell assignments, Sources/stage split, volume, and mute state.
- Folder scanner fallback that discovers new video files and raises PlayXLS toasts on the Qt main thread.
- Core tests for layout geometry, config round trips, keybinding dispatch, playback state, and preview pooling.

## Test

```bash
.venv/bin/pytest -q
python -m compileall playxls
```

## Native Dependency Notes

This machine currently has `/snap/bin/mpv` but does not expose GTK4/libmpv development headers or a loadable `libmpv`. The app therefore uses an mpv subprocess embedding adapter for the first runnable native slice. That adapter embeds with mpv's X11-style `--wid`, so PlayXLS prefers Qt's `xcb` backend when it is available, including on Wayland desktops with XWayland. See `MIGRATION_FROM_PROTOTYPE.md` for remaining native gaps and the migration path to libmpv/WebKitGTK/Flatpak.

Development is currently Ubuntu-first. The finished app should also be usable on macOS and Windows, so platform-specific integration should stay isolated behind adapters. Packaging is intentionally the final build phase after backend, browser, and performance behavior are settled.

### Ubuntu Qt X11 Dependency

If launch fails with Qt's `Could not load the Qt platform plugin "xcb"` message, install the missing runtime package:

```bash
sudo apt install libxcb-cursor0
```

PlayXLS now checks for this before creating `QApplication` and exits with that command instead of aborting. Forcing `QT_QPA_PLATFORM=wayland` is not recommended with the current subprocess-mpv backend because embedded local-video playback depends on X11/XWayland window embedding.
