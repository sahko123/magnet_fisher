import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

_TORZNAB_NS = 'http://torznab.com/schemas/2015/feed'

# ── Local Jackett detection ─────────────────────────────────────────────

def local_config() -> tuple[str, str]:
    """Read Jackett's ServerConfig.json → (base_url, api_key). Returns ('', '') on failure."""
    cfg = Path(os.environ.get('APPDATA', '')) / 'Jackett' / 'ServerConfig.json'
    try:
        with open(cfg, encoding='utf-8') as f:
            data = json.load(f)
        port = data.get('Port', 9117)
        key  = data.get('ApiKey', '')
        if key:
            return f'http://localhost:{port}', key
    except Exception:
        pass
    return '', ''


def ensure_running(base_url: str) -> bool:
    """Return True if Jackett is reachable. If not, try launching JackettTray.exe and wait."""
    if _ping(base_url):
        return True

    tray = _find_tray()
    if not tray:
        return False

    subprocess.Popen([str(tray)], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
    for _ in range(15):
        time.sleep(1)
        if _ping(base_url):
            return True
    return False


def _ping(base_url: str) -> bool:
    try:
        urllib.request.urlopen(f"{base_url.rstrip('/')}/api/v2.0/indexers", timeout=2)
        return True
    except Exception:
        return False


def _find_tray() -> Path | None:
    for env in ('ProgramFiles', 'ProgramW6432', 'ProgramFiles(x86)'):
        p = Path(os.environ.get(env, '')) / 'Jackett' / 'JackettTray.exe'
        if p.exists():
            return p
    return None


# ── Search ──────────────────────────────────────────────────────────────

def search(base_url: str, api_key: str, query: str) -> list[dict]:
    params = urllib.parse.urlencode({'apikey': api_key, 't': 'search', 'q': query})
    url = f"{base_url.rstrip('/')}/api/v2.0/indexers/all/results/torznab?{params}"

    req = urllib.request.Request(url, headers={'User-Agent': 'MagnetFisher/1.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()

    root = ET.fromstring(data)
    channel = root.find('channel')
    if channel is None:
        return []

    def _int(val: str) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    results = []
    for item in channel.findall('item'):
        title = (item.findtext('title') or '').strip()

        try:
            size = int(item.findtext('size') or 0)
        except ValueError:
            size = 0

        attrs: dict[str, str] = {
            a.get('name', ''): a.get('value', '')
            for a in item.findall(f'{{{_TORZNAB_NS}}}attr')
            if a.get('name')
        }

        magnet = attrs.get('magneturl', '')
        if not magnet:
            enc = item.find('enclosure')
            if enc is not None:
                candidate = enc.get('url', '')
                if candidate.startswith('magnet:'):
                    magnet = candidate

        if not magnet or not title:
            continue

        results.append({
            'title':    title,
            'size':     size,
            'seeders':  _int(attrs.get('seeders', '0')),
            'leechers': _int(attrs.get('peers',   '0')),
            'indexer':  attrs.get('indexer', ''),
            'magnet':   magnet,
        })

    return results
