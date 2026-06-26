"""
Standalone libtorrent worker process.

Reads JSON commands from stdin, writes JSON events to stdout.
Bundled as torrent_worker.exe (console, no PyQt6) so libtorrent
and Qt6 never share the same process (they conflict on OpenSSL).

Commands (sent by the GUI → this process via stdin):
    {"cmd": "fetch_metadata", "magnet": "magnet:?xt=..."}
    {"cmd": "start_download", "magnet": "...", "save_path": "C:/..."}
    {"cmd": "pause",  "magnet": "..."}
    {"cmd": "resume", "magnet": "..."}
    {"cmd": "remove", "magnet": "..."}
    {"cmd": "quit"}

Events (sent by this process → GUI via stdout):
    {"event": "metadata_ready",  "magnet": "...", "name": "...", "size": N, "files": [...]}
    {"event": "metadata_error",  "magnet": "...", "error": "..."}
    {"event": "progress",        "magnet": "...", "progress": 42.3, ...}
    {"event": "finished",        "magnet": "..."}
    {"event": "error",           "magnet": "...", "error": "..."}
"""
import sys
import os
import json
import time
import threading

# Make project modules importable whether running as a script or as a worker exe.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# In the frozen torrent_worker.exe, libtorrent's OpenSSL DLLs live in
# _internal/libtorrent/ alongside the .pyd file.  Python 3.8+ resolves
# load-time dependencies from the adjacent directory, but any DLL that
# libtorrent lazy-loads at session-creation time uses PATH instead.
# os.add_dll_directory() makes _internal/libtorrent/ a persistent search
# directory so those calls succeed.
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _lt_dir = os.path.join(sys._MEIPASS, 'libtorrent')
    if os.path.isdir(_lt_dir):
        os.add_dll_directory(_lt_dir)

import libtorrent as lt


# ── libtorrent session ─────────────────────────────────────────────────
_session = lt.session()
_session.apply_settings({
    'listen_interfaces':        '0.0.0.0:6881',
    'alert_mask':               lt.alert.category_t.all_categories,
    'announce_to_all_trackers': True,
    'announce_to_all_tiers':    True,

    # DHT lets us find peers even when trackers are dead.
    'enable_dht':               True,
    'dht_bootstrap_nodes': (
        'router.bittorrent.com:6881,'
        'router.utorrent.com:6881,'
        'dht.transmissionbt.com:6881,'
        'dht.aelitis.com:6881'
    ),

    # Local service discovery (peers on the same LAN).
    'enable_lsd':               True,
    # Port mapping so we're reachable behind NAT.
    'enable_natpmp':            True,
    'enable_upnp':              True,

    # Bypass the OS write cache so libtorrent writes go directly to the platter
    # (or NAS NIC) rather than into RAM.  This makes total_wanted_done advance
    # at real disk speed, not RAM speed, so the adaptive throttle below actually
    # reflects HDD throughput.  Mode 1 = disable_os_cache_with_fallback: tries
    # unbuffered I/O, silently falls back to buffered on NAS drivers that don't
    # support it.  Without this, the OS cache absorbs ~200 MB then stalls the
    # disk thread, disconnecting peers (the "200 MB cliff").
    'disk_io_write_mode':       1,

    # How many unwritten bytes libtorrent may queue before it chokes incoming
    # data.  With direct I/O the queue reflects real backpressure rather than OS
    # cache headroom, so 16 MB is enough headroom without letting a large burst
    # accumulate before the throttle responds.
    'max_queued_disk_bytes':    16 * 1024 * 1024,

    # Peer connection headroom — defaults cap us well below the tracker's reported
    # seeder count. 800 global slots + faster ramp-up closes the gap.
    'connections_limit':        800,
    'connection_speed':         30,

    # More upload slots → tit-for-tat logic gets more reciprocation from peers.
    'unchoke_slots_limit':      20,
    # More in-flight block requests per peer → keeps the pipeline full when
    # round-trip latency is high (slow NAS, congested LAN, distant seeders).
    'max_out_request_queue':    500,
    # Drop a peer that hasn't delivered a requested block within 10 s and
    # re-request from someone else — prevents one slow peer from stalling a piece.
    'request_timeout':          10,
    # Pieces small enough to fit in this many blocks are requested whole from
    # one peer, cutting round-trip overhead on slow or high-latency links.
    'whole_pieces_threshold':   20,
})

_handles: dict[str, lt.torrent_handle] = {}   # magnet → handle
_lock = threading.Lock()


# ── Helpers ────────────────────────────────────────────────────────────

def _emit(obj: dict):
    """Write one JSON event line to stdout (thread-safe via GIL + line buffering)."""
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def _fmt_eta(secs: float) -> str:
    if secs <= 0 or secs != secs:
        return '—'
    s = int(secs)
    if s < 60:   return f'{s}s'
    if s < 3600: return f'{s // 60}m {s % 60}s'
    return f'{s // 3600}h {(s % 3600) // 60}m'


_STATE_LABELS = {
    0: 'Queued',
    1: 'Checking files',
    2: 'Fetching metadata',
    3: 'Downloading',
    4: 'Finished',
    5: 'Seeding',
    6: 'Allocating',
    7: 'Checking resume data',
}


# ── Workers (each runs in its own daemon thread) ───────────────────────

