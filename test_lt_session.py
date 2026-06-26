"""Minimal test: import libtorrent and create a session, then exit."""
import sys
import os

print("starting", flush=True)

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _lt_dir = os.path.join(sys._MEIPASS, 'libtorrent')
    if os.path.isdir(_lt_dir):
        os.add_dll_directory(_lt_dir)
        print(f"added {_lt_dir}", flush=True)

print("importing lt", flush=True)
import libtorrent as lt
print(f"lt version {lt.version}", flush=True)

print("creating session", flush=True)
s = lt.session()
print("session created OK", flush=True)
del s
print("done", flush=True)
