"""
Windows registry: register / unregister Magnet Fisher as the magnet: URI handler.
Uses HKEY_CURRENT_USER so no admin rights are needed.
"""
import sys
import os

_APP_NAME = 'Magnet Fisher'
_REG_BASE = r'Software\Classes\magnet'


def _build_command() -> str:
    # PyInstaller frozen bundle — sys.executable IS the .exe
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}" "%1"'

    # Running as a plain Python script
    exe = sys.executable
    # Prefer pythonw.exe so no console window appears when a magnet is clicked
    pythonw = os.path.join(os.path.dirname(exe), 'pythonw.exe')
    if os.path.exists(pythonw):
        exe = pythonw
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'main.py'))
    return f'"{exe}" "{script}" "%1"'


def register(exe_command: str = None):
    """Register as the magnet: handler. Call once on first launch."""
    try:
        import winreg
    except ImportError:
        print('winreg unavailable — skipping magnet handler registration')
        return

    cmd = exe_command or _build_command()

    try:
        root = winreg.HKEY_CURRENT_USER

        key = winreg.CreateKey(root, _REG_BASE)
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, f'URL:{_APP_NAME}')
        winreg.SetValueEx(key, 'URL Protocol', 0, winreg.REG_SZ, '')
        winreg.CloseKey(key)

        cmd_key = winreg.CreateKey(root, rf'{_REG_BASE}\shell\open\command')
        winreg.SetValueEx(cmd_key, '', 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(cmd_key)

        print(f'[magnet_handler] Registered: {cmd}')
    except Exception as exc:
        print(f'[magnet_handler] Failed to register: {exc}')


def unregister():
    """Remove the magnet: handler registration."""
    try:
        import winreg
        for sub in (r'\shell\open\command', r'\shell\open', r'\shell', ''):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, _REG_BASE + sub)
            except FileNotFoundError:
                pass
    except Exception as exc:
        print(f'[magnet_handler] Failed to unregister: {exc}')


def is_registered() -> bool:
    """Return True if the magnet: handler is registered to us."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            rf'{_REG_BASE}\shell\open\command'
        )
        val, _ = winreg.QueryValueEx(key, '')
        winreg.CloseKey(key)
        return 'main.py' in val or 'MagnetFisher' in val
    except FileNotFoundError:
        return False
