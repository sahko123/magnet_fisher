# 🧲 Magnet Fisher

A fast, minimal torrent client with a soft paper light-mode UI.

Paste or click a magnet link → get an instant file preview → confirm → it downloads.

---

## Features

- **Instant preview** — fetches torrent metadata from DHT/peers before downloading anything; shows the full file tree, total size, and file count
- **Single-instance** — clicking a magnet link while Magnet Fisher is already running opens a new preview in the existing instance instantly
- **System tray** — closes to tray, always ready; right-click to quit
- **Live stats** — download/upload speed, seeds, peers, ETA, and state updated every second
- **Configurable save path** — defaults to `~/Downloads`, remembered per session
- **Soft paper aesthetic** — warm grey palette, no harsh white or bright colours

---

## Setup

### 1. Install dependencies

```
pip install -r requirements.txt
```

> **Note:** `libtorrent` on Windows is easiest via a pre-built wheel:
> ```
> pip install libtorrent
> ```
> If that fails, grab a wheel from https://github.com/arvidn/libtorrent/releases

### 2. Run

```
python main.py
```

### 3. Register as magnet: handler

Magnet Fisher registers itself automatically on first run (writes to
`HKEY_CURRENT_USER\Software\Classes\magnet` — no admin required).

To do it manually:
```python
from utils.magnet_handler import register
register()
```

To unregister:
```python
from utils.magnet_handler import unregister
unregister()
```

---

## Project layout

```
Magnet Fisher/
├── main.py                  # Entry point
├── requirements.txt
│
├── core/
│   ├── session.py           # libtorrent session + QThread workers
│   └── settings.py          # JSON settings in %APPDATA%\Magnet Fisher\
│
├── ui/
│   ├── style.py             # Global QSS stylesheet
│   ├── widgets.py           # TitleBar, Spinner
│   ├── preview_dialog.py    # Metadata preview + confirm dialog
│   └── download_window.py   # Main window + download cards
│
└── utils/
    ├── format.py            # format_size / format_rate / format_eta
    ├── ipc.py               # Single-instance TCP socket
    └── magnet_handler.py    # Windows registry for magnet: URI scheme
```

---

## Colour palette

| Role | Hex |
|------|-----|
| Background | `#f5f5f5` |
| Surface / cards | `#eaeaea` |
| Primary text | `#2a2a2a` |
| Muted text | `#888888` |
| Border | `#d0d0d0` |
| Accent (progress, focus) | `#a8c8e8` |
| Danger hover | `#c42b1c` |
