# Build: PlayXLS — A multi-stream video player for Ubuntu

You are building **PlayXLS** (pronounced "play-axles"), a desktop video player for Ubuntu Linux that goes well beyond what mpv, VLC, or GridPlayer offer. Its identity is *multi-stream by default*: every layout, interaction, and setting assumes the user may be watching one video, four videos, or a mix of videos and live web streams simultaneously. The reference design has already been prototyped as a React/HTML demo — your job is to ship a real native Linux application with the same UX and the same visual language.

A working interactive UI/UX prototype exists (single-file React component, ~1500 lines) demonstrating the full interaction model: layout switching with thumbnail picker, custom grid editor, hover-expand, hover-volume, library hover previews, browser cells, cell-confined fullscreen, streamlined settings dialog, keybind recording, and full light/dark theme support. Use it as the visual and behavioral source of truth — match the layout, spacing, color treatment, typography hierarchy, and interaction timings rather than reinventing them.

---

## Tech stack

**Required**:
- **Language/runtime**: Rust (preferred for performance) OR Python with PyQt6/PySide6. Pick one and commit.
- **GUI toolkit**: GTK4 + libadwaita (most native on modern Ubuntu/GNOME), or Qt 6 if you went Python. Avoid Electron — the multi-video performance budget cannot afford it.
- **Video backend**: libmpv (mpv embedded as a library). Each grid cell is its own mpv instance with shared event loop. Do not use GStreamer directly unless libmpv proves insufficient — mpv handles 95% of codec/format edge cases for free.
- **Browser cells**: WebKitGTK (if GTK) or QtWebEngine (if Qt). One webview per browser cell. Must support persistent cookies/sessions per-cell.
- **HLS streaming**: shell out to `streamlink` and `yt-dlp` as subprocesses; resolve to a direct URL, hand it to mpv.
- **Filesystem watching**: `inotify` via the `notify` crate (Rust) or `watchdog` (Python).
- **Settings storage**: TOML or JSON in `~/.config/playxls/`. Do not use dconf/gsettings — keep the app self-contained.
- **Packaging**: Flatpak as primary distribution (sandboxed, works across all Ubuntu versions). `.deb` as secondary. Snap if you must, but Flatpak first.

**Forbidden**:
- Electron, Tauri webviews for the main UI (webviews only inside browser cells)
- Hardcoded GPU vendor assumptions
- Bundled ffmpeg if libmpv already pulls it in

---

## Visual design

Match the prototype exactly. The aesthetic is **disciplined, minimal, app-native** — not Spotify, not VLC, not generic "media center." It should feel like a tool a Linux power user would respect: tight spacing, consistent typography, no decorative flourish.

### Themes — first-class light + dark

The app must ship with both **dark** (default) and **light** themes, plus a system-following option. The toggle lives in the title bar (Sun/Moon icon) and is also bound to **Ctrl+T**. Settings → Appearance also has a Theme segmented control.

Every color must flow through a theme token object. Do not hardcode color values in components — pull from the active theme. The two themes share the same amber accent semantically; the value differs to maintain WCAG contrast on both backgrounds.

**Dark theme tokens**:
```
bg              #0a0a0c   (root background)
surface1        #0d0d10   (sidebar)
surface2        #15151a   (elevated, popovers, settings panels)
surface3        #1c1c20   (hover, sliders, segmented backgrounds)
titleBar        #0f0f12

border          #1c1c20
borderStrong    #2a2a30

textPrimary     #e7e5e4   (stone-200)
textSecondary   #a8a29e   (stone-400)
textTertiary    #78716c   (stone-500)
textMuted       #57534e   (stone-600)

accent          #fbbf24   (amber-400)
accentBg        rgba(251, 191, 36, 0.15)
accentBorder    rgba(251, 191, 36, 0.40)
danger          #f43f5e   (rose-500 — fullscreen badges, delete confirms)
success         #34d399   (emerald-400 — live folders, currently-playing)

cellBg          #000000   (always black; videos render on black regardless of theme)
cellEmpty       #0c0c10
onAccent        #1c1917   (text on amber buttons)
```

