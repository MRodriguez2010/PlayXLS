# PlayXLS Checkpoint

Updated: 2026-05-07

## Current State

PlayXLS is a Python 3.12 + PySide6/Qt 6 native desktop app. It runs from the project virtualenv:

```bash
cd /home/ai-agents/Projects/PlayXLS
.venv/bin/playxls --diagnose
.venv/bin/playxls --safe-mode
.venv/bin/playxls
```

The latest slice added preview/library performance certification, persisted Sources/stage splitter sizing, custom-layout delete affordances, browser source-list compatibility notices, richer QtWebEngine load-failure messages, cached watched-folder startup loading, the large-NAS startup fix, the XCB launch preference for embedded mpv playback, Pluto playback-limited warnings, repeat/shuffle auto-advance for finished local videos, visible mpv load-failure diagnostics for local video cells, a recovery safe-mode launch path for bypassing watched folders, watched-folder scan failure logging, symbolic transport controls, unified local-video timeline heads, HD/NAS playback tuning, optional audio normalization, browser volume best-effort control, an in-app Diagnostics dialog, and the first direct libmpv backend.

## Latest Libmpv Backend

The local environment now has `/usr/bin/mpv`, `libmpv.so.2`, and the `python-mpv` binding. PlayXLS now exposes `LibMpvController`, a direct libmpv adapter with the same control surface as the existing subprocess backend: `load`, `stop`, `set_pause`, `set_volume`, `seek_absolute`, `set_loop_file`, and `transport_snapshot`.

`preferred_mpv_controller()` selects `LibMpvController` when `libmpv` and `python-mpv` are available, otherwise it falls back to the existing `MpvController` subprocess adapter. Local-video cells and the hover preview pool now use this preferred factory by default.

The libmpv adapter carries over the current playback tuning: disabled mpv OSC/OSD/default bindings, cache/readahead, `hwdec=auto-safe`, bilinear scaling/downscaling, optional `dynaudnorm`, and `wid` embedding into the Qt native child window. This is direct libmpv control, but it is still the `wid` rendering path rather than the lower-level libmpv render API.

`playxls --diagnose` now includes `video backend: libmpv` when the preferred backend is active.

## Latest Transport And Playback Tuning

The bottom transport now has previous, play/pause, stop, next, mute, volume, symbolic repeat, and symbolic shuffle controls. Previous/next assign the adjacent library video into the active local-video cell with wraparound. Stop seeks the active local-video cell to `0` and pauses it. Repeat labels are now compact symbols (`↻`, `↻1`, `↻∞`, `↻F`) and shuffle uses symbolic off/on labels.

The former single seek slider is now a unified local-video timeline. It computes the longest active local-video duration and draws one numbered playhead per local-video cell against that shared time base. Browser videos are excluded because QtWebEngine does not expose reliable per-site playback timing through a shared API. Clicking the timeline seeks the active local-video cell to the corresponding shared-time position, clamped to that cell's duration.

Embedded mpv launches now include cache/readahead, `hwdec=auto-safe`, and faster scaling/downscaling options so HD/NAS files are less costly when rendered into small grid cells. Playback settings now include `Normalize local-video audio`, which enables mpv's `dynaudnorm` filter when selected. Hover enter/leave repositioning no longer animates native embedded video/browser window geometry, reducing flicker from expanded cells.

Browser cells now respond to app mute/unmute through QtWebEngine's page mute API and also run a small JavaScript hook to set standard `video`/`audio` element volume when the site permits it. Sites that isolate media in cross-origin frames or custom players may still ignore proportional volume changes.

The app toolbar now includes an in-app Diagnostics button. It shows the same dependency report as `playxls --diagnose`, including `libmpv` and the selected video backend, and tails `~/.local/state/playxls/playback-diagnostics.jsonl`.

## Latest Folder Scan Diagnostics

Background watched-folder scans now catch per-folder `OSError` failures and include them in the scanner refresh payload as `folder_errors`. The main window records those failures to the diagnostics JSONL file with `kind="folder_scan_failed"` and shows a toast with the folder name. This keeps one bad or unavailable NAS mount from killing the scanner thread silently.

## Latest Safe Mode

The GUI now supports `playxls --safe-mode`. It launches with saved settings, browser presets, and session layout, but skips watched-folder config loading, cached watched-library loading, and background folder scanning for that run. Saved watched-folder config is not modified. Video cells from the saved session are cleared because the watched library is intentionally unavailable, while browser cells can remain.

