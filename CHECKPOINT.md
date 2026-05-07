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

- Browser/config/settings focused tests: `33 passed in 2.14s`
- Full suite: `72 passed in 3.12s`
- `compiled 21 Python source files`
- Diagnostics found `/snap/bin/mpv`, PySide6, and QtWebEngine.
- X11 screenshot validation saved `/tmp/playxls-browser-grid.png` and `/tmp/playxls-browser-drm-notice.png`; the app-level toolbar was visible, selected browser cells rendered, and the `DRM limited` notice fit without crowding the URL field.

## Next Steps

1. Run full test suite after any follow-up edits.
2. Manually validate YouTube/Twitch browser cells with shared-profile cookies and page fullscreen.
3. Add an explicit “open in system browser” handoff if DRM-limited services or login flows need it.
4. Capture site-specific QtWebEngine failure states and route them into concise user-facing messages.