**Light theme tokens**:
```
bg              #fafaf9
surface1        #ffffff
surface2        #f5f5f4
surface3        #e7e5e4
titleBar        #f5f5f4

border          #e7e5e4
borderStrong    #d6d3d1

textPrimary     #1c1917
textSecondary   #44403c
textTertiary    #78716c
textMuted       #a8a29e

accent          #d97706   (amber-600 — deeper for contrast on light)
accentBg        rgba(217, 119, 6, 0.10)
accentBorder    rgba(217, 119, 6, 0.40)
danger          #e11d48
success         #059669

cellBg          #000000   (videos still on black)
cellEmpty       #f5f5f4
onAccent        #ffffff
```

### Typography

- **Body**: Inter, weights 300/400/500/600
- **Mono**: JetBrains Mono, weights 400/500 — for shortcuts, paths, technical labels, all-caps eyebrows with letter-spacing

No display serif. The prototype dropped Fraunces in favor of Inter throughout — keep it that way. The interface should feel app-native, not editorial.

### Spacing & sizing

- Title bar: 36px tall
- Single sidebar: 300px wide (no separate workspace rail)
- Toolbar: 48px tall
- Transport bar: 56px tall
- Cell number badges: 20px tall, monospace, rounded
- Standard rounded corners: 4–6px

### Motion

- Cell layout transitions: `350ms cubic-bezier(.4, 0, .2, 1)` for left/top/width/height
- Hover expand scale: `300ms` ease-out
- Other cells dim to `brightness(0.55)` when one is hover-expanded
- Border fade-in/out: ~300ms; auto-hide after 900ms when not near edges
- Toast notifications: 2200ms total, fade-in 200ms
- Theme transition: instant (no cross-fade — feels laggy)

---

## Window & navigation structure

```
┌──────────────────────────────────────────────────────────────────────┐
│ Title bar: window controls · PlayXLS · theme toggle · grid metadata  │
├──────────────┬──────────────────────────────────────────────────────┤
│              │ Toolbar: [Layout ▼] · borders · hover ▼ · ⋯ · ⚙       │
│              ├──────────────────────────────────────────────────────┤
│   Sidebar    │                                                      │
│   (Sources   │              Cell Grid (the stage)                   │
│    tabs +    │                                                      │
│    content)  │                                                      │
│              ├──────────────────────────────────────────────────────┤
│              │ Transport: ▶ · vol · seek bar · SYNCED                │
└──────────────┴──────────────────────────────────────────────────────┘
```

**No left workspace rail.** A previous design iteration had a 56px-wide icon rail (Library / Folders / Browser / Bindings). It was redundant and was removed during streamlining. Bindings now lives inside Settings; Library / Folders / Browser are tabs at the top of the unified sidebar.

**Sidebar header** (top of sidebar):
- Small uppercase mono "Sources" eyebrow
- Three-tab segmented control: **Library** · **Folders** · **Browser**
- Tab body fills the rest of the sidebar (search, content list, footer actions)

---

## Cell content model

A cell is one of three types:

```rust
enum CellContent {
    Empty,
    Video { video_id: String },
    Browser { url: String, name: String },
}
```

The grid maintains a vector of `CellContent` long enough to cover the maximum cells in any saved layout. When the layout changes, cell assignments persist by index — switching from 2x2 back to 1x1 then back to 2x2 should restore the same content.

---

## Grid system (tile-tree model)

Layouts are **binary trees**, not CSS grids. Leaves are cells; internal nodes are splits.

```rust
enum LayoutNode {
    Leaf,
    Split {
        direction: SplitDirection, // V (side-by-side) or H (stacked)
        ratio: f32,                 // 0.1 to 0.9
        a: Box<LayoutNode>,
        b: Box<LayoutNode>,
    },
}
```

This is what enables the asymmetric "1 large + 2 stacked" layout: split root vertically at 0.6, then split the right child horizontally at 0.5. Any cell can be recursively split, producing arbitrary tile-window-manager layouts (think i3, Rectangle, FancyZones).