## Latest Diagnostics Export

The CLI now supports `playxls --export-diagnostics [ZIP]`. It exits before any GUI startup, writes a zip bundle containing `diagnose.txt`, `manifest.json`, selected TOML config/session files, `playxls.log` when present, and `playback-diagnostics.jsonl` when present. It intentionally excludes cache indexes and browser profile data so the bundle stays small and avoids dumping the full watched-library cache.

## Latest Playback Probe

The CLI now supports `playxls --probe-video SOURCE`. It runs before GUI startup and asks mpv to load one frame with null video/audio outputs, making it useful for separating file/codec/read failures from PlayXLS embedded-window failures. Successful probes return exit code 0; failed probes return exit code 1 with a cleaned mpv diagnostic.

## Latest MPV Diagnostics

Local-video assignment no longer treats creation of the mpv IPC socket as proof that playback loaded. `MpvController` now captures mpv's combined stdout/stderr tail, keeps loader diagnostics available with `--msg-level=all=warn`, and waits for actual loaded media state (`path` or `duration`) before reporting success. If mpv reaches idle after a loader error, PlayXLS treats that as a failed load and stores a cleaned `last_error` instead of leaving the cell in a broken-looking playback state.

Failed video cells now show `Playback failed` plus the mpv diagnostic inside the cell surface, emit `video_load_failed` through `CellWidget` and `GridStage`, and raise a toast from `MainWindow` with the affected cell number. Main window failures also append a JSONL record to `~/.local/state/playxls/playback-diagnostics.jsonl` with timestamp, cell, video id, title/source, and cleaned mpv message. Noisy shutdown lines such as mpv IPC write errors and GLib/GIO cleanup warnings are filtered out of the user-facing diagnostic.

`MpvController.stop()` now uses a bounded shutdown ladder: send mpv `quit`, wait briefly, `terminate()` if needed, wait again, then `kill()` as the final escalation. This keeps failed or wedged local-video loads from leaving stuck child processes behind after the cell clears or reloads.

Validation included a valid local-file smoke and an invalid-source smoke. The valid file loaded with a detected duration of about `21.48s`; the invalid source failed cleanly with mpv's unsupported-protocol diagnostic instead of appearing to load.

## Latest Performance Certification

Repeated preview hover certification used an off-screen XCB Qt harness with 15 temporary symlinked stock-video rows, real `MpvController` instances, and `PreviewPool(max_size=5)`. Results: 15 preview starts created 15 controllers over time, but the pool kept `max_pool_sources=5` and `max_alive_processes=5`; after `stop_all()`, `alive_after_stop=0`. Total elapsed was `11.300s`, average iteration `0.520s`, max iteration `0.692s`, and process RSS delta was about `3.8 MB`.

Large-library certification used the active 5,923-video cached NAS index in static thumbnail mode. `build_state()` loaded the cache in `1.180s`; initial library render took `0.501s`; repeated search/show-more rebuilds kept `max_rows=400` for the exercised flow and `max_native_thumbs=0`. A harness run exposed that static thumbnail rows were still calling `preview_pool.pause()` on destruction; `VideoRow._stop_preview()` now only calls pause in `preview_mode == "lazy"`, dropping static-mode pause calls from `4600` to `0` in the same stress flow.

## Latest Splitter Persistence

The main Sources/stage splitter now persists through the existing session file. `SessionState` and `AppState` carry `main_splitter_sizes`; `MainWindow` restores those sizes during shell construction and captures the current `QSplitter.sizes()` whenever `_save_session()` runs. Old sessions without splitter data still fall back to the existing `[320, 960]` default, and invalid saved sizes are ignored.

## Latest NAS Playback Fix

User reported that browser playback from YouTube worked, but assigning a NAS watched-folder video never played and then caused UI flicker. Direct mpv probing showed the NAS file was readable and playable when mpv was not embedded. A Qt Wayland embed probe reproduced the real failure: passing a Qt Wayland native window id to mpv's current `--wid` subprocess backend made mpv exit with `BadWindow` before playback.

Fix: `choose_qt_platform()` now prefers Qt's `xcb` backend whenever a `DISPLAY` is available and `libxcb-cursor0` is installed, including on Wayland desktops with XWayland. Explicit `QT_QPA_PLATFORM` still wins. This keeps the current libmpv/subprocess `wid` embedding path on the X11/XWayland surface model it requires until the project moves to a lower-level render API or another native backend.

