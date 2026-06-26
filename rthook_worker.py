"""
PyInstaller runtime hook — runs for every start of the frozen exe.

In --torrent-worker mode the PyQt6 hook has already prepended
sys._MEIPASS (_internal/) to PATH so that Qt's OpenSSL DLLs are
discoverable.  That same directory also contains Qt6's OpenSSL 3.x
DLLs (libcrypto-3.dll, libcrypto-3-x64.dll).

libtorrent uses OpenSSL 1.1.x DLLs stored in _internal/libtorrent/.
Even though the names differ, having _MEIPASS on PATH can interfere
with how libtorrent's OpenSSL resolves symbols during session
construction, causing a native crash (0xC0000005).

This hook runs AFTER pyi_rth_pyqt6.py.  It removes _MEIPASS from
PATH again when we're in worker mode so libtorrent has a clean DLL
search environment.  The Qt6 PATH entry is not needed in worker mode
because no Qt modules are imported there.
"""
import os
import sys

if '--torrent-worker' in sys.argv and hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS
    sep = os.pathsep
    parts = os.environ.get('PATH', '').split(sep)
    parts = [p for p in parts if os.path.normcase(p) != os.path.normcase(meipass)]
    os.environ['PATH'] = sep.join(parts)
