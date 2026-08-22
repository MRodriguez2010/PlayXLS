# PlayXLS — Project Context

## Purpose

PlayXLS is an Ubuntu-first native multi-stream video workspace. It places local/NAS video and browser sources into configurable tile-tree layouts, persists sessions and source settings, and provides app-level playback, browser, diagnostics, and recovery controls.

## Current reality

- The production implementation is Python 3.12 with PySide6/Qt 6.
- Local video prefers direct libmpv through `python-mpv` and retains an mpv subprocess fallback.
- Browser cells use QtWebEngine with shared or per-cell local profiles.
- Large watched-folder libraries use a cached index and bounded rendering; runtime media and indexes are not stored in Git.
- The checkpoint records 149 passing tests plus focused playback, browser, diagnostics, and performance evidence from May 2026.
- Ubuntu is the only validated target. Packaging, cross-platform support, sustained-use certification, and protected-service playback remain incomplete.

## Core capabilities

- preset and custom tile-tree layouts;
- one-to-many local video playback with unified transport and timeline;
- watched folders, cached NAS library startup, filters, and bounded row rendering;
- hover previews through a bounded controller pool;
- browser cells with persistent profiles and system-browser handoff;
- repeat, shuffle, resume, mute, volume, and per-cell assignment persistence;
- safe-mode startup, playback probe, dependency diagnostics, and bounded diagnostics export;
- recovery-oriented error surfaces for media loads and background scans.

## Repository map

| Path | Role |
| --- | --- |
| `playxls/` | Native application source. |
| `tests/` | Pure and Qt-aware regression suite. |
| `README.md` | Setup, current capabilities, tests, and native dependencies. |
| `CHECKPOINT.md` | Detailed implementation evidence and resume point. |
| `MIGRATION_FROM_PROTOTYPE.md` | Porting decisions and remaining architecture gaps. |
| `Initial_Demo/` | React design/behavior reference, not the production runtime. |
| `playxls-logo-pack/` | Product identity assets and usage guidance. |

## Source, data, and privacy boundaries

- The owner-designated local checkout is the active source. This private GitHub repository is a secondary source/history backup.
- Videos, watched-folder contents, NAS paths, cached indexes, sessions, browser profiles/cookies, playback history, diagnostics exports, and user configuration do not belong in GitHub.
- Diagnostics should remain bounded and should not include browser-profile data or private media indexes.
- The product is content-agnostic, but real libraries can be highly sensitive. Tests, demos, screenshots, and a future public repository must use synthetic or redistributable media.

## Run and test

Follow `README.md` for the complete dependency notes. The normal development flow is:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[gui,watch,streams,test]'
.venv/bin/playxls --diagnose
.venv/bin/pytest -q
python -m compileall playxls
```

GUI success depends on host Qt/mpv libraries and display mode. A headless test pass does not prove embedded playback, protected browser playback, or long-session stability.

## Architecture constraints

- Current mpv rendering still relies on an X11/XWayland `wid` embedding path even when direct libmpv control is selected.
- QtWebEngine cannot guarantee playback for DRM-heavy services and some login flows; the system-browser handoff is intentional.
- Browser and local-video sources do not expose one uniform timing/control API.
- Runtime scanning and UI construction must remain bounded for multi-thousand-file libraries.

## Maturity and launch path

- **Current phase:** substantial functional prototype / private alpha.
- **Website showcase:** ready for a controlled demo and case study using synthetic media.
- **Sellable-product potential:** high for a privacy-first local/NAS multi-view player, monitoring workspace, or creator/research dashboard.
- **Before paid release:** installer/package and update strategy, license review for mpv/Qt/browser components, crash recovery, sustained performance, explicit telemetry policy, support boundaries, and validation on every advertised platform.
- **Public-source candidate:** a sanitized duplicate can be credible after removing any private-media references/history and adding redistributable fixtures, CI-safe headless tests, contribution/security docs, and reproducible packaging.

## Resume point

Run the full suite after any code edit, then validate real HD/NAS media through the direct libmpv path, decide whether to keep `wid` or adopt the lower-level render API, and observe bounded playback diagnostics during sustained use. Packaging remains the final milestone after backend and browser behavior settle.