Validation: a temporary XCB PlayXLS smoke assigned one cached NAS video to a 1x1 grid. mpv stayed alive, exposed an IPC socket, and transport snapshots advanced from about `0.06s` to `1.89s` with a detected duration of about `473s`.

## Latest Pluto Browser Notice

Pluto.tv can render and allow sign-in inside QtWebEngine, but the playback path reported `Player:2 ErrorNotSupported` / `No playable format` from site JavaScript. `browser_compatibility_notice()` now flags `pluto.tv` with `Playback limited`, which appears in both the Sources browser list and the active browser toolbar next to the existing system-browser handoff.

## Latest Layout Management

The layout menu now includes a `Delete Custom Layout` submenu when saved custom layouts exist. Delete actions are only generated for `LayoutDefinition.custom == True`, so built-in presets are protected. Deleting a non-current custom layout removes it from memory and rewrites `layouts.toml` with the remaining custom layouts. Deleting the active custom layout falls back to the first built-in preset, saves the session, persists the remaining custom layouts, and refreshes the UI.

## Latest Browser Hardening

DRM-limited service notices now appear in the Sources browser list as well as the active browser toolbar. `BrowserRow` uses the same pure `playxls.browser.browser_compatibility_notice()` classifier as the toolbar, so Netflix, Disney+, Prime Video, Max, and HBO Max show `DRM limited` before the source is assigned to a cell.

QtWebEngine load failures now use `QWebEnginePage.loadingChanged` details when available. `playxls.browser.browser_load_failure_message()` formats Qt error strings/codes such as `net::ERR_NAME_NOT_RESOLVED (-105)` and falls back to the failed host. `CellWidget` keeps the richer `loadingChanged` failure from being overwritten by a later generic `loadFinished(False)`, while preserving `loadFinished(False)` as a fallback for builds or cases without detailed loading info.

Toolbar failure notices still take priority over generic DRM warnings and still point users to the system-browser handoff.

Live QtWebEngine validation loaded YouTube, Twitch, Netflix, Prime Video, Disney+, and Max successfully through the PlayXLS `CellWidget` path. Final URLs/titles were captured, including Prime Video's non-prime redirect and Max's redirect to `hbomax.com`; no load failures were emitted for the landing pages. This does not validate login or protected playback.

## Latest Cached Startup Fix

Startup no longer walks every configured watched folder before the window appears. `ConfigStore` now persists a watched-library index at `~/.cache/playxls/library_index.toml`, and `build_state()` loads videos from that cache instead of calling `scan_folder()` on startup.

The folder scanner now supports:

- a seeded `seen_paths` set so startup can avoid synchronous priming;
- one-batch refresh callbacks instead of thousands of per-file UI updates;
- a 1-second initial background delay followed by 30-second polling.

`MainWindow._folder_scan_refreshed()` applies scanner batches on the Qt thread, updates folder counts, filters ignored videos, clears cells for removed files, saves the refreshed cache only when the scan result changed, and syncs the library UI once. If a refresh returns the same paths and counts, it returns before cache rewriting or UI resync.

The current NAS cache was seeded once during this session:

```text
cached=5923 folders=[('01_Main Collection', 4336), ('Taboos', 1587)]
```

After that, `build_state()` loaded the 5,923 cached videos in `0:01.34`, and the Qt Wayland smoke loaded the cached library, rendered 200 rows, created 0 native thumbnail windows, and exited in `0:02.65`. A timed launch that allowed the background refresh to complete saw one refresh at about `8.88s`; after the no-op optimization, the unchanged refresh callback took `0.002s` and the max 100 ms event-loop tick gap was `0.106s`.

## Latest NAS Library Fix

User added two SMB/GVfs watched folders on a NAS with 5,923 discovered video files, after which PlayXLS froze on startup and sometimes aborted with:

```text
The Wayland connection experienced a fatal error: Too many references: cannot splice
```

Root cause: startup scanned the NAS folders, then the Sources library eagerly created one `VideoRow` and one native thumbnail window per discovered video. With thousands of rows, that put heavy pressure on Wayland/native child window resources before a file could even be played. The app also synchronously primed the folder watcher after the startup scan, duplicating an expensive NAS walk.

Fix:

