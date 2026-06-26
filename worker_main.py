"""
Entry point for the standalone torrent worker process.

Bundled as torrent_worker.exe by PyInstaller — console subsystem,
no PyQt6, no OpenSSL conflicts.  The GUI spawns this exe over pipes
instead of re-invoking itself with --torrent-worker.
"""
from torrent_process import run_worker

if __name__ == '__main__':
    run_worker()
