"""
Subprocess-based torrent session.

libtorrent runs in a child process (torrent_process.py) to avoid the
OpenSSL version conflict with Qt6 (Qt uses OpenSSL 3.x, libtorrent 1.1.x).

Communication: JSON lines over stdin/stdout pipes.
All events arrive on a background reader thread but are bounced to the
Qt main thread via a queued signal before hitting any slot.
"""
import sys
import os
import json
import subprocess
import threading

from PyQt6.QtCore import QObject, pyqtSignal


# ── Bridge ─────────────────────────────────────────────────────────────

class TorrentBridge(QObject):
    """
    Manages the libtorrent subprocess and routes JSON events to listeners.
    Lives on the main thread; the background reader thread only emits
    _raw_event which Qt delivers on the main thread via QueuedConnection.
    """
    _raw_event = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._proc: subprocess.Popen | None = None
        self._listeners: dict[str, list] = {}   # magnet → [callable, ...]
        self._raw_event.connect(self._route)
        self._start()

    # ── Process lifecycle ──────────────────────────────────────────────

    def _start(self):
        if getattr(sys, 'frozen', False):
            # Bundled: use the dedicated torrent_worker.exe (sits alongside
            # MagnetFisher.exe).  It is a minimal console binary with only
            # libtorrent — no PyQt6 DLLs, no Qt runtime hooks, no OpenSSL
            # version conflicts.
            worker = os.path.join(os.path.dirname(sys.executable), 'torrent_worker.exe')
            if os.path.isfile(worker):
                cmd = [worker]
            else:
                # Fallback: re-invoke ourselves with the legacy worker flag.
                cmd = [sys.executable, '--torrent-worker']
        else:
            script = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', 'torrent_process.py')
            )
            cmd = [sys.executable, script]

        # Hide any console window the subprocess might otherwise flash
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE

        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            startupinfo=si,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        threading.Thread(
            target=self._reader, daemon=True, name='torrent-bridge-reader'
        ).start()

    def _reader(self):
        """Background thread: read stdout lines and emit as Qt signals."""
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._raw_event.emit(json.loads(line))
            except (json.JSONDecodeError, RuntimeError):
                pass

    # ── Routing (main thread) ──────────────────────────────────────────

    def _route(self, event: dict):
        magnet = event.get('magnet', '')
        for cb in list(self._listeners.get(magnet, [])):
            try:
                cb(event)
            except Exception:
                pass

    # ── Subscription API ───────────────────────────────────────────────

    def subscribe(self, magnet: str, callback):
        self._listeners.setdefault(magnet, []).append(callback)

    def unsubscribe(self, magnet: str, callback):
        lst = self._listeners.get(magnet, [])
        if callback in lst:
            lst.remove(callback)

    # ── Command senders ────────────────────────────────────────────────

    def _send(self, cmd: dict):
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.stdin.write(json.dumps(cmd) + '\n')
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError):
                pass

    def fetch_metadata(self, magnet: str):
        self._send({'cmd': 'fetch_metadata', 'magnet': magnet})

    def start_download(self, magnet: str, save_path: str):
        self._send({'cmd': 'start_download', 'magnet': magnet, 'save_path': save_path})

    def pause(self, magnet: str):
        self._send({'cmd': 'pause', 'magnet': magnet})

    def resume(self, magnet: str):
        self._send({'cmd': 'resume', 'magnet': magnet})

    def remove(self, magnet: str):
        self._send({'cmd': 'remove', 'magnet': magnet})
        self._listeners.pop(magnet, None)

    def shutdown(self):
        self._send({'cmd': 'quit'})
        if self._proc:
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()


# ── Worker: metadata fetch ─────────────────────────────────────────────

class MetadataFetcher(QObject):
    """Emits ready(metadata_dict, magnet) or failed(error_str)."""
    ready  = pyqtSignal(dict, str)
    failed = pyqtSignal(str)

    def __init__(self, bridge: TorrentBridge, magnet_uri: str):
        super().__init__()
        self._bridge     = bridge
        self._magnet_uri = magnet_uri
        self._cancelled  = False

    def start(self):
        self._bridge.subscribe(self._magnet_uri, self._on_event)
        self._bridge.fetch_metadata(self._magnet_uri)

    def cancel(self):
        self._cancelled = True
        self._bridge.unsubscribe(self._magnet_uri, self._on_event)

    def _on_event(self, event: dict):
        if self._cancelled:
            return
        evt = event.get('event')
        if evt == 'metadata_ready':
            self._bridge.unsubscribe(self._magnet_uri, self._on_event)
            self.ready.emit(event, self._magnet_uri)
        elif evt == 'metadata_error':
            self._bridge.unsubscribe(self._magnet_uri, self._on_event)
            self.failed.emit(event.get('error', 'Unknown error'))


# ── Worker: active download ────────────────────────────────────────────

class DownloadWorker(QObject):
    """Forwards progress/finished/errored signals from the subprocess."""
    progress = pyqtSignal(dict)
    finished = pyqtSignal()
    errored  = pyqtSignal(str)

    def __init__(self, bridge: TorrentBridge, magnet_uri: str, save_path: str):
        super().__init__()
        self._bridge     = bridge
        self._magnet_uri = magnet_uri
        self._save_path  = save_path

    def start(self):
        self._bridge.subscribe(self._magnet_uri, self._on_event)
        self._bridge.start_download(self._magnet_uri, self._save_path)

    def _on_event(self, event: dict):
        evt = event.get('event')
        if evt == 'progress':
            self.progress.emit(event)
        elif evt == 'finished':
            self._bridge.unsubscribe(self._magnet_uri, self._on_event)
            self.finished.emit()
        elif evt == 'error':
            self._bridge.unsubscribe(self._magnet_uri, self._on_event)
            self.errored.emit(event.get('error', 'Unknown error'))

    def pause(self):   self._bridge.pause(self._magnet_uri)
    def resume(self):  self._bridge.resume(self._magnet_uri)
    def stop(self):    self._bridge.remove(self._magnet_uri)


# ── Session (one per app) ──────────────────────────────────────────────

class TorrentSession:
    """Creates and owns the TorrentBridge; hands out worker objects."""

    def __init__(self):
        self._bridge = TorrentBridge()

    def fetch_metadata(self, magnet_uri: str) -> MetadataFetcher:
        return MetadataFetcher(self._bridge, magnet_uri)

    def start_download(self, magnet_uri: str, save_path: str) -> DownloadWorker:
        return DownloadWorker(self._bridge, magnet_uri, save_path)

    def shutdown(self):
        self._bridge.shutdown()
