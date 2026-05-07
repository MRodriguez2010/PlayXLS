# Migration From Prototype

The React prototype in `Initial_Demo/playxls_demo.jsx` is the visual and behavioral source of truth. This native build ports the shell, source tabs, tile-tree layout model, settings model, theme tokens, keybindings, hover behavior, layout picker/editor, and cell-confined fullscreen concept into Python + PySide6.

## Intentional Divergences In This Build

- **Video backend:** PlayXLS now prefers direct libmpv through the `python-mpv` binding when `libmpv` is loadable. The previous embedded `mpv` subprocess with JSON IPC remains as fallback for machines without the binding or system library. `playxls --diagnose` and the in-app Diagnostics dialog report both `libmpv` availability and the selected video backend.
- **Current libmpv rendering path:** The new libmpv adapter still embeds into Qt native child windows through mpv's `wid` option. A later backend milestone can move to the lower-level libmpv render API if pure Wayland rendering or finer GPU control becomes necessary.
- **Snap mpv IPC fallback:** When fallback `/snap/bin/mpv` is used, PlayXLS puts the JSON IPC socket under `~/PlayXLS Runtime/mpv-ipc` because Snap mpv cannot bind sockets in hidden home directories such as `~/.cache`.
- **Browser cells:** The prompt prefers WebKitGTK for GTK or QtWebEngine for Qt. This build uses QtWebEngine when the optional PySide6 WebEngine module is installed and shows a native placeholder otherwise. Page fullscreen requests are accepted and kept inside the current browser cell; they do not trigger PlayXLS stage fullscreen. Browser cells use persistent profile paths. This still needs site-by-site validation against services with custom video players and DRM requirements.
- **Browser profile scope:** Browser storage now defaults to one reused PlayXLS QtWebEngine profile so logins/cookies can work across browser cells without multiple Chromium profile objects contending for the same disk cache. The Advanced settings page keeps an isolated per-cell profile option for users who want cell-local sessions.
- **Browser controls:** Controls moved out of individual browser cells into an app-level browser toolbar because QtWebEngine's native X11 child window repeatedly clipped or obscured in-cell Qt controls. The toolbar targets the active/hovered browser cell.
- **Hover previews:** Lazy hover previews are implemented through a bounded mpv LRU preview pool and now use the preferred libmpv/subprocess backend factory. The current `wid` render target still reloads when the same source is previewed in a different native window; a future render-API backend can make render-target detach/reattach cheaper.
- **Grid editor:** Presets, split, remove, undo, reset, and save exist. Drag handles and per-cell click selection are simplified in this slice.
- **Packaging:** Flatpak and `.deb` manifests are deliberately deferred until the end of the build. Backend, browser behavior, cross-platform runtime choices, and performance budgets should settle before packaging work begins.
- **Performance certification:** Long-run CPU/memory budgets are not certified yet. `playxls --diagnose` exposes the local dependency state for the next profiling pass.
- **Host Qt runtime:** X11 launches require Ubuntu's `libxcb-cursor0` package. The launcher detects the missing library and exits with install guidance instead of letting Qt abort.

## Platform Target

Development is happening on Ubuntu Linux first, with Ubuntu as the first validation target. The finished app should also be usable on macOS and Windows, so backend and packaging decisions should avoid Linux-only assumptions where a cross-platform Qt/mpv path is practical. Platform-specific behavior should be isolated behind adapters.

## Keep From Prototype

- 36px title bar, 300px unified sidebar, 48px toolbar, 56px transport.
- Dark/light theme token semantics with amber accent.
- Binary tile-tree layouts rather than CSS grid assumptions.
- Sparse toolbar: layout, borders, hover, settings.
- Source tabs: Library, Folders, Browser.
- Settings sections: Appearance, Playback, Library, Shortcuts, Advanced.
- Cell assignment persistence by index when layouts change.
- Stage-confined fullscreen rather than whole-window fullscreen.

## Next Native Milestones

1. Validate direct libmpv against real NAS HD files and decide whether to keep `wid` embedding or move to libmpv's lower-level render API.
2. Validate and harden browser profile sharing, fullscreen, and cookie/session behavior against YouTube/Twitch/Netflix-style players.
3. Add splitter drag handles to the grid editor and the live stage.
4. Certify performance and memory behavior under sustained multi-video use, including preview hovers.
5. Final step only: add Flatpak, `.deb`, and platform-specific packaging/build verification.
