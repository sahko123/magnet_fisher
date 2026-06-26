"""
Magnet Fisher — entry point.

Usage:
    python main.py                       # Open main window
    python main.py "magnet:?xt=urn:..."  # Open preview for a magnet link
    python main.py --torrent-worker      # Internal: run as the libtorrent subprocess

The --torrent-worker flag is used by the bundled exe so it can spawn itself
as its own libtorrent backend (keeping libtorrent and Qt6 in separate processes
to avoid their OpenSSL version conflict).
"""
import sys
import os

# Ensure the project root is on the path regardless of cwd.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── MUST be first: intercept worker mode before any Qt imports ─────────
if '--torrent-worker' in sys.argv:
    from torrent_process import run_worker
    run_worker()
    sys.exit(0)

# ── Normal GUI startup ─────────────────────────────────────────────────
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QPalette, QColor

from core.session import TorrentSession
from ui.style import QSS
from ui.download_window import DownloadWindow
from ui.preview_dialog import PreviewDialog
from utils.ipc import try_send_to_existing, start_listener
from utils.magnet_handler import register as register_magnet_handler, is_registered


def _apply_palette(app: QApplication) -> None:
    """Apply soft paper light-mode palette so native widgets inherit the right colours."""
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor('#f5f5f5'))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor('#2a2a2a'))
    pal.setColor(QPalette.ColorRole.Base,            QColor('#eaeaea'))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor('#f5f5f5'))
    pal.setColor(QPalette.ColorRole.Text,            QColor('#2a2a2a'))
    pal.setColor(QPalette.ColorRole.Button,          QColor('#eaeaea'))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor('#2a2a2a'))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor('#a8c8e8'))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor('#1a1a1a'))
    pal.setColor(QPalette.ColorRole.Mid,             QColor('#d0d0d0'))
    pal.setColor(QPalette.ColorRole.Dark,            QColor('#c8c8c8'))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor('#888888'))
    app.setPalette(pal)


def main():
    magnet = sys.argv[1] if len(sys.argv) > 1 else None

    # Single-instance: hand off to running instance and exit immediately.
    if magnet and try_send_to_existing(magnet):
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setApplicationName('Magnet Fisher')
    app.setOrganizationName('MagnetFisher')
    app.setQuitOnLastWindowClosed(False)

    _apply_palette(app)
    app.setStyleSheet(QSS)

    session = TorrentSession()
    window  = DownloadWindow(session)

    if not is_registered():
        register_magnet_handler()

    # Keep Python references to open preview dialogs so they aren't
    # garbage-collected while the user is interacting with them.
    _active_dialogs: set = set()

    # ── Thread-safe magnet delivery ────────────────────────────────────
    # start_listener() calls its callback from a background thread.
    # Touching Qt widgets from a non-main thread is illegal in Qt6.
    # We bridge the gap with a signal: emitting a signal is thread-safe;
    # Qt delivers it to the connected slot on the main-thread event loop.
    class _MagnetRelay(QObject):
        received = pyqtSignal(str)

    _relay = _MagnetRelay()

    def open_preview(magnet_uri: str) -> None:
        dlg = PreviewDialog(session, magnet_uri, window)
        dlg.download_requested.connect(
            lambda uri, path, name: window.add_download(name, uri, path)
        )
        dlg.finished.connect(lambda _result: _active_dialogs.discard(dlg))
        _active_dialogs.add(dlg)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    _relay.received.connect(open_preview)
    start_listener(lambda uri: _relay.received.emit(uri))

    window.show()   # always show — tray-only start is confusing
    if magnet:
        QTimer.singleShot(150, lambda: _relay.received.emit(magnet))

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