- Library rendering now starts with the first 200 matching rows and adds a `Show N more` action for incremental expansion.
- Static thumbnail mode no longer marks every row thumbnail as a native window. Native thumbnail windows are only created for live lazy previews.
- Folder scanner startup can be seeded with already loaded library paths, so `MainWindow` skips the duplicate synchronous prime after `build_state()`.
- The fallback folder scanner interval is now 30 seconds instead of 5 seconds, reducing repeated NAS polling pressure.

The first fix smoke against the user's active config loaded 5,923 videos, rendered 200 rows, created 0 native thumbnail windows in `thumb` mode, and exited cleanly via timed auto-quit.

## Latest Browser Profile Fix

The previous slice changed embedded browser profiles from per-cell-only to shared-by-default. Browser cells now use one reused `QWebEngineProfile` object backed by `~/.cache/playxls/browser/shared/{storage,cache}` unless the user switches Advanced settings to per-cell isolation, which uses `~/.cache/playxls/browser/cell-N/{storage,cache}`.

## Latest Browser Fix

User reported blank white pages for browser cells and cell-local controls visually hidden behind the page surface. Root cause: the first shared-profile implementation gave each cell a separate `QWebEngineProfile` object pointed at the same Chromium profile/cache directory. Simultaneous cells could contend for the same disk cache and fail to finish page loads. The cell-local control strip also could not reliably coexist inside the same cell as a QtWebEngine native child window on X11.

Fix:

- Reuse a single cached shared `QWebEngineProfile` object for shared profile mode.
- Keep per-cell mode as individually owned profiles.
- Remove browser controls from individual browser cells entirely.
- Browser cells now contain only the web surface plus PlayXLS overlay controls.
- Add a normal app-level browser toolbar above the stage. It targets the active/hovered browser cell and owns back, forward, reload, and URL navigation.
- Keep browser web views as manually positioned direct children so they are not layout-managed with unrelated chrome.

## Earlier Browser Hardening

The app-level browser toolbar shows a short `DRM limited` compatibility notice when the active browser cell points at known protected-video services such as Netflix, Disney+, Prime Video, Max, or HBO Max. The notice is intentionally outside the QtWebEngine cell surface so it avoids the same X11 stacking problem that affected in-cell controls.

The classifier is pure URL-based behavior in `playxls.browser.browser_compatibility_notice`, so future service-specific handling can be tested without constructing Qt widgets.

The same toolbar now includes an external-open handoff button for the active browser cell. It opens the assigned/current URL through `QDesktopServices.openUrl`, with the callable kept injectable as `MainWindow.open_external_url` for tests. This gives DRM-limited services and login-hostile embedded flows a clear system-browser escape path.

QtWebEngine load failures flow from `CellWidget` to `GridStage` to `MainWindow`. A later successful load clears the failure state, and failure notices take priority over generic DRM-limited notices.

## Latest Transport Hardening

Local-video cells no longer expose mpv's own OSC/OSD/default input bindings inside each embedded cell. `MpvController` now builds subprocess args with `--osc=no`, `--osd-level=0`, and `--input-default-bindings=no`, keeping playback controls in PlayXLS' app-level transport and reducing hover-expansion interference.

The app-level transport now includes repeat and shuffle controls with persisted session state:

- `repeat off`
- `repeat 1`
- `repeat all`
- `repeat folder`
- `shuffle off/on`

`repeat 1` pushes `loop-file=inf` to running local mpv instances. `repeat all`, `repeat folder`, and shuffle now auto-advance when mpv reports `eof-reached`; the next-video selection lives in pure `playxls.queueing.next_video_for_repeat()` and is covered independently from the Qt transport wiring.

User manually confirmed that shared browser login persists across cells, and browser-video fullscreen is correctly confined to the cell.

## Latest Hover Fix

User reported that hover expansion only stacked correctly for Cell 4; Cells 1, 2, and 3 expanded underneath later cells and were clipped. Root cause: `GridStage.reposition()` raised every cell in index order on each layout pass, which made the last cell topmost unless a cell was fullscreen. Hover expansion changed geometry but did not change stacking.

Fix: after normal layout positioning, `GridStage.reposition()` now raises the hovered cell above siblings when no cell fullscreen is active. A Qt regression test verifies that an expanded hovered Cell 1 is the top widget at an overlap point that previously returned Cell 4.

## Verification

Latest full verification:

