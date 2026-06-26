"""Quick script to identify which libtorrent setting crashes the frozen subprocess."""
import subprocess, sys, os

exe = os.path.join(os.path.dirname(__file__), r'dist\MagnetFisher\MagnetFisher.exe')

def py_test(code):
    r = subprocess.run(
        [sys.executable, '-c', code],
        capture_output=True, text=True, timeout=10
    )
    return r.returncode, r.stderr[:300]

base = """
import libtorrent as lt
s = lt.session()
s.apply_settings({'listen_interfaces': '0.0.0.0:6881',
                  'alert_mask': 0,
                  'announce_to_all_trackers': True,
                  'announce_to_all_tiers': True})
"""

tests = [
    ('base only',             base),
    ('+enable_dht',           base + "s.apply_settings({'enable_dht': True})"),
    ('+dht_bootstrap_nodes',  base + "s.apply_settings({'enable_dht': True, 'dht_bootstrap_nodes': 'router.bittorrent.com:6881,router.utorrent.com:6881'})"),
    ('+enable_lsd',           base + "s.apply_settings({'enable_lsd': True})"),
    ('+enable_natpmp',        base + "s.apply_settings({'enable_natpmp': True})"),
    ('+enable_upnp',          base + "s.apply_settings({'enable_upnp': True})"),
    ('all new combined',      base + """s.apply_settings({
    'enable_dht': True,
    'dht_bootstrap_nodes': 'router.bittorrent.com:6881,router.utorrent.com:6881,dht.transmissionbt.com:6881',
    'enable_lsd': True, 'enable_natpmp': True, 'enable_upnp': True})"""),
]

for label, code in tests:
    rc, err = py_test(code + '\nprint("pass")')
    status = 'OK    ' if rc == 0 else f'CRASH ({rc})'
    print(f'{status}  {label}')
    if err.strip():
        print(f'       err: {err[:120]}')
