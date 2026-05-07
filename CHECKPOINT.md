# PlayXLS Checkpoint

Updated: 2026-05-07

## Current State

PlayXLS is a Python 3.12 + PySide6/Qt 6 native desktop app. It runs from the project virtualenv:

```bash
cd /home/ai-agents/Projects/PlayXLS
.venv/bin/playxls --diagnose
.venv/bin/playxls
```

The latest slice changed embedded browser profiles from per-cell-only to shared-by-default. Browser cells now use one reused `QWebEngineProfile` object backed by `~/.cache/playxls/browser/shared/{storage,cache}` unless the user switches Advanced settings to per-cell isolation, which uses `~/.cache/playxls/browser/cell-N/{storage,cache}`.

## Latest Browser Fix

User reported blank white pages for browser cells and cell-local controls visually hidden behind the page surface. Root cause: the first shared-profile implementation gave each cell a separate `QWebEngineProfile` object pointed at the same Chromium profile/cache directory. Simultaneous cells could contend for the same disk cache and fail to finish page loads. The cell-local control strip also could not reliably coexist inside the same cell as a QtWebEngine native child window on X11.

Fix:

- Reuse a single cached shared `QWebEngineProfile` object for shared profile mode.
- Keep per-cell mode as individually owned profiles.
- Remove browser controls from individual browser cells entirely.
- Browser cells now contain only the web surface plus PlayXLS overlay controls.
- Add a normal app-level browser toolbar above the stage. It targets the active/hovered browser cell and owns back, forward, reload, and URL navigation.
- Keep browser web views as manually positioned direct children so they are not layout-managed with unrelated chrome.

## Latest Browser Hardening

The app-level browser toolbar now shows a short `DRM limited` compatibility notice when the active browser cell points at known protected-video services such as Netflix, Disney+, Prime Video, Max, or HBO Max. The notice is intentionally outside the QtWebEngine cell surface so it avoids the same X11 stacking problem that affected in-cell controls.

The classifier is pure URL-based behavior in `playxls.browser.browser_compatibility_notice`, so future service-specific handling can be tested without constructing Qt widgets.

The same toolbar now includes an external-open handoff button for the active browser cell. It opens the assigned/current URL through `QDesktopServices.openUrl`, with the callable kept injectable as `MainWindow.open_external_url` for tests. This gives DRM-limited services and login-hostile embedded flows a clear system-browser escape path.

QtWebEngine load failures now flow from `CellWidget` to `GridStage` to `MainWindow`. When the active browser cell reports `loadFinished(False)`, the toolbar shows `Load failed` with a tooltip pointing users to the system-browser handoff. A later successful load clears the failure state, and failure notices take priority over generic DRM-limited notices.

## Latest Transport Hardening

Local-video cells no longer expose mpv's own OSC/OSD/default input bindings inside each embedded cell. `MpvController` now builds subprocess args with `--osc=no`, `--osd-level=0`, and `--input-default-bindings=no`, keeping playback controls in PlayXLS' app-level transport and reducing hover-expansion interference.

The app-level transport now includes repeat and shuffle controls with persisted session state:

- `repeat off`
- `repeat 1`
- `repeat all`
- `repeat folder`
- `shuffle off/on`

`repeat 1` also pushes `loop-file=inf` to running local mpv instances; other repeat/shuffle modes are now represented in state/UI and are ready for the next queue/folder auto-advance slice.

User manually confirmed that shared browser login persists across cells, and browser-video fullscreen is correctly confined to the cell.

## Verification

Latest full verification:

```bash
QT_QPA_PLATFORM=offscreen QTWEBENGINE_DISABLE_SANDBOX=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider
QT_QPA_PLATFORM=offscreen QTWEBENGINE_DISABLE_SANDBOX=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_browser.py tests/test_browser_cell.py tests/test_config.py tests/test_settings_dialog.py tests/test_main_window_transport.py
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

- Transport/config focused tests: `26 passed in 1.87s`
- Full suite: `80 passed in 2.90s`
- `compiled 21 Python source files`
- Diagnostics found `/snap/bin/mpv`, PySide6, and QtWebEngine.
- X11 screenshot validation saved `/tmp/playxls-browser-grid.png`, `/tmp/playxls-browser-drm-notice.png`, and `/tmp/playxls-browser-external-button.png`; the app-level toolbar was visible, selected browser cells rendered, and the `DRM limited` notice plus external-open button fit without crowding the URL field.
- Transport screenshot validation saved `/tmp/playxls-transport-repeat-shuffle.png`; repeat/shuffle controls fit at `960x620`.

## Next Steps

1. Run full test suite after any follow-up edits.
2. Implement queue/folder auto-advance semantics for repeat all, repeat folder, and shuffle.
3. Decide whether browser limitation notices should also appear in the Sources browser list, not only the active toolbar.
4. Capture richer site-specific QtWebEngine failure details if Qt exposes useful error codes beyond `loadFinished(False)`.