```bash
QT_QPA_PLATFORM=offscreen QTWEBENGINE_DISABLE_SANDBOX=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_video.py tests/test_playback_state.py tests/test_browser_cell.py tests/test_main_window_transport.py
QT_QPA_PLATFORM=offscreen QTWEBENGINE_DISABLE_SANDBOX=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_main_window_transport.py tests/test_browser_cell.py tests/test_video.py tests/test_queueing.py tests/test_models.py tests/test_config.py tests/test_preview.py tests/test_playback_state.py tests/test_settings_dialog.py
QT_QPA_PLATFORM=offscreen QTWEBENGINE_DISABLE_SANDBOX=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from pathlib import Path
files = sorted(Path('playxls').rglob('*.py'))
for path in files:
    compile(path.read_text(), str(path), 'exec')
print(f'compiled {len(files)} Python source files')
PY
.venv/bin/playxls --diagnose
```

Results:

- Focused transport/browser/playback/settings tests after transport and playback tuning: `90 passed in 3.49s`
- Focused diagnostics/playback/browser transport tests: `53 passed in 2.72s`
- Focused config/playback/video/main-window transport tests after adding persistent playback diagnostics: `50 passed in 2.59s`
- Focused video/playback/main-window transport tests after adding mpv shutdown escalation: `42 passed in 2.50s`
- Focused app/config diagnostics-export tests: `14 passed in 0.21s`
- Focused app/video playback-probe tests: `19 passed in 0.22s`
- Focused startup/app safe-mode tests: `13 passed in 0.21s`
- Focused folder/main-window scan failure diagnostics tests: `29 passed in 2.51s`
- Focused libmpv/backend/playback tests: `34 passed in 0.45s`
- Full suite after libmpv migration: `149 passed in 4.63s`
- `compiled 22 Python source files`
- Diagnostics found `/usr/bin/mpv`, PySide6, QtWebEngine, `libxcb-cursor.so.0`, `libmpv: libmpv.so.2`, `video backend: libmpv`, and now selects Qt platform `xcb`.
- Xvfb libmpv smoke generated `/tmp/playxls-libmpv-smoke.mp4`; `preferred_mpv_controller()` selected `LibMpvController`, loaded successfully, kept `last_error=''`, and detected duration `1.0`.
- Diagnostics export smoke wrote `/tmp/playxls-diagnostics-smoke.zip` with `diagnose.txt` and `manifest.json`; the watched-library cache index was excluded.
- Playback probe smoke against a harmless missing file returned exit status `1` and surfaced mpv's missing-file diagnostic.
- Safe-mode startup smoke against the active config launched with `folders=0`, `videos=0`, and no folder scanner.
- Valid local-file smoke: `MpvController.load()` returned true, kept `last_error=''`, and detected a `21.48s` duration.
- Invalid-source smoke: `MpvController.load()` returned false with a cleaned unsupported-protocol mpv diagnostic.
- Cached `build_state()` smoke: `videos=5923 folders=[('01_Main Collection', 4336), ('Taboos', 1587)]`, elapsed `0:01.34`.
- Cached Wayland startup smoke: `videos=5923 rendered_rows=200 native_thumbs=0 scanner_delay=1.0`, elapsed `0:02.65`.
- Cached NAS playback XCB smoke: mpv process remained alive, IPC existed, and position advanced from about `0.06s` to `1.89s` with duration about `473s`.
- Background refresh timing smoke: `callback_durations=[0.002]`, `max_tick_gap=0.106`.
- Live PlayXLS browser-cell landing-page validation: YouTube, Twitch, Netflix, Prime Video, Disney+, and Max all emitted successful page loads with no failure notices.
- X11 screenshot validation saved `/tmp/playxls-browser-grid.png`, `/tmp/playxls-browser-drm-notice.png`, and `/tmp/playxls-browser-external-button.png`; the app-level toolbar was visible, selected browser cells rendered, and the `DRM limited` notice plus external-open button fit without crowding the URL field.
- Transport screenshot validation saved `/tmp/playxls-transport-repeat-shuffle.png`; repeat/shuffle controls fit at `960x620`.
- Hover stack screenshot saved `/tmp/playxls-hover-stack.png`; expanded Cell 1 rendered above overlapping cells.

## Next Steps

1. Run full test suite after any follow-up code edits.
2. Continue interactive site-by-site validation for login, fullscreen, and protected playback where credentials/playback access are available.
3. Validate direct libmpv against real NAS HD files and decide whether the next backend milestone is keeping `wid` embedding or moving to libmpv's lower-level render API.
4. Continue watching the new playback diagnostics log during real NAS playback tests and use it to decide whether failures are codec/container issues, embed/window issues, or backend crashes.