**Required preset layouts** ship with the app:
- Single (1×1)
- 1 × 2 (side-by-side)
- 1 × 3 (three columns)
- 2 × 2
- 3 × 3 (nine cells)
- 1 + 2 stack (one large left, two stacked right) — *this layout is non-negotiable*

**Custom layouts** are saved by the user with a name and persist to `~/.config/playxls/layouts.toml`. They appear in the Layout picker dropdown (see toolbar section) with delete affordance on hover. Saved layouts must round-trip lossless through the config file.

**Grid Editor** (modal, reachable via Ctrl+E or "Create Custom Layout" button at the bottom of the layout picker):
- Click a cell → it highlights amber
- Buttons: split vertical, split horizontal, remove cell (disabled when nothing selected or when removing root)
- Drag the orange handles between cells to resize ratios live (clamp 0.1 to 0.9)
- "Templates" section in the left rail of the editor (Single, 1+2 stack, 2 stack, 1×3, 2×2)
- Undo button (history stack), Reset button
- Name field at bottom + Save Layout button (amber primary action)

**Cell rendering**:
- Each cell is positioned absolutely as a percentage of stage area
- When borders are visible, each cell shrinks by `0.4%` in all directions (creates the gap effect)
- When borders are hidden (`borderMode === "never"` or hover-mode without proximity), cells touch seamlessly
- Cells animate position/size on layout change with the 350ms cubic-bezier above

---

## Border modes

Three modes, settable in the toolbar (cycling button) and Settings → Appearance:

1. **Always** — borders permanently visible, 1px ring in `border` color, rounded corners, slight gap between cells
2. **Hover** (default) — borders hidden by default. Mousing within ~12px of the stage's outer edges fades them in. After 900ms of the mouse leaving the edge zone, they fade out again.
3. **Never** — borders never appear; cells touch seamlessly forever.

Implement edge-detection zones as transparent 12px-wide strips along the top, left, and right of the stage that trigger the fade-in on `mouseenter`. The bottom edge does not trigger (transport bar handles that area).

The `B` keyboard shortcut cycles modes and shows a toast.

---

## Hover behaviors (cell-level)

When the mouse enters a cell, it becomes the "hovered cell." Two configurable behaviors, both surfaced through a single **Hover popover** in the toolbar (consolidated from two separate buttons in the previous design):

### Hover Expand
- Toggle: on/off
- Slider: 105% to 200% (default 140%)
- The hovered cell scales by that percentage
- Other cells dim to `brightness(0.55)`
- The expanding cell anchors its `transform-origin` toward the *inside* of the grid:
  - Cells in the left third anchor `left`; right third anchors `right`; middle anchors `center`
  - Same logic for vertical (top/center/bottom)
- This prevents cells from clipping off-screen when expanding
- Cell `z-index` jumps to 20 while hovered so it overlaps neighbors

### Hover Volume
- Toggle: on/off
- Mode segmented control: "Boost hovered" or "Duck hovered"
- Slider: 10% to 80% delta (default 40%)
- **Boost mode**: hovered cell volume = `master + delta` (clamped to 1.0); other cells = `master - delta` (clamped to 0)
- **Duck mode**: hovered cell volume = `master - delta`; others stay at master
- Apply changes live to the mpv `volume` property for each cell's instance

When fullscreen mode is active for a cell, hover behaviors are suspended (the fullscreen cell is the only thing visible).

The Hover popover button in the toolbar shows amber accent when *either* expand or volume is enabled.

---

## Cell-confined fullscreen

Pressing `F` while hovering a cell, clicking the maximize icon (top-right on hover), or selecting from right-click context menu animates the cell to fill the entire stage area — *but not the entire window*. The toolbar above and transport bar below remain visible.

For **video cells**, this is straightforward: animate width/height to 100% with the same 350ms easing. Other cells fade out (opacity → 0) and become non-interactive.

