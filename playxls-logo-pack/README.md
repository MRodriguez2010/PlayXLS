# PlayXLS Logo Pack

The visual identity for **PlayXLS** — a multi-stream video player for Ubuntu Linux. This pack contains every variant of the mark, lockup, and wordmark in vector (SVG) and raster (PNG) form, plus packaged assets for Linux desktop install, web favicons, and stickers/print.

## What's in the box

```
playxls-logo-pack/
├── mark-primary/         The default amber-on-dark icon. Use everywhere.
├── mark-light/           Light theme — amber-on-paper.
├── mark-amber/           High-contrast solid amber. For stickers, social, fun stuff.
├── mark-monochrome/      Single-color black or white. Embossing, print, faxes.
├── lockup-horizontal/    Mark + wordmark side-by-side. For headers and footers.
├── wordmark/             Type only, no icon. For body copy or tight spaces.
├── app-icons/            Sized 16 → 512px for desktop installs and shortcuts.
├── linux-hicolor/        Drop-in icon theme structure for /usr/share/icons.
├── favicon/              Web favicon (.ico + .png + apple-touch-icon).
└── README.md
```

Every visual element ships in both `.svg` (master, infinitely scalable) and `.png` (raster, multiple sizes). Always reach for the SVG first — only fall back to PNG when the platform truly cannot render vectors (legacy app stores, some email clients, CI badges).

## The mark

The icon depicts the player's signature **1 + 2 stack** layout — one large left cell with two stacked cells on the right. A play triangle sits in the large cell. The bottom-right cell glows amber. A small live dot in the upper-right cell hints at multi-stream playback.

This is not a generic media-player icon. The composition tells you what PlayXLS does in one glance.

## Color

| Role | Token | Value |
|---|---|---|
| Brand accent (dark) | `accent-dark` | `#fbbf24` (amber-400) |
| Brand accent (light) | `accent-light` | `#d97706` (amber-600) |
| Background (dark) | `bg-dark` | `#0a0a0c` |
| Background (light) | `bg-light` | `#fafaf9` |
| Cell black (always) | `cell-black` | `#000000` |
| Surface dark | `surface-dark` | `#1c1c20` |

Videos always render against pure black (`#000000`) regardless of theme — that's why the large left cell stays black in both the dark and light variants of the icon. The amber accent shifts in hue to maintain contrast against the active background.

## Clear space and minimum size

- **Clear space**: leave at least the height of one inner tile gap (~6% of the mark height) on all sides between the icon and other content. Don't crowd it.
- **Minimum size**: 16px for the simplified favicon variant; 24px for the standard mark with all details intact. Below 16px, use only the play triangle as a glyph.

## Wordmark typography

- **Family**: Inter (free, OFL — bundle with builds)
- **Weights**: 600 for `Play`, 300 for `XLS`
- **Letter-spacing**: -0.02em on `Play`, -0.01em on `XLS`

The weight contrast between `Play` (semibold) and `XLS` (light) is intentional. It establishes that "XLS" is a suffix — the product is "Play," modified by "XLS." Don't equalize the weights, don't reverse them, don't all-caps the wordmark.

When Inter isn't available, fall back to the system UI font (`system-ui`, `-apple-system`, `Segoe UI`). Don't substitute a serif or a display font.

## What not to do

- Don't recolor the amber to a different brand color
- Don't add gradients, glows, drop shadows, or stroke outlines
- Don't put the icon on a busy photo or pattern — use a solid backplate
- Don't rotate, skew, or distort the proportions
- Don't separate the play triangle from the grid (it's not a standalone glyph)
- Don't use the wordmark without the icon when both are available
- Don't fill the empty upper-right cell — that negative space is part of the design

## Linux install (Flatpak / .deb)

The `linux-hicolor/` folder is structured exactly as `/usr/share/icons/hicolor/` expects. To install system-wide:

```bash
sudo cp -r linux-hicolor/* /usr/share/icons/hicolor/
sudo gtk-update-icon-cache /usr/share/icons/hicolor/
```

For Flatpak, point your manifest's `icon` field at `linux-hicolor/scalable/apps/io.playxls.PlayXLS.svg` and the build pipeline will pick up all sizes automatically.

The reverse-DNS app ID is `io.playxls.PlayXLS` — change it if you don't own that domain.

## Web

```html
<link rel="icon" type="image/x-icon" href="/favicon/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/favicon/apple-touch-icon.png">
```

## License

This logo pack is part of the PlayXLS brand. Use it freely to refer to PlayXLS, link to its website, or write about it. Don't use it to imply endorsement of unrelated products or to impersonate the project.
