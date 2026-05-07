import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Play, Pause, Volume2, VolumeX, Folder, FolderPlus,
  Keyboard, Mouse, Plus, X, Eye, EyeOff, Maximize2, Minimize2,
  Film, Search, Sliders, Command, Circle, Square,
  RectangleHorizontal, Columns3, Grid2x2, LayoutGrid, Disc3,
  SplitSquareHorizontal, SplitSquareVertical, Save, Edit3,
  Trash2, Copy, RotateCcw, Layers, Globe, Video, MoreHorizontal,
  ChevronDown, ChevronRight, Sun, Moon, ArrowLeft, ArrowRight,
  RefreshCw, Lock, Twitch, Youtube, Wifi, MoreVertical
} from "lucide-react";

// ─── Sample videos ────────────────────────────────────────────────────────────
const SAMPLE_VIDEOS = [
  { id: "v1", title: "Big Buck Bunny",        duration: "9:56",  folder: "Animations", src: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4" },
  { id: "v2", title: "Elephant Dream",        duration: "10:53", folder: "Animations", src: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4" },
  { id: "v3", title: "For Bigger Blazes",     duration: "0:15",  folder: "Trailers",   src: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4" },
  { id: "v4", title: "For Bigger Escape",     duration: "0:15",  folder: "Trailers",   src: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4" },
  { id: "v5", title: "For Bigger Fun",        duration: "1:00",  folder: "Trailers",   src: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4" },
  { id: "v6", title: "For Bigger Joyrides",   duration: "0:15",  folder: "Trailers",   src: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4" },
  { id: "v7", title: "For Bigger Meltdowns",  duration: "0:15",  folder: "Trailers",   src: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4" },
  { id: "v8", title: "Sintel",                duration: "14:48", folder: "Animations", src: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4" },
  { id: "v9", title: "Tears of Steel",        duration: "12:14", folder: "Sci-Fi",     src: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4" },
];

const STREAMING_PRESETS = [
  { id: "yt", name: "YouTube",     url: "https://youtube.com",    color: "#ff0000", icon: Youtube },
  { id: "tw", name: "Twitch",      url: "https://twitch.tv",      color: "#9146ff", icon: Twitch },
  { id: "nf", name: "Netflix",     url: "https://netflix.com",    color: "#e50914", icon: Film },
  { id: "pr", name: "Prime Video", url: "https://primevideo.com", color: "#00a8e1", icon: Film },
  { id: "dp", name: "Disney+",     url: "https://disneyplus.com", color: "#0e47ba", icon: Film },
  { id: "hb", name: "HBO Max",     url: "https://max.com",        color: "#9b50ff", icon: Film },
  { id: "ku", name: "Kick",        url: "https://kick.com",       color: "#53fc18", icon: Wifi },
  { id: "vm", name: "Vimeo",       url: "https://vimeo.com",      color: "#1ab7ea", icon: Video },
];

// ─── Tile-tree grid model ─────────────────────────────────────────────────────
const leaf = () => ({ type: "leaf" });
const splitV = (a, b, ratio = 0.5) => ({ type: "split", direction: "v", ratio, a, b });
const splitH = (a, b, ratio = 0.5) => ({ type: "split", direction: "h", ratio, a, b });
function build3x3() {
  const row = () => splitV(splitV(leaf(), leaf()), leaf(), 0.667);
  return splitH(splitH(row(), row()), row(), 0.667);
}

const PRESET_LAYOUTS = [
  { id: "1x1", label: "Single",       icon: Square,              tree: leaf() },
  { id: "1x2", label: "1 × 2",        icon: RectangleHorizontal, tree: splitV(leaf(), leaf()) },
  { id: "1x3", label: "1 × 3",        icon: Columns3,            tree: splitV(splitV(leaf(), leaf()), leaf(), 0.667) },
  { id: "2x2", label: "2 × 2",        icon: Grid2x2,             tree: splitH(splitV(leaf(), leaf()), splitV(leaf(), leaf())) },
  { id: "3x3", label: "3 × 3",        icon: LayoutGrid,          tree: build3x3() },
  { id: "1+2", label: "1 + 2 stack",  icon: Layers,              tree: splitV(leaf(), splitH(leaf(), leaf()), 0.6) },
];

function collectCells(node, x, y, w, h, out) {
  if (node.type === "leaf") { out.push({ x, y, w, h, path: [] }); return out; }
  if (node.direction === "v") {
    const wA = w * node.ratio;
    collectCells(node.a, x, y, wA, h, out);
    collectCells(node.b, x + wA, y, w - wA, h, out);
  } else {
    const hA = h * node.ratio;
    collectCells(node.a, x, y, w, hA, out);
    collectCells(node.b, x, y + hA, w, h - hA, out);
  }
  return out;
}
const getCells = (tree) => collectCells(tree, 0, 0, 100, 100, []);
function countCells(node) {
  if (node.type === "leaf") return 1;
  return countCells(node.a) + countCells(node.b);
}
function splitLeafAt(node, path, direction) {
  if (path.length === 0) {
    if (node.type !== "leaf") return node;
    return direction === "v" ? splitV(leaf(), leaf()) : splitH(leaf(), leaf());
  }
  const [head, ...rest] = path;
  return { ...node, [head]: splitLeafAt(node[head], rest, direction) };
}
function removeLeafAt(node, path) {
  if (path.length === 1) return node[path[0] === "a" ? "b" : "a"];
  const [head, ...rest] = path;
  return { ...node, [head]: removeLeafAt(node[head], rest) };
}
function setRatioAt(node, path, ratio) {
  if (path.length === 0) return { ...node, ratio };
  const [head, ...rest] = path;
  return { ...node, [head]: setRatioAt(node[head], rest, ratio) };
}
function collectSplits(node, x, y, w, h, path, out) {
  if (node.type === "leaf") return out;
  if (node.direction === "v") {
    const wA = w * node.ratio;
    out.push({ path, direction: "v", x: x + wA, y, length: h, container: { x, y, w, h } });
    collectSplits(node.a, x, y, wA, h, [...path, "a"], out);
    collectSplits(node.b, x + wA, y, w - wA, h, [...path, "b"], out);
  } else {
    const hA = h * node.ratio;
    out.push({ path, direction: "h", x, y: y + hA, length: w, container: { x, y, w, h } });
    collectSplits(node.a, x, y, w, hA, [...path, "a"], out);
    collectSplits(node.b, x, y + hA, w, h - hA, [...path, "b"], out);
  }
  return out;
}
function collectLeavesWithPaths(node, x, y, w, h, path, out) {
  if (node.type === "leaf") { out.push({ x, y, w, h, path }); return out; }
  if (node.direction === "v") {
    const wA = w * node.ratio;
    collectLeavesWithPaths(node.a, x, y, wA, h, [...path, "a"], out);
    collectLeavesWithPaths(node.b, x + wA, y, w - wA, h, [...path, "b"], out);
  } else {
    const hA = h * node.ratio;
    collectLeavesWithPaths(node.a, x, y, w, hA, [...path, "a"], out);
    collectLeavesWithPaths(node.b, x, y + hA, w, h - hA, [...path, "b"], out);
  }
  return out;
}

const WATCH_FOLDERS_INIT = [
  { id: "f1", name: "Animations", path: "~/Videos/Animations",  count: 3, live: true  },
  { id: "f2", name: "Trailers",   path: "~/Downloads/Trailers", count: 5, live: true  },
  { id: "f3", name: "Sci-Fi",     path: "~/Videos/Sci-Fi",      count: 1, live: false },
];

const DEFAULT_KEYBINDS = [
  { id: "kb1", action: "Play / Pause",          combo: "Space",            type: "key"   },
  { id: "kb2", action: "Toggle Grid Borders",   combo: "B",                type: "key"   },
  { id: "kb3", action: "Cycle Grid Layout",     combo: "G",                type: "key"   },
  { id: "kb4", action: "Mute Hovered",          combo: "M",                type: "key"   },
  { id: "kb5", action: "Open Grid Editor",      combo: "Ctrl + E",         type: "key"   },
  { id: "kb6", action: "Open Settings",         combo: "Ctrl + ,",         type: "key"   },
  { id: "kb7", action: "Cell Fullscreen",       combo: "F",                type: "key"   },
  { id: "kb8", action: "Toggle Theme",          combo: "Ctrl + T",         type: "key"   },
];

const DEFAULT_SETTINGS = {
  theme: "dark",          // "dark" | "light"
  borderMode: "hover",
  expandOnHover: true,
  expandPercent: 140,
  volumeOnHover: true,
  hoverVolumeMode: "increase",
  hoverVolumeAmount: 40,
  pauseOnMinimize: true,
  disableScreensaver: true,
  savePlaybackPosition: true,
  seekSyncMode: "disabled",
  previewMode: "lazy",
  previewDelay: 300,
  previewMute: true,
  previewCacheSize: 5,
  hwAcceleration: "auto",
  loggingLevel: "info",
};

// ─── Theme tokens ─────────────────────────────────────────────────────────────
const THEMES = {
  dark: {
    // Surfaces
    bg:        "#0a0a0c",
    surface1:  "#0d0d10",  // sidebar
    surface2:  "#15151a",  // elevated
    surface3:  "#1c1c20",  // hover
    titleBar:  "#0f0f12",
    // Borders
    border:    "#1c1c20",
    borderStrong: "#2a2a30",
    // Text
    textPrimary:    "#e7e5e4",  // stone-200
    textSecondary:  "#a8a29e",  // stone-400
    textTertiary:   "#78716c",  // stone-500
    textMuted:      "#57534e",  // stone-600
    // Accents
    accent:       "#fbbf24",  // amber-400
    accentBg:     "rgba(251, 191, 36, 0.15)",
    accentBorder: "rgba(251, 191, 36, 0.4)",
    danger:       "#f43f5e",  // rose-500
    success:      "#34d399",  // emerald-400
    // Cells
    cellBg:       "#000000",
    cellEmpty:    "#0c0c10",
    // On-accent
    onAccent:     "#1c1917",
  },
  light: {
    bg:        "#fafaf9",
    surface1:  "#ffffff",
    surface2:  "#f5f5f4",
    surface3:  "#e7e5e4",
    titleBar:  "#f5f5f4",
    border:    "#e7e5e4",
    borderStrong: "#d6d3d1",
    textPrimary:    "#1c1917",
    textSecondary:  "#44403c",
    textTertiary:   "#78716c",
    textMuted:      "#a8a29e",
    accent:       "#d97706",  // amber-600 (better contrast on light)
    accentBg:     "rgba(217, 119, 6, 0.10)",
    accentBorder: "rgba(217, 119, 6, 0.40)",
    danger:       "#e11d48",
    success:      "#059669",
    cellBg:       "#000000",  // videos always on black
    cellEmpty:    "#f5f5f4",
    onAccent:     "#ffffff",
  },
};

// ─── MAIN ─────────────────────────────────────────────────────────────────────
export default function PlayXLSDemo() {
  const [layouts, setLayouts] = useState(PRESET_LAYOUTS);
  const [layoutId, setLayoutId] = useState("2x2");
  const layout = layouts.find(l => l.id === layoutId) || layouts[0];
  const cells = getCells(layout.tree);

  const [cellContent, setCellContent] = useState(() => {
    const init = Array(20).fill(null).map((_, i) => ({ type: "video", videoId: SAMPLE_VIDEOS[i % SAMPLE_VIDEOS.length].id }));
    init[1] = { type: "browser", url: "https://youtube.com", name: "YouTube" };
    return init;
  });

  const [libraryVideos, setLibraryVideos] = useState(SAMPLE_VIDEOS);
  const [folders, setFolders] = useState(WATCH_FOLDERS_INIT);

  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const updateSettings = (patch) => setSettings(s => ({ ...s, ...patch }));
  const t = THEMES[settings.theme];

  const {
    borderMode, expandOnHover, expandPercent, volumeOnHover,
    hoverVolumeMode, hoverVolumeAmount, previewMode, previewDelay, previewMute,
  } = settings;

  const [borderHovered, setBorderHovered] = useState(false);
  const borderTimer = useRef(null);
  const showBorders = borderMode === "always" || (borderMode === "hover" && borderHovered);

  const [hoveredCell, setHoveredCell] = useState(null);
  const [fullscreenCell, setFullscreenCell] = useState(null);

  const [playing, setPlaying] = useState(true);
  const [masterVolume, setMasterVolume] = useState(0.6);
  const [muted, setMuted] = useState(false);

  // Sources tab (was: separate workspaces)
  const [sourceTab, setSourceTab] = useState("library");
  const [keybinds, setKeybinds] = useState(DEFAULT_KEYBINDS);
  const [recordingBind, setRecordingBind] = useState(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [layoutPickerOpen, setLayoutPickerOpen] = useState(false);
  const [hoverPopoverOpen, setHoverPopoverOpen] = useState(false);
  const [contextMenu, setContextMenu] = useState(null);

  const [toast, setToast] = useState(null);
  const showToast = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2200);
  }, []);

  const handleBorderEdgeEnter = () => {
    if (borderMode !== "hover") return;
    if (borderTimer.current) clearTimeout(borderTimer.current);
    setBorderHovered(true);
  };
  const handleBorderEdgeLeave = () => {
    if (borderMode !== "hover") return;
    if (borderTimer.current) clearTimeout(borderTimer.current);
    borderTimer.current = setTimeout(() => setBorderHovered(false), 900);
  };

  useEffect(() => {
    const onKey = (e) => {
      if (recordingBind) {
        e.preventDefault();
        const parts = [];
        if (e.ctrlKey)  parts.push("Ctrl");
        if (e.shiftKey) parts.push("Shift");
        if (e.altKey)   parts.push("Alt");
        const k = e.key.length === 1 ? e.key.toUpperCase() : e.key;
        if (!["Control", "Shift", "Alt", "Meta"].includes(e.key)) {
          parts.push(k === " " ? "Space" : k);
          setKeybinds(kb => kb.map(b => b.id === recordingBind ? { ...b, combo: parts.join(" + ") } : b));
          setRecordingBind(null);
          showToast("Binding saved");
        }
        return;
      }
      if (e.target.tagName === "INPUT" || settingsOpen || editorOpen) return;
      if (e.code === "Space") { e.preventDefault(); setPlaying(p => !p); showToast(playing ? "Paused" : "Playing"); }
      if (e.key.toLowerCase() === "b") { updateSettings({ borderMode: borderMode === "always" ? "never" : borderMode === "never" ? "hover" : "always" }); showToast("Border mode cycled"); }
      if (e.key.toLowerCase() === "g") {
        const idx = layouts.findIndex(l => l.id === layoutId);
        const next = layouts[(idx + 1) % layouts.length];
        setLayoutId(next.id);
        showToast(`Grid: ${next.label}`);
      }
      if (e.key.toLowerCase() === "m") { setMuted(m => !m); showToast(muted ? "Unmuted" : "Muted"); }
      if (e.key.toLowerCase() === "f" && hoveredCell !== null) { setFullscreenCell(c => c === hoveredCell ? null : hoveredCell); }
      if (e.key === "Escape") { setFullscreenCell(null); setContextMenu(null); setLayoutPickerOpen(false); setHoverPopoverOpen(false); }
      if (e.ctrlKey && e.key.toLowerCase() === "e") { e.preventDefault(); setEditorOpen(true); }
      if (e.ctrlKey && e.key === ",") { e.preventDefault(); setSettingsOpen(true); }
      if (e.ctrlKey && e.key.toLowerCase() === "t") { e.preventDefault(); updateSettings({ theme: settings.theme === "dark" ? "light" : "dark" }); showToast(`${settings.theme === "dark" ? "Light" : "Dark"} mode`); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [recordingBind, layoutId, playing, muted, showToast, layouts, settingsOpen, editorOpen, borderMode, hoveredCell, settings.theme]);

  const saveCustomLayout = (tree, label) => {
    const id = `custom-${Date.now()}`;
    setLayouts(ls => [...ls, { id, label, icon: Layers, tree, custom: true }]);
    setLayoutId(id);
    showToast(`Saved "${label}"`);
  };
  const deleteLayout = (id) => {
    setLayouts(ls => ls.filter(l => l.id !== id));
    if (layoutId === id) setLayoutId("1x1");
    showToast("Layout deleted");
  };

  const removeFromLibrary = (videoId) => {
    setLibraryVideos(vs => vs.filter(v => v.id !== videoId));
    setCellContent(arr => arr.map(c => c.type === "video" && c.videoId === videoId ? { type: "empty" } : c));
    showToast("Removed from playlist");
  };
  const deleteVideoFile = (videoId) => {
    const v = libraryVideos.find(x => x.id === videoId);
    setLibraryVideos(vs => vs.filter(x => x.id !== videoId));
    setCellContent(arr => arr.map(c => c.type === "video" && c.videoId === videoId ? { type: "empty" } : c));
    showToast(`Deleted ${v?.title} from disk`);
  };

  const assignVideoToCell = (videoId, cellIdx) => {
    setCellContent(arr => { const next = [...arr]; next[cellIdx] = { type: "video", videoId }; return next; });
    showToast(`→ Cell ${cellIdx + 1}`);
  };
  const assignBrowserToCell = (preset, cellIdx) => {
    setCellContent(arr => { const next = [...arr]; next[cellIdx] = { type: "browser", url: preset.url, name: preset.name }; return next; });
    showToast(`${preset.name} → Cell ${cellIdx + 1}`);
  };
  const setCellEmpty = (cellIdx) => {
    setCellContent(arr => { const next = [...arr]; next[cellIdx] = { type: "empty" }; return next; });
  };

  const LayoutIcon = layout.icon;

  return (
    <div className="w-full h-screen overflow-hidden flex flex-col"
         style={{ fontFamily: "'Inter', system-ui, sans-serif", background: t.bg, color: t.textPrimary }}
         onClick={() => { setContextMenu(null); setLayoutPickerOpen(false); setHoverPopoverOpen(false); }}>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
        .font-mono { font-family: 'JetBrains Mono', monospace; }
        .scroll-thin::-webkit-scrollbar { width: 6px; height: 6px; }
        .scroll-thin::-webkit-scrollbar-thumb { background: ${t.borderStrong}; border-radius: 3px; }
        .scroll-thin::-webkit-scrollbar-track { background: transparent; }
        @keyframes pulse-dot { 0%,100% { opacity: 1; } 50% { opacity: .35; } }
        .live-dot { animation: pulse-dot 1.6s ease-in-out infinite; }
        @keyframes fade-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
        .fade-in { animation: fade-in .2s ease-out; }
        input[type="range"] { accent-color: ${t.accent}; }
      `}</style>

      {/* Title bar */}
      <div className="h-9 flex items-center justify-between px-3 select-none flex-shrink-0 border-b"
           style={{ background: t.titleBar, borderColor: t.border }}>
        <div className="flex items-center gap-2.5">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full hover:bg-[#e0564a] transition-colors cursor-pointer" style={{ background: t.borderStrong }} />
            <div className="w-3 h-3 rounded-full hover:bg-[#e0a84a] transition-colors cursor-pointer" style={{ background: t.borderStrong }} />
            <div className="w-3 h-3 rounded-full hover:bg-[#5ac26d] transition-colors cursor-pointer" style={{ background: t.borderStrong }} />
          </div>
          <div className="flex items-center gap-1.5 ml-2">
            <span className="text-[12px] font-semibold tracking-tight" style={{ color: t.textPrimary }}>PlayXLS</span>
            <span className="text-[10px] font-mono" style={{ color: t.textMuted }}>multi-stream player</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={(e) => { e.stopPropagation(); updateSettings({ theme: settings.theme === "dark" ? "light" : "dark" }); }}
            title="Toggle theme (Ctrl+T)"
            className="w-7 h-7 flex items-center justify-center rounded transition-colors hover:bg-stone-500/10"
            style={{ color: t.textTertiary }}>
            {settings.theme === "dark" ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
          </button>
          <span className="text-[10px] font-mono" style={{ color: t.textMuted }}>
            {layout.label} · {cells.length} {cells.length === 1 ? "cell" : "cells"}
          </span>
        </div>
      </div>

      <div className="flex-1 flex min-h-0">
        {/* Single sidebar — no left rail anymore */}
        <div className="w-[300px] flex flex-col flex-shrink-0 min-h-0 border-r"
             style={{ background: t.surface1, borderColor: t.border }}>

          {/* Sources tab strip */}
          <div className="flex-shrink-0 p-3 pb-2">
            <div className="text-[10px] font-mono uppercase tracking-wider mb-2" style={{ color: t.textMuted }}>Sources</div>
            <div className="flex gap-0.5 rounded p-0.5" style={{ background: t.surface2 }}>
              {[
                { id: "library", label: "Library", icon: Film },
                { id: "folders", label: "Folders", icon: Folder },
                { id: "browser", label: "Browser", icon: Globe },
              ].map(tab => {
                const Icon = tab.icon;
                const active = sourceTab === tab.id;
                return (
                  <button key={tab.id} onClick={() => setSourceTab(tab.id)}
                    className="flex-1 h-8 flex items-center justify-center gap-1.5 rounded text-[11px] transition-colors"
                    style={{
                      background: active ? t.surface1 : "transparent",
                      color: active ? t.textPrimary : t.textTertiary,
                      fontWeight: active ? 500 : 400,
                      boxShadow: active ? "0 1px 2px rgba(0,0,0,.2)" : "none",
                    }}>
                    <Icon className="w-3.5 h-3.5" /> {tab.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Sidebar content */}
          <div className="flex-1 flex flex-col min-h-0">
            {sourceTab === "library" && (
              <LibraryPanel t={t} videos={libraryVideos} cellContent={cellContent} cellCount={cells.length}
                showToast={showToast} previewMode={previewMode} previewDelay={previewDelay} previewMute={previewMute}
                onAssign={assignVideoToCell} onRemove={removeFromLibrary} onDelete={deleteVideoFile} />
            )}
            {sourceTab === "folders" && (
              <FoldersPanel t={t} folders={folders} setFolders={setFolders} showToast={showToast} />
            )}
            {sourceTab === "browser" && (
              <BrowserPanel t={t} cellContent={cellContent} cellCount={cells.length} onAssign={assignBrowserToCell} />
            )}
          </div>
        </div>

        {/* Stage */}
        <div className="flex-1 flex flex-col min-w-0 relative" style={{ background: t.bg }}>

          {/* Streamlined toolbar */}
          <div className="h-12 border-b flex items-center px-3 gap-2 flex-shrink-0" style={{ borderColor: t.border }}>

            {/* Layout picker (single dropdown) */}
            <div className="relative">
              <button onClick={(e) => { e.stopPropagation(); setLayoutPickerOpen(o => !o); }}
                className="h-8 px-3 flex items-center gap-2 rounded text-[12px] transition-colors hover:bg-stone-500/10"
                style={{ background: t.surface2, color: t.textPrimary }}>
                <LayoutIcon className="w-3.5 h-3.5" style={{ color: t.accent }} />
                <span className="font-medium">{layout.label}</span>
                <ChevronDown className="w-3 h-3" style={{ color: t.textTertiary }} />
              </button>

              {layoutPickerOpen && (
                <LayoutPickerPopover t={t} layouts={layouts} layoutId={layoutId}
                  onSelect={(id) => { setLayoutId(id); setLayoutPickerOpen(false); showToast(`Grid: ${layouts.find(l => l.id === id).label}`); }}
                  onDelete={deleteLayout} onCustom={() => { setEditorOpen(true); setLayoutPickerOpen(false); }} />
              )}
            </div>

            <div className="w-px h-5 mx-1" style={{ background: t.border }} />

            {/* Borders cycling button */}
            <button onClick={() => { const next = borderMode === "always" ? "hover" : borderMode === "hover" ? "never" : "always"; updateSettings({ borderMode: next }); showToast(`Borders: ${next}`); }}
              className="h-8 px-3 flex items-center gap-2 rounded text-[12px] transition-colors hover:bg-stone-500/10"
              style={{ background: t.surface2, color: t.textSecondary }}
              title="B">
              {borderMode === "always" ? <Eye className="w-3.5 h-3.5" /> : borderMode === "never" ? <EyeOff className="w-3.5 h-3.5" /> : <Mouse className="w-3.5 h-3.5" />}
              <span>borders</span>
              <span className="font-mono text-[10px]" style={{ color: t.textTertiary }}>{borderMode}</span>
            </button>

            {/* Hover popover (consolidates expand + volume) */}
            <div className="relative">
              <button onClick={(e) => { e.stopPropagation(); setHoverPopoverOpen(o => !o); }}
                className="h-8 px-3 flex items-center gap-2 rounded text-[12px] transition-colors hover:bg-stone-500/10"
                style={{
                  background: (expandOnHover || volumeOnHover) ? t.accentBg : t.surface2,
                  color: (expandOnHover || volumeOnHover) ? t.accent : t.textSecondary,
                }}>
                <Sliders className="w-3.5 h-3.5" />
                <span>hover</span>
                <ChevronDown className="w-3 h-3" />
              </button>

              {hoverPopoverOpen && (
                <HoverPopover t={t} settings={settings} updateSettings={updateSettings} onClose={() => setHoverPopoverOpen(false)} />
              )}
            </div>

            <div className="flex-1" />

            <button onClick={() => setSettingsOpen(true)}
              className="h-8 w-8 flex items-center justify-center rounded transition-colors hover:bg-stone-500/10"
              style={{ color: t.textSecondary }}
              title="Settings (Ctrl+,)">
              <Sliders className="w-4 h-4" />
            </button>
          </div>

          {/* Stage area */}
          <div className="flex-1 relative overflow-hidden p-5">
            <CellGrid
              t={t}
              cells={cells} cellContent={cellContent} videos={libraryVideos}
              hoveredCell={hoveredCell} setHoveredCell={setHoveredCell}
              fullscreenCell={fullscreenCell} setFullscreenCell={setFullscreenCell}
              showBorders={showBorders} expandOnHover={expandOnHover} expandPercent={expandPercent}
              volumeOnHover={volumeOnHover} hoverVolumeMode={hoverVolumeMode} hoverVolumeAmount={hoverVolumeAmount}
              playing={playing} masterVolume={masterVolume} muted={muted} borderMode={borderMode}
              onContextMenu={(e, cellIdx) => { e.preventDefault(); setContextMenu({ x: e.clientX, y: e.clientY, cellIdx }); }}
              onClearCell={setCellEmpty}
            />
          </div>

          {/* Transport */}
          <div className="h-14 border-t flex items-center px-4 gap-3 flex-shrink-0" style={{ borderColor: t.border, background: t.surface1 }}>
            <button onClick={() => { setPlaying(p => !p); showToast(playing ? "Paused" : "Playing"); }}
              className="w-9 h-9 rounded-full flex items-center justify-center hover:scale-105 transition-transform"
              style={{ background: t.textPrimary, color: t.bg }}>
              {playing ? <Pause className="w-3.5 h-3.5" fill="currentColor" /> : <Play className="w-3.5 h-3.5 ml-0.5" fill="currentColor" />}
            </button>

            <div className="flex items-center gap-1.5 min-w-[120px]">
              <button onClick={() => setMuted(m => !m)} style={{ color: t.textSecondary }} className="hover:opacity-80">
                {muted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </button>
              <input type="range" min="0" max="1" step="0.01" value={muted ? 0 : masterVolume}
                onChange={(e) => { setMasterVolume(parseFloat(e.target.value)); if (muted) setMuted(false); }}
                className="w-20" />
            </div>

            <div className="flex-1 flex items-center gap-2.5">
              <span className="text-[10px] font-mono" style={{ color: t.textTertiary }}>00:42</span>
              <div className="flex-1 h-1 rounded-full overflow-hidden relative" style={{ background: t.surface3 }}>
                <div className="h-full rounded-full" style={{ width: "23%", background: `linear-gradient(90deg, ${t.accent}, ${t.danger})` }} />
                <div className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full shadow-lg"
                     style={{ left: "calc(23% - 5px)", background: t.textPrimary }} />
              </div>
              <span className="text-[10px] font-mono" style={{ color: t.textTertiary }}>03:04</span>
            </div>

            <div className="flex items-center gap-1.5 text-[10px] font-mono" style={{ color: t.textTertiary }}>
              <Disc3 className="w-3 h-3 live-dot" style={{ color: t.danger }} />
              <span>SYNCED</span>
            </div>
          </div>

          {toast && (
            <div className="absolute top-14 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded text-[12px] font-mono shadow-2xl z-50 pointer-events-none fade-in"
                 style={{ background: t.textPrimary, color: t.bg }}>
              {toast}
            </div>
          )}

          {borderMode === "hover" && !fullscreenCell && (
            <>
              <div className="absolute inset-x-0 top-12 h-3 z-30" onMouseEnter={handleBorderEdgeEnter} onMouseLeave={handleBorderEdgeLeave} />
              <div className="absolute inset-y-12 left-0 w-3 z-30" onMouseEnter={handleBorderEdgeEnter} onMouseLeave={handleBorderEdgeLeave} />
              <div className="absolute inset-y-12 right-0 w-3 z-30" onMouseEnter={handleBorderEdgeEnter} onMouseLeave={handleBorderEdgeLeave} />
            </>
          )}

          {contextMenu && (
            <CellContextMenu t={t} x={contextMenu.x} y={contextMenu.y} cellIdx={contextMenu.cellIdx}
              cell={cellContent[contextMenu.cellIdx]} onClose={() => setContextMenu(null)}
              onClear={() => { setCellEmpty(contextMenu.cellIdx); setContextMenu(null); }}
              onFullscreen={() => { setFullscreenCell(contextMenu.cellIdx); setContextMenu(null); }} />
          )}
        </div>
      </div>

      {editorOpen && (
        <GridEditor t={t} initialTree={layout.tree} initialLabel={layout.custom ? layout.label : ""}
          onClose={() => setEditorOpen(false)}
          onSave={(tree, label) => { saveCustomLayout(tree, label); setEditorOpen(false); }} />
      )}

      {settingsOpen && (
        <SettingsDialog t={t} settings={settings} updateSettings={updateSettings}
          keybinds={keybinds} setKeybinds={setKeybinds}
          recordingBind={recordingBind} setRecordingBind={setRecordingBind}
          onClose={() => setSettingsOpen(false)} />
      )}
    </div>
  );
}

// ─── LAYOUT PICKER POPOVER ────────────────────────────────────────────────────
function LayoutPickerPopover({ t, layouts, layoutId, onSelect, onDelete, onCustom }) {
  return (
    <div className="absolute top-10 left-0 z-40 rounded-md shadow-2xl p-2 fade-in"
         style={{ background: t.surface2, border: `1px solid ${t.border}`, minWidth: 280 }}
         onClick={(e) => e.stopPropagation()}>
      <div className="text-[10px] font-mono uppercase tracking-wider px-2 py-1 mb-1" style={{ color: t.textMuted }}>
        Layouts
      </div>
      <div className="grid grid-cols-3 gap-1.5">
        {layouts.map(l => {
          const Icon = l.icon;
          const active = l.id === layoutId;
          return (
            <div key={l.id} className="relative group/lp">
              <button onClick={() => onSelect(l.id)}
                className="w-full p-2 rounded flex flex-col items-center gap-1.5 transition-colors"
                style={{
                  background: active ? t.accentBg : t.surface1,
                  border: `1px solid ${active ? t.accentBorder : t.border}`,
                }}>
                {/* Mini layout preview */}
                <div className="w-full aspect-video rounded flex items-center justify-center" style={{ background: t.bg }}>
                  <LayoutThumbnail t={t} tree={l.tree} active={active} />
                </div>
                <span className="text-[10px] font-medium" style={{ color: active ? t.accent : t.textSecondary }}>
                  {l.label}
                </span>
              </button>
              {l.custom && (
                <button onClick={(e) => { e.stopPropagation(); onDelete(l.id); }}
                  className="absolute top-1 right-1 w-4 h-4 rounded-full text-white items-center justify-center hidden group-hover/lp:flex"
                  style={{ background: t.danger }}>
                  <X className="w-2.5 h-2.5" strokeWidth={3} />
                </button>
              )}
            </div>
          );
        })}
      </div>
      <button onClick={onCustom}
        className="w-full mt-2 h-8 flex items-center justify-center gap-1.5 rounded text-[11px] font-medium transition-colors hover:opacity-80"
        style={{ background: t.accent, color: t.onAccent }}>
        <Plus className="w-3.5 h-3.5" /> Create Custom Layout
      </button>
    </div>
  );
}

// Tiny layout thumbnail (renders the tile-tree as nested boxes)
function LayoutThumbnail({ t, tree, active }) {
  const cells = getCells(tree);
  return (
    <div className="relative w-[90%] h-[80%]" style={{ background: t.surface3, borderRadius: 2 }}>
      {cells.map((c, i) => (
        <div key={i} className="absolute"
          style={{
            left: `${c.x + 1}%`, top: `${c.y + 1}%`, width: `${c.w - 2}%`, height: `${c.h - 2}%`,
            background: active ? t.accent : t.textTertiary, opacity: active ? 0.6 : 0.3, borderRadius: 1,
          }} />
      ))}
    </div>
  );
}

// ─── HOVER POPOVER ────────────────────────────────────────────────────────────
function HoverPopover({ t, settings, updateSettings, onClose }) {
  return (
    <div className="absolute top-10 left-0 z-40 rounded-md shadow-2xl p-3 fade-in"
         style={{ background: t.surface2, border: `1px solid ${t.border}`, width: 280 }}
         onClick={(e) => e.stopPropagation()}>

      {/* Expand */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Maximize2 className="w-3.5 h-3.5" style={{ color: t.accent }} />
          <span className="text-[12px] font-medium" style={{ color: t.textPrimary }}>Expand on Hover</span>
        </div>
        <Toggle t={t} value={settings.expandOnHover} onChange={(v) => updateSettings({ expandOnHover: v })} />
      </div>
      <div className={settings.expandOnHover ? "" : "opacity-40 pointer-events-none"}>
        <div className="flex items-center justify-between text-[11px] mb-1" style={{ color: t.textSecondary }}>
          <span>Scale</span>
          <span className="font-mono" style={{ color: t.accent }}>{settings.expandPercent}%</span>
        </div>
        <input type="range" min="105" max="200" step="5" value={settings.expandPercent}
          onChange={(e) => updateSettings({ expandPercent: parseInt(e.target.value, 10) })}
          className="w-full" />
      </div>

      <div className="my-3 h-px" style={{ background: t.border }} />

      {/* Volume */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Volume2 className="w-3.5 h-3.5" style={{ color: t.accent }} />
          <span className="text-[12px] font-medium" style={{ color: t.textPrimary }}>Volume on Hover</span>
        </div>
        <Toggle t={t} value={settings.volumeOnHover} onChange={(v) => updateSettings({ volumeOnHover: v })} />
      </div>
      <div className={settings.volumeOnHover ? "" : "opacity-40 pointer-events-none"}>
        <div className="grid grid-cols-2 gap-1 mb-2">
          <button onClick={() => updateSettings({ hoverVolumeMode: "increase" })}
            className="h-7 rounded text-[11px] font-mono transition-colors"
            style={{
              background: settings.hoverVolumeMode === "increase" ? t.accent : t.surface3,
              color: settings.hoverVolumeMode === "increase" ? t.onAccent : t.textSecondary,
            }}>
            Boost hovered
          </button>
          <button onClick={() => updateSettings({ hoverVolumeMode: "decrease" })}
            className="h-7 rounded text-[11px] font-mono transition-colors"
            style={{
              background: settings.hoverVolumeMode === "decrease" ? t.accent : t.surface3,
              color: settings.hoverVolumeMode === "decrease" ? t.onAccent : t.textSecondary,
            }}>
            Duck hovered
          </button>
        </div>
        <div className="flex items-center justify-between text-[11px] mb-1" style={{ color: t.textSecondary }}>
          <span>Amount</span>
          <span className="font-mono" style={{ color: t.accent }}>
            {settings.hoverVolumeMode === "increase" ? "+" : "−"}{settings.hoverVolumeAmount}%
          </span>
        </div>
        <input type="range" min="10" max="80" step="5" value={settings.hoverVolumeAmount}
          onChange={(e) => updateSettings({ hoverVolumeAmount: parseInt(e.target.value, 10) })}
          className="w-full" />
      </div>
    </div>
  );
}

// ─── CELL GRID ────────────────────────────────────────────────────────────────
function CellGrid({
  t, cells, cellContent, videos, hoveredCell, setHoveredCell,
  fullscreenCell, setFullscreenCell, showBorders, expandOnHover, expandPercent,
  volumeOnHover, hoverVolumeMode, hoverVolumeAmount, playing, masterVolume, muted, borderMode,
  onContextMenu, onClearCell,
}) {
  const videoRefs = useRef({});

  useEffect(() => {
    Object.entries(videoRefs.current).forEach(([_, vid]) => {
      if (!vid) return;
      if (playing) vid.play().catch(() => {});
      else vid.pause();
    });
  }, [playing, cells.length]);

  useEffect(() => {
    Object.entries(videoRefs.current).forEach(([cellIdx, vid]) => {
      if (!vid) return;
      const idx = parseInt(cellIdx, 10);
      let v = muted ? 0 : masterVolume;
      const delta = hoverVolumeAmount / 100;
      if (volumeOnHover && hoveredCell !== null) {
        if (hoverVolumeMode === "increase") {
          v = idx === hoveredCell ? Math.min(1, masterVolume + delta) : Math.max(0, masterVolume - delta);
        } else {
          v = idx === hoveredCell ? Math.max(0, masterVolume - delta) : masterVolume;
        }
        if (muted) v = 0;
      }
      vid.volume = v;
    });
  }, [hoveredCell, masterVolume, muted, volumeOnHover, hoverVolumeMode, hoverVolumeAmount, cells.length]);

  const gapPct = showBorders ? 0.4 : 0;

  return (
    <div className="w-full h-full relative">
      {cells.map((cell, idx) => {
        const content = cellContent[idx] || { type: "empty" };
        const video = content.type === "video" ? videos.find(v => v.id === content.videoId) : null;
        const isHovered = hoveredCell === idx;
        const isFullscreen = fullscreenCell === idx;
        const otherFullscreen = fullscreenCell !== null && fullscreenCell !== idx;
        const otherHovered = hoveredCell !== null && hoveredCell !== idx && fullscreenCell === null;
        const scale = (expandOnHover && isHovered && !isFullscreen && fullscreenCell === null) ? expandPercent / 100 : 1;

        const xCenter = cell.x + cell.w / 2;
        const yCenter = cell.y + cell.h / 2;
        const originX = xCenter < 33 ? "left" : xCenter > 67 ? "right" : "center";
        const originY = yCenter < 33 ? "top"  : yCenter > 67 ? "bottom" : "center";

        const cellLeft = isFullscreen ? 0 : cell.x + gapPct;
        const cellTop  = isFullscreen ? 0 : cell.y + gapPct;
        const cellW    = isFullscreen ? 100 : cell.w - gapPct * 2;
        const cellH    = isFullscreen ? 100 : cell.h - gapPct * 2;

        return (
          <div key={idx}
            onMouseEnter={() => !otherFullscreen && setHoveredCell(idx)}
            onMouseLeave={() => setHoveredCell(null)}
            onContextMenu={(e) => onContextMenu(e, idx)}
            className="absolute"
            style={{
              left: `${cellLeft}%`, top: `${cellTop}%`, width: `${cellW}%`, height: `${cellH}%`,
              zIndex: isFullscreen ? 30 : isHovered ? 20 : 1,
              opacity: otherFullscreen ? 0 : 1,
              pointerEvents: otherFullscreen ? "none" : "auto",
              transition: "left 350ms cubic-bezier(.4,0,.2,1), top 350ms cubic-bezier(.4,0,.2,1), width 350ms cubic-bezier(.4,0,.2,1), height 350ms cubic-bezier(.4,0,.2,1), opacity 200ms",
            }}>
            <div className={`absolute inset-0 ${showBorders || isFullscreen ? "rounded-md" : ""} overflow-hidden transition-all duration-300`}
              style={{
                background: content.type === "empty" ? t.cellEmpty : t.cellBg,
                transform: `scale(${scale})`,
                transformOrigin: `${originX} ${originY}`,
                boxShadow: (isHovered && !isFullscreen)
                  ? `0 20px 60px -10px rgba(0,0,0,.6), 0 0 0 1px ${t.accentBorder}`
                  : showBorders ? `0 0 0 1px ${t.border}` : "none",
                filter: otherHovered && expandOnHover ? "brightness(0.55)" : "brightness(1)",
              }}>

              {content.type === "video" && video && (
                <video ref={(el) => { videoRefs.current[idx] = el; }} src={video.src}
                  className="w-full h-full object-cover"
                  loop muted={muted} playsInline crossOrigin="anonymous" />
              )}

              {content.type === "browser" && (
                <BrowserCell t={t} url={content.url} name={content.name} isFullscreen={isFullscreen} />
              )}

              {content.type === "empty" && (
                <div className="w-full h-full flex flex-col items-center justify-center gap-1.5"
                     style={{ color: t.textMuted }}>
                  <Plus className="w-5 h-5" strokeWidth={1.5} />
                  <div className="text-[10px] font-mono uppercase tracking-wider">empty cell</div>
                </div>
              )}

              {/* Cell number badge */}
              <div className="absolute top-2 left-2 z-10 transition-all"
                   style={{ transform: isHovered && !isFullscreen ? "scale(1.05)" : "scale(1)" }}>
                <div className="px-1.5 h-5 flex items-center gap-1 rounded font-mono text-[10px] backdrop-blur"
                     style={{
                       background: isFullscreen ? t.danger
                                 : isHovered ? t.accent
                                 : "rgba(0,0,0,0.6)",
                       color: isFullscreen ? "#fff"
                            : isHovered ? t.onAccent
                            : "#e7e5e4",
                     }}>
                  {content.type === "browser" && <Globe className="w-2.5 h-2.5" />}
                  {content.type === "video" && <Video className="w-2.5 h-2.5" />}
                  <span className="font-semibold">{idx + 1}</span>
                </div>
              </div>

              {(isHovered || isFullscreen) && content.type !== "empty" && (
                <button onClick={(e) => { e.stopPropagation(); setFullscreenCell(isFullscreen ? null : idx); }}
                  className="absolute top-2 right-2 z-10 w-7 h-7 rounded backdrop-blur flex items-center justify-center transition-colors"
                  style={{ background: "rgba(0,0,0,0.6)", color: "#e7e5e4" }}>
                  {isFullscreen ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
                </button>
              )}

              {content.type === "video" && (
                <div className={`absolute inset-0 pointer-events-none transition-opacity duration-300 ${isHovered && !isFullscreen ? "opacity-100" : "opacity-0"}`}>
                  <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 50%)" }} />
                  <div className="absolute bottom-2.5 left-2.5 right-2.5">
                    <div className="text-[12px] font-medium text-white">{video?.title}</div>
                    <div className="flex items-center justify-between text-[10px] font-mono text-white/60 mt-0.5">
                      <span>{video?.folder} · {video?.duration}</span>
                      {volumeOnHover && (
                        <span style={{ color: t.accent }}>vol {hoverVolumeMode === "increase" ? "+" : "−"}{hoverVolumeAmount}%</span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── BROWSER CELL ─────────────────────────────────────────────────────────────
function BrowserCell({ t, url, name, isFullscreen }) {
  const [currentUrl, setCurrentUrl] = useState(url);
  const [editing, setEditing] = useState(false);
  const [draftUrl, setDraftUrl] = useState(url);

  const preset = STREAMING_PRESETS.find(p => p.url === currentUrl) || STREAMING_PRESETS.find(p => p.name === name);
  const Icon = preset?.icon || Globe;
  const color = preset?.color || "#666";

  return (
    <div className="w-full h-full flex flex-col" style={{ background: "#1a1a1f" }} onClick={(e) => e.stopPropagation()}>
      <div className="h-8 flex items-center gap-1 px-2 flex-shrink-0 border-b" style={{ background: "#0f0f12", borderColor: "#2a2a30" }}>
        <button className="w-5 h-5 flex items-center justify-center rounded hover:bg-white/5" style={{ color: "#a8a29e" }}>
          <ArrowLeft className="w-3 h-3" />
        </button>
        <button className="w-5 h-5 flex items-center justify-center rounded hover:bg-white/5" style={{ color: "#a8a29e" }}>
          <ArrowRight className="w-3 h-3" />
        </button>
        <button className="w-5 h-5 flex items-center justify-center rounded hover:bg-white/5" style={{ color: "#a8a29e" }}>
          <RefreshCw className="w-3 h-3" />
        </button>
        <div className="flex-1 h-5 rounded flex items-center gap-1.5 px-2 cursor-text" style={{ background: "#0a0a0c" }}
             onClick={() => { setEditing(true); setDraftUrl(currentUrl); }}>
          <Lock className="w-2.5 h-2.5 flex-shrink-0" style={{ color: "#34d399" }} />
          {editing ? (
            <input autoFocus value={draftUrl} onChange={(e) => setDraftUrl(e.target.value)}
              onBlur={() => { setCurrentUrl(draftUrl); setEditing(false); }}
              onKeyDown={(e) => { if (e.key === "Enter") { setCurrentUrl(draftUrl); setEditing(false); } if (e.key === "Escape") setEditing(false); }}
              className="flex-1 bg-transparent text-[10px] font-mono outline-none"
              style={{ color: "#e7e5e4" }} />
          ) : (
            <span className="flex-1 text-[10px] font-mono truncate" style={{ color: "#d6d3d1" }}>{currentUrl}</span>
          )}
        </div>
      </div>
      <div className="flex-1 relative overflow-hidden flex items-center justify-center"
           style={{ background: `radial-gradient(ellipse at center, ${color}22 0%, #0a0a0c 70%)` }}>
        <div className="text-center px-6">
          <div className="w-14 h-14 rounded-2xl mx-auto mb-2.5 flex items-center justify-center" style={{ background: color }}>
            <Icon className="w-7 h-7 text-white" strokeWidth={1.6} />
          </div>
          <div className="text-xl font-semibold" style={{ color: "#e7e5e4" }}>{preset?.name || name}</div>
          <div className="text-[10px] font-mono mt-1" style={{ color: "#78716c" }}>{currentUrl}</div>
          <div className="mt-3 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-mono"
               style={{ background: "rgba(255,255,255,0.05)", color: "#a8a29e" }}>
            <Circle className="w-1.5 h-1.5 fill-emerald-400 text-emerald-400 live-dot" />
            embedded webview
          </div>
          {isFullscreen && (
            <div className="mt-2 text-[10px] font-mono" style={{ color: "#f43f5e" }}>
              fullscreen — bound to cell, not screen
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── CELL CONTEXT MENU ────────────────────────────────────────────────────────
function CellContextMenu({ t, x, y, cellIdx, cell, onClose, onClear, onFullscreen }) {
  const isEmpty = !cell || cell.type === "empty";
  return (
    <div className="fixed z-50 rounded-md shadow-2xl py-1 min-w-[180px] fade-in"
         style={{ left: x, top: y, background: t.surface2, border: `1px solid ${t.border}` }}
         onClick={(e) => e.stopPropagation()}>
      <div className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider border-b"
           style={{ color: t.textMuted, borderColor: t.border }}>
        Cell {cellIdx + 1}
      </div>
      <button onClick={onFullscreen} disabled={isEmpty}
        className="w-full px-3 py-1.5 text-left text-[12px] hover:bg-stone-500/10 disabled:opacity-40 flex items-center gap-2"
        style={{ color: t.textPrimary }}>
        <Maximize2 className="w-3.5 h-3.5" /> Fullscreen <span className="ml-auto text-[10px] font-mono" style={{ color: t.textTertiary }}>F</span>
      </button>
      <button onClick={onClear} disabled={isEmpty}
        className="w-full px-3 py-1.5 text-left text-[12px] hover:bg-stone-500/10 disabled:opacity-40 flex items-center gap-2"
        style={{ color: t.textPrimary }}>
        <X className="w-3.5 h-3.5" /> Clear cell
      </button>
    </div>
  );
}

// ─── GRID EDITOR ──────────────────────────────────────────────────────────────
function GridEditor({ t, initialTree, initialLabel, onClose, onSave }) {
  const [tree, setTree] = useState(initialTree);
  const [history, setHistory] = useState([initialTree]);
  const [selectedPath, setSelectedPath] = useState([]);
  const [label, setLabel] = useState(initialLabel || "Custom Layout");
  const stageRef = useRef(null);
  const dragRef = useRef(null);

  const pushHistory = (tt) => { setTree(tt); setHistory(h => [...h, tt]); };
  const undo = () => { if (history.length <= 1) return; const p = history.slice(0, -1); setHistory(p); setTree(p[p.length - 1]); };
  const reset = () => { setTree(leaf()); setHistory([leaf()]); setSelectedPath([]); };
  const splitSelected = (d) => pushHistory(splitLeafAt(tree, selectedPath, d));
  const removeSelected = () => { if (selectedPath.length === 0) return; pushHistory(removeLeafAt(tree, selectedPath)); setSelectedPath([]); };

  const onSplitterMouseDown = (e, splitInfo) => {
    e.preventDefault();
    const rect = stageRef.current.getBoundingClientRect();
    dragRef.current = { splitInfo, rect, startTree: tree };
    const onMove = (ev) => {
      const d = dragRef.current; if (!d) return;
      const { splitInfo, rect, startTree } = d;
      const { container } = splitInfo;
      let ratio;
      if (splitInfo.direction === "v") {
        const localX = ((ev.clientX - rect.left) / rect.width) * 100;
        ratio = (localX - container.x) / container.w;
      } else {
        const localY = ((ev.clientY - rect.top) / rect.height) * 100;
        ratio = (localY - container.y) / container.h;
      }
      ratio = Math.max(0.1, Math.min(0.9, ratio));
      setTree(setRatioAt(startTree, splitInfo.path, ratio));
    };
    const onUp = () => {
      if (dragRef.current) setHistory(h => [...h, tree]);
      dragRef.current = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  const leaves = collectLeavesWithPaths(tree, 0, 0, 100, 100, [], []);
  const splits = collectSplits(tree, 0, 0, 100, 100, [], []);
  const pathsEqual = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);

  const presets = [
    { label: "Single",      tree: leaf() },
    { label: "1 + 2 stack", tree: splitV(leaf(), splitH(leaf(), leaf()), 0.6) },
    { label: "2 stack",     tree: splitH(leaf(), leaf()) },
    { label: "1 × 3",       tree: splitV(splitV(leaf(), leaf()), leaf(), 0.667) },
    { label: "2 × 2",       tree: splitH(splitV(leaf(), leaf()), splitV(leaf(), leaf())) },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-8 fade-in"
         style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}>
      <div className="rounded-lg w-full max-w-5xl h-full max-h-[750px] flex flex-col overflow-hidden shadow-2xl"
           style={{ background: t.surface1, border: `1px solid ${t.border}` }}>

        <div className="h-12 border-b flex items-center justify-between px-4 flex-shrink-0" style={{ borderColor: t.border }}>
          <div className="flex items-center gap-2.5">
            <Edit3 className="w-4 h-4" style={{ color: t.accent }} strokeWidth={1.8} />
            <div className="text-[14px] font-semibold" style={{ color: t.textPrimary }}>Grid Editor</div>
            <div className="text-[10px] font-mono" style={{ color: t.textTertiary }}>· click a cell to split it</div>
          </div>
          <button onClick={onClose} className="w-7 h-7 flex items-center justify-center rounded hover:bg-stone-500/10" style={{ color: t.textTertiary }}>
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 flex min-h-0">
          <div className="w-52 border-r p-4 flex flex-col gap-4 overflow-y-auto scroll-thin flex-shrink-0" style={{ borderColor: t.border }}>
            <div>
              <div className="text-[10px] font-mono uppercase tracking-wider mb-2" style={{ color: t.textMuted }}>Selected Cell</div>
              <div className="space-y-1">
                <button onClick={() => splitSelected("v")}
                  className="w-full h-8 flex items-center gap-2 px-2.5 rounded text-[11px] font-medium transition-colors"
                  style={{ background: t.surface2, color: t.textPrimary }}>
                  <SplitSquareHorizontal className="w-3.5 h-3.5" style={{ color: t.accent }} /> Split vertical
                </button>
                <button onClick={() => splitSelected("h")}
                  className="w-full h-8 flex items-center gap-2 px-2.5 rounded text-[11px] font-medium transition-colors"
                  style={{ background: t.surface2, color: t.textPrimary }}>
                  <SplitSquareVertical className="w-3.5 h-3.5" style={{ color: t.accent }} /> Split horizontal
                </button>
                <button onClick={removeSelected} disabled={selectedPath.length === 0}
                  className="w-full h-8 flex items-center gap-2 px-2.5 rounded text-[11px] font-medium transition-colors disabled:opacity-40"
                  style={{ background: t.surface2, color: t.textPrimary }}>
                  <Trash2 className="w-3.5 h-3.5" /> Remove cell
                </button>
              </div>
              <div className="text-[10px] font-mono mt-2 leading-relaxed" style={{ color: t.textMuted }}>
                Drag handles between cells to resize.
              </div>
            </div>

            <div className="border-t pt-4" style={{ borderColor: t.border }}>
              <div className="text-[10px] font-mono uppercase tracking-wider mb-2" style={{ color: t.textMuted }}>History</div>
              <div className="grid grid-cols-2 gap-1">
                <button onClick={undo} disabled={history.length <= 1}
                  className="h-8 flex items-center justify-center gap-1 rounded text-[11px] font-mono transition-colors disabled:opacity-40"
                  style={{ background: t.surface2, color: t.textSecondary }}>
                  <RotateCcw className="w-3 h-3" /> Undo
                </button>
                <button onClick={reset}
                  className="h-8 flex items-center justify-center rounded text-[11px] font-mono transition-colors"
                  style={{ background: t.surface2, color: t.textSecondary }}>
                  Reset
                </button>
              </div>
            </div>

            <div className="border-t pt-4" style={{ borderColor: t.border }}>
              <div className="text-[10px] font-mono uppercase tracking-wider mb-2" style={{ color: t.textMuted }}>Templates</div>
              <div className="space-y-1">
                {presets.map(p => (
                  <button key={p.label} onClick={() => { pushHistory(p.tree); setSelectedPath([]); }}
                    className="w-full h-7 px-2 flex items-center gap-1.5 rounded text-[11px] font-mono transition-colors"
                    style={{ background: t.surface2, color: t.textSecondary }}>
                    <Copy className="w-3 h-3" style={{ color: t.textTertiary }} /> {p.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex-1 p-6 flex items-center justify-center min-w-0">
            <div ref={stageRef}
              className="relative w-full h-full max-w-[800px] rounded-md overflow-hidden"
              style={{ background: t.bg, border: `1px solid ${t.border}` }}>
              {leaves.map((cell, i) => {
                const isSelected = pathsEqual(cell.path, selectedPath);
                return (
                  <div key={i} onClick={() => setSelectedPath(cell.path)}
                    className="absolute cursor-pointer transition-all duration-200"
                    style={{
                      left: `${cell.x}%`, top: `${cell.y}%`, width: `${cell.w}%`, height: `${cell.h}%`,
                      background: isSelected ? t.accentBg : t.surface2,
                      border: `${isSelected ? 2 : 1}px solid ${isSelected ? t.accent : t.border}`,
                    }}>
                    <div className="w-full h-full flex items-center justify-center">
                      <span className="text-2xl font-light"
                            style={{ color: isSelected ? t.accent : t.textTertiary }}>
                        {i + 1}
                      </span>
                    </div>
                  </div>
                );
              })}
              {splits.map((s, i) => (
                <div key={i} onMouseDown={(e) => onSplitterMouseDown(e, s)}
                  className={`absolute z-10 group/handle ${s.direction === "v" ? "cursor-ew-resize" : "cursor-ns-resize"}`}
                  style={{
                    left: `${s.x}%`, top: `${s.y}%`,
                    width: s.direction === "v" ? "8px" : `${s.length}%`,
                    height: s.direction === "h" ? "8px" : `${s.length}%`,
                    transform: s.direction === "v" ? "translateX(-4px)" : "translateY(-4px)",
                  }}>
                  <div className={`absolute transition-colors ${
                    s.direction === "v" ? "left-1/2 -translate-x-1/2 top-0 bottom-0 w-[2px]" : "top-1/2 -translate-y-1/2 left-0 right-0 h-[2px]"
                  }`}
                    style={{ background: "transparent" }}
                    onMouseEnter={(e) => e.currentTarget.style.background = t.accent}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"} />
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="h-12 border-t flex items-center justify-between px-4 flex-shrink-0" style={{ borderColor: t.border }}>
          <div className="flex items-center gap-2 flex-1 max-w-md">
            <span className="text-[10px] font-mono uppercase tracking-wider" style={{ color: t.textMuted }}>Name</span>
            <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="My Layout"
              className="flex-1 h-7 px-2 rounded text-[11px] font-mono outline-none"
              style={{ background: t.surface2, color: t.textPrimary, border: `1px solid ${t.border}` }} />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono mr-2" style={{ color: t.textTertiary }}>{countCells(tree)} cells</span>
            <button onClick={onClose}
              className="h-8 px-3 rounded text-[11px] font-medium transition-colors"
              style={{ color: t.textSecondary }}>
              Cancel
            </button>
            <button onClick={() => onSave(tree, label || "Untitled")}
              className="h-8 px-3 flex items-center gap-1.5 rounded text-[11px] font-medium transition-colors hover:opacity-80"
              style={{ background: t.accent, color: t.onAccent }}>
              <Save className="w-3.5 h-3.5" /> Save Layout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── LIBRARY PANEL ────────────────────────────────────────────────────────────
function LibraryPanel({
  t, videos, cellContent, cellCount, showToast,
  previewMode, previewDelay, previewMute,
  onAssign, onRemove, onDelete,
}) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [assignTarget, setAssignTarget] = useState(null);
  const [hoveredId, setHoveredId] = useState(null);
  const [previewActiveId, setPreviewActiveId] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [openMenu, setOpenMenu] = useState(null);
  const previewTimer = useRef(null);

  const filtered = videos.filter(v =>
    v.title.toLowerCase().includes(search.toLowerCase()) &&
    (filter === "all" || v.folder === filter)
  );
  const folders = ["all", ...new Set(videos.map(v => v.folder))];

  const cellsForVideo = (videoId) => {
    const out = [];
    for (let i = 0; i < cellCount; i++) {
      const c = cellContent[i];
      if (c?.type === "video" && c.videoId === videoId) out.push(i + 1);
    }
    return out;
  };

  const handleHoverIn = (id) => {
    setHoveredId(id);
    if (previewMode === "off") return;
    if (previewTimer.current) clearTimeout(previewTimer.current);
    previewTimer.current = setTimeout(() => setPreviewActiveId(id), previewDelay);
  };
  const handleHoverOut = () => {
    setHoveredId(null);
    if (previewTimer.current) clearTimeout(previewTimer.current);
    setPreviewActiveId(null);
  };

  return (
    <>
      <div className="px-3 pb-2 flex-shrink-0 space-y-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5" style={{ color: t.textMuted }} />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search videos…"
            className="w-full rounded h-8 pl-8 pr-2 text-[12px] outline-none transition-colors"
            style={{ background: t.surface2, color: t.textPrimary, border: `1px solid ${t.border}` }} />
        </div>
        <div className="flex gap-1 overflow-x-auto scroll-thin">
          {folders.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className="px-2 h-6 rounded text-[10px] font-mono whitespace-nowrap transition-colors"
              style={{
                background: filter === f ? t.textPrimary : t.surface2,
                color: filter === f ? t.bg : t.textSecondary,
              }}>{f}</button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scroll-thin px-1.5 pb-3 min-h-0">
        {filtered.map(v => {
          const playingCells = cellsForVideo(v.id);
          const isAssigning = assignTarget === v.id;
          const isHovered = hoveredId === v.id;
          const isPreviewing = previewActiveId === v.id;
          const showPreview = isPreviewing && previewMode === "lazy";
          const wantsConfirm = confirmDelete === v.id;
          const menuOpen = openMenu === v.id;

          return (
            <div key={v.id}
              onMouseEnter={() => handleHoverIn(v.id)}
              onMouseLeave={handleHoverOut}
              className="px-2 py-1.5 rounded transition-colors"
              style={{ background: isHovered ? t.surface2 : "transparent" }}>

              <div className="flex items-center gap-2.5">
                <button onClick={() => setAssignTarget(isAssigning ? null : v.id)}
                  className="w-12 h-8 rounded flex items-center justify-center flex-shrink-0 relative overflow-hidden"
                  style={{ background: t.surface3, border: `1px solid ${t.border}` }}>
                  {showPreview ? (
                    <video src={v.src} autoPlay muted={previewMute} loop playsInline crossOrigin="anonymous"
                           className="w-full h-full object-cover" />
                  ) : (
                    <Film className="w-3.5 h-3.5" style={{ color: t.textTertiary }} />
                  )}
                  {playingCells.length > 0 && (
                    <div className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full live-dot ring-2"
                         style={{ background: t.success, ringColor: t.surface1 }} />
                  )}
                </button>

                <button onClick={() => setAssignTarget(isAssigning ? null : v.id)}
                  className="flex-1 min-w-0 text-left">
                  <div className="text-[12px] font-medium truncate" style={{ color: t.textPrimary }}>{v.title}</div>
                  <div className="text-[10px] font-mono truncate" style={{ color: t.textTertiary }}>
                    {v.folder} · {v.duration}
                  </div>
                </button>

                {/* Cell badges */}
                {playingCells.length > 0 && (
                  <div className="flex items-center gap-0.5 flex-shrink-0">
                    {playingCells.map(n => (
                      <div key={n} className="w-4 h-4 rounded flex items-center justify-center"
                           style={{ background: t.accentBg, border: `1px solid ${t.accentBorder}` }}>
                        <span className="text-[9px] font-mono font-semibold" style={{ color: t.accent }}>{n}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Single overflow menu instead of three icons */}
                <div className={`relative transition-opacity flex-shrink-0 ${isHovered || menuOpen ? "opacity-100" : "opacity-0"}`}>
                  <button onClick={(e) => { e.stopPropagation(); setOpenMenu(menuOpen ? null : v.id); }}
                    className="w-6 h-6 flex items-center justify-center rounded hover:bg-stone-500/10"
                    style={{ color: t.textTertiary }}>
                    <MoreHorizontal className="w-3.5 h-3.5" />
                  </button>
                  {menuOpen && (
                    <div className="absolute right-0 top-7 z-30 rounded-md shadow-lg py-1 min-w-[160px] fade-in"
                         style={{ background: t.surface2, border: `1px solid ${t.border}` }}
                         onClick={(e) => e.stopPropagation()}>
                      <button onClick={() => { setAssignTarget(v.id); setOpenMenu(null); }}
                        className="w-full px-3 py-1.5 text-left text-[11px] hover:bg-stone-500/10 flex items-center gap-2"
                        style={{ color: t.textPrimary }}>
                        <Plus className="w-3 h-3" /> Load to cell…
                      </button>
                      <button onClick={() => { onRemove(v.id); setOpenMenu(null); }}
                        className="w-full px-3 py-1.5 text-left text-[11px] hover:bg-stone-500/10 flex items-center gap-2"
                        style={{ color: t.textPrimary }}>
                        <X className="w-3 h-3" /> Remove from playlist
                      </button>
                      <button onClick={() => { setConfirmDelete(v.id); setOpenMenu(null); }}
                        className="w-full px-3 py-1.5 text-left text-[11px] hover:bg-stone-500/10 flex items-center gap-2"
                        style={{ color: t.danger }}>
                        <Trash2 className="w-3 h-3" /> Delete from disk
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {wantsConfirm && (
                <div className="mt-1.5 p-2 rounded fade-in"
                     style={{ background: `${t.danger}15`, border: `1px solid ${t.danger}40` }}>
                  <div className="text-[10px] font-mono mb-1.5" style={{ color: t.danger }}>
                    Delete <span className="font-semibold">{v.title}</span> from disk? Cannot be undone.
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => { onDelete(v.id); setConfirmDelete(null); }}
                      className="flex-1 h-6 rounded text-[10px] font-mono text-white"
                      style={{ background: t.danger }}>Delete</button>
                    <button onClick={() => setConfirmDelete(null)}
                      className="flex-1 h-6 rounded text-[10px] font-mono"
                      style={{ background: t.surface3, color: t.textPrimary }}>Cancel</button>
                  </div>
                </div>
              )}

              {isAssigning && !wantsConfirm && (
                <div className="mt-1.5 pt-1.5 border-t fade-in" style={{ borderColor: t.border }}>
                  <div className="text-[9px] font-mono uppercase tracking-wider mb-1" style={{ color: t.textMuted }}>Load into cell</div>
                  <div className="flex flex-wrap gap-1">
                    {Array.from({ length: cellCount }).map((_, i) => {
                      const c = cellContent[i];
                      const isCurrent = c?.type === "video" && c.videoId === v.id;
                      return (
                        <button key={i}
                          onClick={() => { onAssign(v.id, i); setAssignTarget(null); }}
                          disabled={isCurrent}
                          className="w-6 h-6 rounded text-[10px] font-mono transition-all"
                          style={{
                            background: isCurrent ? `${t.success}33` : t.surface3,
                            border: `1px solid ${isCurrent ? `${t.success}80` : t.border}`,
                            color: isCurrent ? t.success : t.textSecondary,
                          }}>{i + 1}</button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}

// ─── FOLDERS PANEL ────────────────────────────────────────────────────────────
function FoldersPanel({ t, folders, setFolders, showToast }) {
  const [confirmDelete, setConfirmDelete] = useState(null);
  const toggleLive = (id) => {
    setFolders(f => f.map(x => x.id === id ? { ...x, live: !x.live } : x));
    const f = folders.find(x => x.id === id);
    showToast(`${f.live ? "Paused" : "Resumed"} ${f.name}`);
  };
  const addFolder = () => {
    const name = `Folder ${folders.length + 1}`;
    setFolders(f => [...f, { id: `f-${Date.now()}`, name, path: `~/Videos/${name}`, count: 0, live: true }]);
    showToast(`Watching ${name}`);
  };
  const deleteFolder = (id) => {
    const f = folders.find(x => x.id === id);
    setFolders(fs => fs.filter(x => x.id !== id));
    setConfirmDelete(null);
    showToast(`Deleted ${f.name}`);
  };

  return (
    <>
      <div className="flex-1 overflow-y-auto scroll-thin px-2 pb-3 min-h-0">
        {folders.map((f) => {
          const wantsConfirm = confirmDelete === f.id;
          return (
            <div key={f.id} className="px-2 py-2 rounded hover:bg-stone-500/5 group transition-colors">
              <div className="flex items-center gap-2">
                <Folder className="w-3.5 h-3.5 flex-shrink-0" style={{ color: t.accent }} />
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] font-medium truncate" style={{ color: t.textPrimary }}>{f.name}</div>
                  <div className="text-[10px] font-mono truncate" style={{ color: t.textTertiary }}>{f.path}</div>
                </div>
                <button onClick={() => toggleLive(f.id)}
                  className="flex items-center gap-1 px-1.5 h-5 rounded text-[9px] font-mono uppercase tracking-wider"
                  style={{
                    background: f.live ? `${t.success}25` : t.surface3,
                    color: f.live ? t.success : t.textTertiary,
                  }}>
                  <Circle className={`w-1.5 h-1.5 fill-current ${f.live ? "live-dot" : ""}`} />
                  {f.live ? "live" : "paused"}
                </button>
              </div>
              <div className="mt-1.5 flex items-center justify-between text-[10px] font-mono" style={{ color: t.textTertiary }}>
                <span>{f.count} files · 4s ago</span>
                <button onClick={() => setConfirmDelete(wantsConfirm ? null : f.id)}
                  className="opacity-0 group-hover:opacity-100 transition-all hover:opacity-100"
                  style={{ color: t.textTertiary }}
                  onMouseEnter={(e) => e.currentTarget.style.color = t.danger}
                  onMouseLeave={(e) => e.currentTarget.style.color = t.textTertiary}>
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>

              {wantsConfirm && (
                <div className="mt-1.5 p-2 rounded fade-in"
                     style={{ background: `${t.danger}15`, border: `1px solid ${t.danger}40` }}>
                  <div className="text-[10px] font-mono mb-1.5" style={{ color: t.danger }}>
                    Delete folder <span className="font-semibold">{f.name}</span> and all videos? Cannot be undone.
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => deleteFolder(f.id)}
                      className="flex-1 h-6 rounded text-[10px] font-mono text-white"
                      style={{ background: t.danger }}>Delete from disk</button>
                    <button onClick={() => setConfirmDelete(null)}
                      className="flex-1 h-6 rounded text-[10px] font-mono"
                      style={{ background: t.surface3, color: t.textPrimary }}>Cancel</button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="flex-shrink-0 p-2 border-t" style={{ borderColor: t.border }}>
        <button onClick={addFolder}
          className="w-full h-8 flex items-center justify-center gap-1.5 rounded text-[11px] font-medium transition-colors"
          style={{ background: t.surface2, color: t.textPrimary }}>
          <FolderPlus className="w-3.5 h-3.5" /> Add Watch Folder
        </button>
      </div>
    </>
  );
}

// ─── BROWSER PANEL ────────────────────────────────────────────────────────────
function BrowserPanel({ t, cellContent, cellCount, onAssign }) {
  const [assignTarget, setAssignTarget] = useState(null);
  const [customUrl, setCustomUrl] = useState("");

  const cellsForUrl = (url) => {
    const out = [];
    for (let i = 0; i < cellCount; i++) {
      const c = cellContent[i];
      if (c?.type === "browser" && c.url === url) out.push(i + 1);
    }
    return out;
  };

  const addCustom = () => {
    if (!customUrl.trim()) return;
    let url = customUrl.trim();
    if (!url.startsWith("http")) url = "https://" + url;
    let name;
    try { name = new URL(url).hostname.replace("www.", ""); } catch { name = url; }
    setAssignTarget({ url, name });
    setCustomUrl("");
  };

  return (
    <>
      <div className="px-3 pb-2 flex-shrink-0">
        <div className="flex gap-1">
          <input value={customUrl} onChange={(e) => setCustomUrl(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") addCustom(); }}
            placeholder="Paste any URL…"
            className="flex-1 rounded h-8 px-2.5 text-[11px] font-mono outline-none transition-colors"
            style={{ background: t.surface2, color: t.textPrimary, border: `1px solid ${t.border}` }} />
          <button onClick={addCustom} disabled={!customUrl.trim()}
            className="h-8 w-8 rounded disabled:opacity-30 flex items-center justify-center"
            style={{ background: t.accent, color: t.onAccent }}>
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scroll-thin px-1.5 pb-3 min-h-0">
        {STREAMING_PRESETS.map(p => {
          const Icon = p.icon;
          const isAssigning = assignTarget?.url === p.url;
          const playingCells = cellsForUrl(p.url);
          return (
            <div key={p.id} className="px-2 py-1.5 rounded hover:bg-stone-500/5 transition-colors">
              <button onClick={() => setAssignTarget(isAssigning ? null : { url: p.url, name: p.name })}
                className="w-full text-left flex items-center gap-2.5">
                <div className="w-8 h-8 rounded flex items-center justify-center flex-shrink-0" style={{ background: p.color }}>
                  <Icon className="w-3.5 h-3.5 text-white" strokeWidth={1.8} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] font-medium" style={{ color: t.textPrimary }}>{p.name}</div>
                  <div className="text-[10px] font-mono truncate" style={{ color: t.textTertiary }}>{p.url}</div>
                </div>
                <div className="flex items-center gap-0.5">
                  {playingCells.map(n => (
                    <div key={n} className="w-4 h-4 rounded flex items-center justify-center"
                         style={{ background: t.accentBg, border: `1px solid ${t.accentBorder}` }}>
                      <span className="text-[9px] font-mono font-semibold" style={{ color: t.accent }}>{n}</span>
                    </div>
                  ))}
                  {playingCells.length === 0 && <Plus className="w-3.5 h-3.5" style={{ color: t.textMuted }} />}
                </div>
              </button>

              {isAssigning && (
                <div className="mt-1.5 pt-1.5 border-t fade-in" style={{ borderColor: t.border }}>
                  <div className="text-[9px] font-mono uppercase tracking-wider mb-1" style={{ color: t.textMuted }}>Load into cell</div>
                  <div className="flex flex-wrap gap-1">
                    {Array.from({ length: cellCount }).map((_, i) => {
                      const c = cellContent[i];
                      const isCurrent = c?.type === "browser" && c.url === p.url;
                      return (
                        <button key={i} onClick={() => { onAssign(p, i); setAssignTarget(null); }}
                          disabled={isCurrent}
                          className="w-6 h-6 rounded text-[10px] font-mono transition-all"
                          style={{
                            background: isCurrent ? `${t.success}33` : t.surface3,
                            border: `1px solid ${isCurrent ? `${t.success}80` : t.border}`,
                            color: isCurrent ? t.success : t.textSecondary,
                          }}>{i + 1}</button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}

// ─── SETTINGS DIALOG (4 sections) ─────────────────────────────────────────────
function SettingsDialog({ t, settings, updateSettings, keybinds, setKeybinds, recordingBind, setRecordingBind, onClose }) {
  const [section, setSection] = useState("appearance");
  const sections = [
    { id: "appearance", label: "Appearance", icon: Sun },
    { id: "playback",   label: "Playback",   icon: Play },
    { id: "library",    label: "Library",    icon: Film },
    { id: "shortcuts",  label: "Shortcuts",  icon: Keyboard },
    { id: "advanced",   label: "Advanced",   icon: Sliders },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-8 fade-in"
         style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}>
      <div className="rounded-lg w-full max-w-3xl h-full max-h-[640px] flex flex-col overflow-hidden shadow-2xl"
           style={{ background: t.surface1, border: `1px solid ${t.border}` }}>

        <div className="h-12 border-b flex items-center justify-between px-4 flex-shrink-0" style={{ borderColor: t.border }}>
          <div className="text-[14px] font-semibold" style={{ color: t.textPrimary }}>Settings</div>
          <button onClick={onClose} className="w-7 h-7 flex items-center justify-center rounded hover:bg-stone-500/10" style={{ color: t.textTertiary }}>
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 flex min-h-0">
          <div className="w-44 border-r py-2 flex-shrink-0" style={{ borderColor: t.border }}>
            {sections.map(s => {
              const Icon = s.icon;
              const active = section === s.id;
              return (
                <button key={s.id} onClick={() => setSection(s.id)}
                  className="w-full px-3 h-9 text-left text-[12px] flex items-center gap-2.5 transition-colors"
                  style={{
                    background: active ? t.accentBg : "transparent",
                    color: active ? t.accent : t.textSecondary,
                    fontWeight: active ? 500 : 400,
                  }}>
                  <Icon className="w-3.5 h-3.5" /> {s.label}
                </button>
              );
            })}
          </div>

          <div className="flex-1 overflow-y-auto scroll-thin p-5 min-w-0">
            {section === "appearance" && <AppearanceSettings t={t} settings={settings} update={updateSettings} />}
            {section === "playback"   && <PlaybackSettings   t={t} settings={settings} update={updateSettings} />}
            {section === "library"    && <LibrarySettings    t={t} settings={settings} update={updateSettings} />}
            {section === "shortcuts"  && <ShortcutsSettings  t={t} keybinds={keybinds} setKeybinds={setKeybinds} recordingBind={recordingBind} setRecordingBind={setRecordingBind} />}
            {section === "advanced"   && <AdvancedSettings   t={t} settings={settings} update={updateSettings} />}
          </div>
        </div>

        <div className="h-11 border-t flex items-center justify-between px-4 flex-shrink-0" style={{ borderColor: t.border }}>
          <div className="text-[10px] font-mono" style={{ color: t.textMuted }}>Saved automatically</div>
          <button onClick={onClose}
            className="h-7 px-4 rounded text-[11px] font-medium transition-colors hover:opacity-80"
            style={{ background: t.accent, color: t.onAccent }}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

function Section({ t, title, children }) {
  return (
    <div className="mb-5">
      <div className="text-[11px] font-medium uppercase tracking-wider mb-2.5" style={{ color: t.textTertiary }}>{title}</div>
      <div className="space-y-1">{children}</div>
    </div>
  );
}
function Row({ t, label, hint, children }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <div className="flex-1 min-w-0">
        <div className="text-[12px]" style={{ color: t.textPrimary }}>{label}</div>
        {hint && <div className="text-[10px] font-mono mt-0.5" style={{ color: t.textMuted }}>{hint}</div>}
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  );
}
function Toggle({ t, value, onChange }) {
  return (
    <button onClick={() => onChange(!value)}
      className="w-9 h-5 rounded-full relative transition-colors"
      style={{ background: value ? t.accent : t.surface3 }}>
      <div className="absolute top-0.5 w-4 h-4 rounded-full transition-transform"
        style={{ background: value ? t.onAccent : t.textPrimary, transform: value ? "translateX(18px)" : "translateX(2px)" }} />
    </button>
  );
}
function Segments({ t, value, onChange, options }) {
  return (
    <div className="flex rounded p-0.5" style={{ background: t.surface3 }}>
      {options.map(o => (
        <button key={o.value} onClick={() => onChange(o.value)}
          className="px-2.5 h-6 rounded text-[10px] font-mono transition-colors"
          style={{
            background: value === o.value ? t.surface1 : "transparent",
            color: value === o.value ? t.textPrimary : t.textSecondary,
            fontWeight: value === o.value ? 500 : 400,
          }}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
function Select({ t, value, onChange, options }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}
      className="h-7 px-2 rounded text-[11px] font-mono outline-none cursor-pointer"
      style={{ background: t.surface3, color: t.textPrimary, border: `1px solid ${t.border}` }}>
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}
function NumInput({ t, value, onChange, min, max, step = 1, suffix }) {
  return (
    <div className="flex items-center gap-1.5">
      <input type="number" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10) || 0)}
        className="w-14 h-7 px-2 rounded text-[11px] font-mono outline-none text-right"
        style={{ background: t.surface3, color: t.textPrimary, border: `1px solid ${t.border}` }} />
      {suffix && <span className="text-[10px] font-mono" style={{ color: t.textTertiary }}>{suffix}</span>}
    </div>
  );
}

function AppearanceSettings({ t, settings, update }) {
  return (
    <>
      <Section t={t} title="Theme">
        <Row t={t} label="Color theme" hint="System theme follows your OS preference">
          <Segments t={t} value={settings.theme} onChange={(v) => update({ theme: v })}
            options={[{ value: "dark", label: "Dark" }, { value: "light", label: "Light" }]} />
        </Row>
      </Section>
      <Section t={t} title="Grid">
        <Row t={t} label="Border visibility" hint={settings.borderMode === "hover" ? "Borders fade in near edges" : null}>
          <Segments t={t} value={settings.borderMode} onChange={(v) => update({ borderMode: v })}
            options={[{ value: "always", label: "Always" }, { value: "hover", label: "Hover" }, { value: "never", label: "Hidden" }]} />
        </Row>
      </Section>
      <Section t={t} title="Hover Behavior">
        <Row t={t} label="Expand cell on hover">
          <Toggle t={t} value={settings.expandOnHover} onChange={(v) => update({ expandOnHover: v })} />
        </Row>
        <div className={settings.expandOnHover ? "" : "opacity-40 pointer-events-none"}>
          <Row t={t} label="Expand amount">
            <div className="flex items-center gap-2">
              <input type="range" min="105" max="200" step="5" value={settings.expandPercent}
                onChange={(e) => update({ expandPercent: parseInt(e.target.value, 10) })}
                className="w-32" />
              <span className="text-[11px] font-mono w-10 text-right" style={{ color: t.accent }}>{settings.expandPercent}%</span>
            </div>
          </Row>
        </div>
        <Row t={t} label="Adjust volume on hover">
          <Toggle t={t} value={settings.volumeOnHover} onChange={(v) => update({ volumeOnHover: v })} />
        </Row>
        <div className={settings.volumeOnHover ? "" : "opacity-40 pointer-events-none"}>
          <Row t={t} label="Volume mode">
            <Segments t={t} value={settings.hoverVolumeMode} onChange={(v) => update({ hoverVolumeMode: v })}
              options={[{ value: "increase", label: "Boost" }, { value: "decrease", label: "Duck" }]} />
          </Row>
          <Row t={t} label="Volume amount">
            <div className="flex items-center gap-2">
              <input type="range" min="10" max="80" step="5" value={settings.hoverVolumeAmount}
                onChange={(e) => update({ hoverVolumeAmount: parseInt(e.target.value, 10) })}
                className="w-32" />
              <span className="text-[11px] font-mono w-10 text-right" style={{ color: t.accent }}>
                {settings.hoverVolumeMode === "increase" ? "+" : "−"}{settings.hoverVolumeAmount}%
              </span>
            </div>
          </Row>
        </div>
      </Section>
    </>
  );
}
function PlaybackSettings({ t, settings, update }) {
  return (
    <>
      <Section t={t} title="Playback">
        <Row t={t} label="Pause when minimized">
          <Toggle t={t} value={settings.pauseOnMinimize} onChange={(v) => update({ pauseOnMinimize: v })} />
        </Row>
        <Row t={t} label="Disable screensaver while playing">
          <Toggle t={t} value={settings.disableScreensaver} onChange={(v) => update({ disableScreensaver: v })} />
        </Row>
        <Row t={t} label="Resume videos where you left off">
          <Toggle t={t} value={settings.savePlaybackPosition} onChange={(v) => update({ savePlaybackPosition: v })} />
        </Row>
      </Section>
      <Section t={t} title="Sync">
        <Row t={t} label="Seek sync mode" hint="Keep all grid cells timestamp-locked">
          <Select t={t} value={settings.seekSyncMode} onChange={(v) => update({ seekSyncMode: v })}
            options={[
              { value: "disabled", label: "Disabled" },
              { value: "soft",     label: "Soft" },
              { value: "hard",     label: "Hard" },
            ]} />
        </Row>
      </Section>
    </>
  );
}
function LibrarySettings({ t, settings, update }) {
  return (
    <>
      <Section t={t} title="Hover Preview">
        <Row t={t} label="Strategy" hint="Lazy is recommended — decode on hover, keep last N warm">
          <Segments t={t} value={settings.previewMode} onChange={(v) => update({ previewMode: v })}
            options={[
              { value: "off",   label: "Off"   },
              { value: "lazy",  label: "Lazy"  },
              { value: "thumb", label: "Thumb" },
            ]} />
        </Row>
        <Row t={t} label="Hover delay">
          <NumInput t={t} value={settings.previewDelay} onChange={(v) => update({ previewDelay: v })} min={0} max={2000} step={50} suffix="ms" />
        </Row>
        <Row t={t} label="Cache size">
          <NumInput t={t} value={settings.previewCacheSize} onChange={(v) => update({ previewCacheSize: v })} min={1} max={20} suffix="videos" />
        </Row>
        <Row t={t} label="Mute previews">
          <Toggle t={t} value={settings.previewMute} onChange={(v) => update({ previewMute: v })} />
        </Row>
      </Section>
    </>
  );
}
function ShortcutsSettings({ t, keybinds, setKeybinds, recordingBind, setRecordingBind }) {
  return (
    <Section t={t} title="Keyboard & Mouse">
      <div className="space-y-1">
        {keybinds.map(b => {
          const Icon = b.type === "mouse" ? Mouse : b.type === "macro" ? Command : Keyboard;
          const recording = recordingBind === b.id;
          return (
            <div key={b.id} className="flex items-center justify-between py-1.5">
              <div className="flex items-center gap-2">
                <Icon className="w-3.5 h-3.5"
                  style={{ color: b.type === "macro" ? t.danger : b.type === "mouse" ? "#0ea5e9" : t.accent }}
                  strokeWidth={1.8} />
                <span className="text-[12px]" style={{ color: t.textPrimary }}>{b.action}</span>
              </div>
              <button onClick={() => setRecordingBind(recording ? null : b.id)}
                className="h-7 px-3 rounded font-mono text-[10px] flex items-center gap-1.5 transition-all min-w-[120px] justify-center"
                style={{
                  background: recording ? `${t.danger}25` : t.surface3,
                  color: recording ? t.danger : t.textSecondary,
                  border: `1px solid ${recording ? `${t.danger}50` : t.border}`,
                }}>
                {recording ? <><Circle className="w-2 h-2 fill-current live-dot" /> recording…</> : b.combo}
              </button>
            </div>
          );
        })}
      </div>
    </Section>
  );
}
function AdvancedSettings({ t, settings, update }) {
  return (
    <>
      <Section t={t} title="Performance">
        <Row t={t} label="Hardware acceleration">
          <Select t={t} value={settings.hwAcceleration} onChange={(v) => update({ hwAcceleration: v })}
            options={[
              { value: "auto",  label: "Auto-detect" },
              { value: "vaapi", label: "VA-API" },
              { value: "vdpau", label: "VDPAU" },
              { value: "off",   label: "Disabled" },
            ]} />
        </Row>
      </Section>
      <Section t={t} title="Logging">
        <Row t={t} label="Logging level">
          <Select t={t} value={settings.loggingLevel} onChange={(v) => update({ loggingLevel: v })}
            options={[
              { value: "error", label: "Errors" },
              { value: "warn",  label: "Warnings" },
              { value: "info",  label: "Info" },
              { value: "debug", label: "Debug" },
            ]} />
        </Row>
        <Row t={t} label="" hint="Open the rolling log file in your text editor">
          <button className="h-7 px-3 rounded text-[11px] font-mono transition-colors"
            style={{ background: t.surface3, color: t.textSecondary }}>
            Open log
          </button>
        </Row>
      </Section>
    </>
  );
}