For **browser cells**, this is the hard part. Web pages call `element.requestFullscreen()` and expect to take over the screen. You must:
1. Intercept the Fullscreen API in WebKitGTK/QtWebEngine
2. When the page requests fullscreen, instead of going true-fullscreen, expand the webview to fill the cell bounds and scroll/resize the embedded video element to match
3. Provide an "Exit fullscreen" overlay button inside the cell (since the browser's own button still triggers `exitFullscreen`)
4. Make sure keyboard shortcuts (F, Esc) still work even when the webview has focus

This behavior is non-optional and is enabled by default in PlayXLS. There is no setting to disable it — escaping a cell to true fullscreen would defeat the purpose of the multi-stream layout.

The cell number badge turns `danger` (rose) with white text while in fullscreen mode, signaling the state.

---

## Toolbar

Streamlined to three primary controls plus a settings button. **The toolbar is intentionally sparse** — anything that can live in a popover or settings dialog does.

```
┌────────────────────────────────────────────────────────────────────────┐
│ [📐 Layout Name ▼]  │  [👁 borders: hover]  [⚙ hover ▼]    ⋯    [⚙]  │
└────────────────────────────────────────────────────────────────────────┘
```

### 1. Layout Picker (dropdown button)
- Shows the active layout's icon + name + chevron
- Click to open a popover containing all layouts (presets + saved custom)
- Each layout in the popover renders as a tile: a **mini thumbnail** of the actual tile-tree geometry (real preview, not an icon), plus the name underneath
- Custom layouts show a delete-X badge on hover
- A "Create Custom Layout" button at the bottom opens the Grid Editor
- Active layout is highlighted with amber accent border + background tint

### 2. Borders cycling button
- Single tap cycles: Always → Hover → Never → Always
- Shows current state inline ("borders: hover") with appropriate icon (Eye / Mouse / EyeOff)
- Bound to `B`

### 3. Hover popover button
- Opens a popover containing both Hover Expand and Hover Volume controls
- Button background turns amber when either feature is enabled
- Popover has:
  - Expand toggle + scale slider (105–200%)
  - Volume toggle + Boost/Duck segmented control + amount slider (10–80%)
  - Live values shown next to sliders

### 4. Settings gear (right-aligned)
- Opens the Settings dialog (Ctrl+,)

That's it. No layout chip strip, no separate expand/volume buttons. If the user wants those controls always-visible, they're a single click away in the popover.

---

## Sidebar tabs

### Library tab

**Top**: search bar + folder filter chips (`all` / `Animations` / `Trailers` / etc.)

**Each video row**:
- 48×32 thumbnail/preview area on the left
- Title + folder/duration metadata (mono, tertiary text)
- Cell number badges — small amber-bordered squares (16×16) showing which cells this video is currently loaded into. Multiple cells = multiple badges.
- Single overflow menu (`⋯`) at the right that appears on hover. **No more three-icon clutter.** The menu contains:
  - **Load to cell…** → opens cell picker inline
  - **Remove from playlist** (non-destructive)
  - **Delete from disk** (destructive — opens confirmation banner)

**Cell picker** (appears below row when "Load to cell" clicked): grid of small numbered buttons, one per cell in current layout. Currently-assigned cells show in green, are disabled, and serve only as visual confirmation. Click any other to assign and dismiss.

**Delete confirmation**: clicking "Delete from disk" expands a danger-tinted inline banner with the video title and "Cannot be undone" copy. Buttons: Delete / Cancel.

**Hover preview** — the headline interaction:
- After `previewDelay` ms (default 300ms) of hovering a video row, the thumbnail area starts playing the video inline, muted, looped
- On mouse leave, immediately stop and free the decoder

#### Preview caching strategy

Three-mode toggle in Settings → Library, with **Lazy** as default:

- **Off** — static thumbnails only (use first-frame screenshot generated on folder scan, stored in `~/.cache/playxls/thumbs/`)
- **Lazy (recommended default)** — decode on hover, keep last N videos warm in an LRU cache. N is user-configurable (1–20, default 5). Each cached entry holds a paused mpv instance pre-seeked to the first frame; hover resumes it instantly. Memory footprint ~10–20MB per cached video.
- **Thumb** — static thumbnails generated on folder scan; no inline playback. Compromise mode for low-RAM machines.

(The previous "Full preload" mode was cut. It was always going to be a footgun on machines with large libraries.)

Why not skip caching entirely? First-frame decode for an unseen MP4 is 200–800ms even on fast hardware; HEVC/AV1 worse. Lazy LRU bridges that gap. The 300ms hover delay is itself a debounce that prevents accidental decode storms during scrolling.

Implement the LRU as a separate component owning a small pool of mpv instances. When a row's preview is requested:
1. Check the cache. If warm, attach its mpv to the preview canvas and call `play`.
2. If cold, evict the oldest cached instance, repurpose it for this video, seek to first frame, attach.
3. On mouse leave, detach (instance stays in cache, paused).

### Folders tab

List of folders the app monitors via inotify. Each row:
- Folder icon (amber)
- Name + path (`~/Videos/Animations` style)
- Live/paused chip (success-tinted with pulsing dot when live, muted when paused) — click to toggle
- File count + "polled Xs ago"
- Hover-revealed trash icon for **delete folder from disk** (the only destructive action allowed on folders — there is no "remove from app, keep on disk" option per the requirements)

Delete confirmation banner expands inline, identical pattern to library deletion. Confirmation copy: "Delete folder X and all its videos? Cannot be undone."

Add folder button at the bottom opens a native file chooser. New folders default to `live: true`.

When a watched folder is live and inotify fires `IN_CREATE`, a new file is added to the library list under that folder. Show a brief toast: "Added: {filename}". This is the killer feature versus playlist-based players.

### Browser tab

**Top**: custom URL input — text field with `+` button. Enter any URL, it normalizes to https:// if missing scheme, derives a name from hostname, opens the cell picker.

**8 streaming presets**, each shown as a row:

| Preset | URL | Color |
|---|---|---|
| YouTube | https://youtube.com | `#ff0000` |
| Twitch | https://twitch.tv | `#9146ff` |
| Netflix | https://netflix.com | `#e50914` |
| Prime Video | https://primevideo.com | `#00a8e1` |
| Disney+ | https://disneyplus.com | `#0e47ba` |
| HBO Max | https://max.com | `#9b50ff` |
| Kick | https://kick.com | `#53fc18` |
| Vimeo | https://vimeo.com | `#1ab7ea` |

Each row shows a colored 32×32 icon tile, the service name, the URL, and (when in use) cell number badges identical to the library panel.

Click any preset/custom URL → cell picker appears inline → assign. The cell becomes a `Browser` cell pointing at that URL.

**Inside a browser cell**: render a minimal browser chrome (back / forward / refresh + URL bar with lock icon for HTTPS). Below, the actual webview. The URL bar is editable — clicking it lets you navigate to a different URL within the cell.

Sessions and cookies persist per-cell using separate WebKitGTK contexts (or QtWebEngine profiles). User stays logged into Netflix in cell 2 even after restarting the app.

---

## Settings dialog (Ctrl+,)

Modal, max 768×640, with a left sidebar of section names and a scrollable content area. **Five sections** (consolidated from earlier seven):

```
┌──────────────────────────────────────────────────────────────┐
│ Settings                                                  [×] │
├────────────────┬────────────────────────────────────────────┤
│ ☀ Appearance   │                                            │
│ ▶ Playback     │           [section content]                │
│ ▣ Library      │                                            │
│ ⌨ Shortcuts    │                                            │
│ ⚙ Advanced     │                                            │
├────────────────┴────────────────────────────────────────────┤
│ Saved automatically                                  [Done]   │
└──────────────────────────────────────────────────────────────┘
```

### Appearance
- **Theme** — Dark / Light segmented control
- **Border visibility** — Always / Hover / Hidden segmented
- **Expand cell on hover** — toggle
  - **Expand amount** — slider 105–200% (disabled state when toggle off, but visible)
- **Adjust volume on hover** — toggle
  - **Volume mode** — Boost / Duck segmented
  - **Volume amount** — slider 10–80%

### Playback
- **Pause when minimized** — toggle (default on)
- **Disable screensaver while playing** — toggle (default on) — uses `org.freedesktop.ScreenSaver.Inhibit` D-Bus call
- **Resume videos where you left off** — toggle (default on)
- **Seek sync mode** — Disabled / Soft / Hard select
  - When enabled, all grid cells stay timestamp-locked
  - Hard mode uses mpv's seek-broadcast; soft mode catches up gradually

### Library
- **Strategy** — Off / Lazy / Thumb segmented (preview mode)
- **Hover delay** — number input 0–2000ms (default 300)
- **Cache size** — number input 1–20 videos (default 5)
- **Mute previews** — toggle (default on)

### Shortcuts
List of mappable actions. Each row shows the action name, type icon (Keyboard / Mouse / Command in distinct colors), and the current binding as a button. Click the button to enter recording mode (danger-tinted, "recording…" with pulsing dot). The next non-modifier keypress with all active modifiers becomes the new binding.

**Default bindings** (must persist):

| Action | Default | Type |
|---|---|---|
| Play / Pause | Space | key |
| Toggle Grid Borders | B | key |
| Cycle Grid Layout | G | key |
| Mute Hovered | M | key |
| Open Grid Editor | Ctrl+E | key |
| Open Settings | Ctrl+, | key |
| Cell Fullscreen | F | key |
| Toggle Theme | Ctrl+T | key |

Mouse and macro types are also supported in the data model — design for extensibility but ship without them in v1 if needed.

### Advanced
- **Hardware acceleration** — Auto / VA-API / VDPAU / Disabled select
- **Logging level** — Errors / Warnings / Info / Debug select
- **Open log** — button that opens `~/.local/state/playxls/playxls.log` in the default text editor

Every setting persists to `~/.config/playxls/settings.toml`. Settings save on change (no Apply button); the footer says "Saved automatically" and has just a Done button.

---

## Title bar

36px tall, with:
- Left: traffic-light window controls (close/minimize/maximize)
- Center-left: app name "PlayXLS" (12px, semibold) + "multi-stream player" subtitle (10px mono, muted)
- Right: theme toggle button (Sun in dark mode, Moon in light) + grid metadata in mono (`2 × 2 · 4 cells`)

The theme toggle is duplicated in Settings → Appearance and bound to Ctrl+T.

---

## Transport bar

Bottom of the stage area, 56px tall:
- Round play/pause button (36×36, primary text color background, bg color icon, scales up 5% on hover)
- Mute button + master volume slider (80px wide range, amber accent)
- Time display (current / total) flanking a thin gradient progress bar (amber → danger) with circular thumb
- "SYNCED" indicator on the far right with a pulsing danger-color disc icon — appears when seek sync is on, stays passive otherwise

The transport reflects the *primary* cell's state: the largest video cell in the current layout, or the most recently interacted cell. When a cell is fullscreen, transport reflects that cell.

---

## Cell-level controls

### Cell number badge (always visible)
- Top-left corner, 20px tall, mono `1` etc.
- Black/60% backdrop normally
- Turns **amber** with onAccent text when the cell is hovered
- Turns **danger** with white text when the cell is fullscreen
- Small icon prefix indicates content type: `▶` for video, `🌐` for browser

### Fullscreen button (hover-revealed, top-right)
- 28×28 button with maximize/minimize icon
- Click to toggle fullscreen for that cell
- Also accessible via right-click context menu

### Right-click context menu
- "Cell N" eyebrow
- **Fullscreen** (with `F` shortcut hint on the right)
- **Clear cell**

Foundation for adding more later (mute solo, swap with cell N, replace content, etc.).

### Hover overlay (video cells only)
- Bottom gradient appears on hover
- Shows: video title (white, 12px medium), folder + duration (mono, white/60%), and current hover-volume status (amber, e.g. "vol +40%") when active

---

## Toast notifications

A small pill-shaped notification anchored ~14px below the toolbar, centered horizontally. `textPrimary` background, `bg` text, mono font, 12px. Used for confirming layout changes, mode toggles, file actions ("→ Cell 2", "Removed from playlist", "Border mode cycled"). Auto-dismiss after 2200ms, fade-in 200ms.

Keep them short. **"→ Cell 2"** beats **"Loaded video into cell 2"**. Use the same compression in all toasts.

Do not use toasts for errors — those go to a proper error dialog.

---

## Configuration files

```
~/.config/playxls/
├── settings.toml          # all of Settings dialog
├── layouts.toml           # custom layouts (tile-trees serialized)
├── bindings.toml          # keybindings + macros
├── watch_folders.toml     # folder paths + live/paused state
├── playlists.toml         # named playlists/queues
└── sessions/              # per-window state (positions, last cells)
    └── default.toml

~/.cache/playxls/
├── thumbs/                # first-frame thumbnails
│   └── {video_hash}.webp
└── browser/
    └── {cell_id}/         # WebKit/QtWebEngine profile dirs

~/.local/state/playxls/
└── playxls.log            # rotating log
```

All TOML files must be human-editable and forward-compatible (unknown keys ignored, missing keys defaulted).

---

## Performance budget

- 4 simultaneous 1080p video cells: under 30% CPU on a 2020-era i5/Ryzen 5 with VA-API enabled
- 9 simultaneous 720p cells: must remain responsive (no dropped UI frames)
- Layout transitions: 60 FPS animation on integrated GPUs
- Grid editor: zero frame drops during splitter drag
- Library scroll with Lazy preview: smooth even with 1000+ videos in a folder
- Theme toggle: instant, no flicker
- Cold-start to first-cell-playing: under 2 seconds
- Settings dialog open: under 100ms

If you can't meet these, surface the bottleneck in the log and provide a diagnostic command (`playxls --diagnose`).

---

## Out of scope for v1

These are intentionally cut to keep the initial release focused. Don't build them but design data structures so they can be added later:

- Recording / clipping cells
- Picture-in-picture extraction (popping a cell into a floating window)
- Per-cell audio device routing
- Sync groups (mark a subset of cells as timeline-locked)
- Headless/companion mode for mobile control
- Macro engine + macro editor UI
- Subtitle/audio track selection per cell
- Multi-window support (multiple PlayXLS windows across monitors)
- Streamlink/yt-dlp resolver patterns UI (the integration ships, but pattern editing lives in TOML for now)

---

## Definition of done

The shipped v1 must:

1. Open a video file from CLI: `playxls ~/Videos/foo.mp4` plays it in single layout
2. Open multiple files: `playxls a.mp4 b.mp4 c.mp4 d.mp4` switches to 2x2 with all four loaded
3. Watch folders: drop a new file into `~/Videos/Animations` and it appears in the library within 5 seconds, with a toast notification
4. Custom layouts: build a 1+2 stack in the editor, save it, restart PlayXLS, find it in the layout picker with a real thumbnail and the cells preserved
5. Browser cells: assign YouTube to cell 2, watch a video, click YouTube's fullscreen button → it expands within the cell, not the screen
6. Hover preview: hover any video in the library for 300ms → the thumbnail starts playing inline, muted
7. Hover expand: with a 2x2 grid and expand at 160%, hover any cell → it scales to 1.6x with neighbors dimmed
8. Hover volume in boost mode at 40%: master at 0.5, hover a cell → that cell goes to 0.9, others go to 0.1
9. Cell-confined fullscreen: press F over any cell → it animates to fill the stage area, transport stays visible, Esc restores
10. **Theme switching**: toggle theme via title bar button or Ctrl+T → entire UI repaints to the other theme instantly, no element retains the old palette, settings persist across restart
11. Settings persist: change every setting, restart, all values restored
12. Bindings: rebind Play/Pause to `K`, restart, K still works
13. All keyboard shortcuts in the table above work as specified
14. Memory after 30 minutes of normal use: stable, no leak from repeated layout switches, theme toggles, or preview hovers
15. Flatpak builds and installs cleanly on Ubuntu 22.04, 24.04, and the current LTS

---

## Reference prototype

A working React/HTML prototype demonstrates every interaction described above (visible in the project artifacts). When in doubt about visual treatment, animation timing, microcopy, or interaction flow, defer to the prototype. It is the design source of truth.

The prototype is structured around a `t` (theme) token object that flows into every component. Replicate this pattern in your toolkit's theming system — components should never reference colors directly. A theme switch should be a single state change that the entire UI subscribes to.

When you've shipped v1, write a `MIGRATION_FROM_PROTOTYPE.md` documenting any places where the native implementation diverges and why.
