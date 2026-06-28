"""
Persistent settings stored in %APPDATA%\\Magnet Fisher\\settings.json.
"""
import json
import os
from pathlib import Path

_APP_NAME = 'Magnet Fisher'
_SETTINGS_DIR = Path(os.environ.get('APPDATA', Path.home())) / _APP_NAME
_SETTINGS_FILE = _SETTINGS_DIR / 'settings.json'

DEFAULTS: dict = {
    'save_path':          str(Path.home() / 'Downloads'),
    'max_download_rate':  0,   # 0 = unlimited (bytes/s)
    'max_upload_rate':    0,
    'window_x':           None,
    'window_y':           None,
    'window_w':           640,
    'window_h':           520,
    'jackett_url':        '',
    'jackett_api_key':    '',
}


def load() -> dict:
    """Load settings from disk, falling back to defaults for missing keys."""
    if _SETTINGS_FILE.exists():
        try:
            with open(_SETTINGS_FILE, encoding='utf-8') as f:
                data = json.load(f)
            return {**DEFAULTS, **data}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(settings: dict):
    """Persist settings to disk."""
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