def _fetch_metadata(magnet: str):
    handle = None
    try:
        params = lt.parse_magnet_uri(magnet)
        params.save_path = str(os.path.expanduser('~'))
        handle = _session.add_torrent(params)

        deadline = time.monotonic() + 90
        while not handle.status().has_metadata:
            if time.monotonic() > deadline:
                _session.remove_torrent(handle)
                _emit({'event': 'metadata_error', 'magnet': magnet,
                       'error': 'Timed out — no peers responded. Check your connection or try again.'})
                return
            time.sleep(0.25)

        info = handle.torrent_file()
        _session.remove_torrent(handle)
        handle = None

        fs = info.files()
        files = [
            {'path': fs.file_path(i).replace('\\', '/'),
             'size': fs.file_size(i)}
            for i in range(fs.num_files())
        ]
        _emit({
            'event':  'metadata_ready',
            'magnet': magnet,
            'name':   info.name(),
            'size':   info.total_size(),
            'files':  files,
        })
    except Exception as exc:
        _emit({'event': 'metadata_error', 'magnet': magnet, 'error': str(exc)})
    finally:
        if handle is not None:
            try: _session.remove_torrent(handle)
            except Exception: pass


def _download(magnet: str, save_path: str):
    try:
        params = lt.parse_magnet_uri(magnet)
        params.save_path = save_path
        # sparse mode: libtorrent creates files on demand as pieces arrive.
        # With sequential_download enabled, writes are always forward-seeking so
        # fragmentation doesn't occur — no need to pre-size files up front.
        # Pre-sizing (ftruncate) was tried but forces libtorrent to run a full
        # checking_files pass over the entire (zero-filled) file on every start,
        # which saturates the disk and starves the download write path.
        params.storage_mode = lt.storage_mode_t.storage_mode_sparse
        handle = _session.add_torrent(params)
        # Sequential piece order → writes are always forward-seeking on the platter.
        # Rarest-first scatters writes across the file, forcing constant head seeks
        # (5-15 ms each) that drop effective HDD throughput from ~100 MB/s to < 5 MB/s.
        handle.set_sequential_download(True)
        # Per-torrent connection ceiling — without this the global limit is split
        # across all active torrents and a single torrent gets very few slots.
        handle.set_max_connections(400)

        with _lock:
            _handles[magnet] = handle

        # Sliding window of (monotonic_time, total_wanted_done) used to display
        # the real disk write rate in the GUI.  With disk_io_write_mode=1
        # (direct I/O, no OS cache) total_wanted_done advances at actual platter
        # speed, so backpressure is handled entirely by max_queued_disk_bytes —
        # no download-rate cap needed here.
        _write_history: list[tuple[float, int]] = []

        while True:
            with _lock:
                if magnet not in _handles:
                    return  # removed by a "remove" command

            s = handle.status()
            state_int = int(s.state)
            total = max(s.total_wanted, 0)
            done  = max(s.total_wanted_done, 0)
            rate  = max(s.download_rate, 0)
            eta   = _fmt_eta((total - done) / rate) if rate > 0 and total > done else '—'
            pct   = round((done / total * 100) if total > 0 else s.progress * 100, 1)

            now = time.monotonic()
            measured_write_rate = 0
            if state_int == 3:
                _write_history.append((now, done))
                while _write_history and now - _write_history[0][0] > 10:
                    _write_history.pop(0)
                if len(_write_history) >= 4 and now - _write_history[0][0] >= 4:
                    span                = now - _write_history[0][0]
                    measured_write_rate = (done - _write_history[0][1]) / span
            else:
                _write_history.clear()

            _emit({
                'event':      'progress',
                'magnet':     magnet,
                'progress':   pct,
                'down_rate':  rate,
                'write_rate': int(measured_write_rate),
                'up_rate':    max(s.upload_rate, 0),
                'seeds':      max(s.num_seeds, 0),
                'peers':      max(s.num_peers, 0),
                'total':      total,
                'downloaded': done,
                'state':      _STATE_LABELS.get(state_int, 'Connecting…'),
                'eta':        eta,
            })

            if state_int in (4, 5) or s.progress >= 1.0:
                _emit({'event': 'finished', 'magnet': magnet})
                with _lock:
                    _handles.pop(magnet, None)
                return

            time.sleep(1)

    except Exception as exc:
        _emit({'event': 'error', 'magnet': magnet, 'error': str(exc)})
        with _lock:
            _handles.pop(magnet, None)


# ── Command dispatcher ─────────────────────────────────────────────────

def _dispatch(cmd: dict):
    command = cmd.get('cmd', '')
    magnet  = cmd.get('magnet', '')

    if command == 'fetch_metadata':
        threading.Thread(target=_fetch_metadata, args=(magnet,), daemon=True).start()

    elif command == 'start_download':
        save_path = cmd.get('save_path', os.path.expanduser('~/Downloads'))
        threading.Thread(target=_download, args=(magnet, save_path), daemon=True).start()

    elif command == 'pause':
        with _lock:
            h = _handles.get(magnet)
        if h: h.pause()

    elif command == 'resume':
        with _lock:
            h = _handles.get(magnet)
        if h: h.resume()

    elif command == 'remove':
        with _lock:
            h = _handles.pop(magnet, None)
        if h:
            try: _session.remove_torrent(h)
            except Exception: pass

    elif command == 'quit':
        _session.pause()
        sys.exit(0)


# ── Entry point ────────────────────────────────────────────────────────

def run_worker():
    """Main loop: read JSON commands from stdin, dispatch them."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            _dispatch(json.loads(line))
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            _emit({'event': 'error', 'magnet': '', 'error': f'Dispatch error: {exc}'})


if __name__ == '__main__':
    run_worker()
