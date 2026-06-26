"""
Single-instance IPC via a local TCP socket.

First instance starts a listener on PORT.
Subsequent instances send their magnet URI to the listener and exit.
"""
import socket
import threading

_PORT = 47_891
_HOST = '127.0.0.1'


def try_send_to_existing(message: str) -> bool:
    """
    Try to send a message to a running instance.
    Returns True if successful (meaning another instance handled it).
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.8)
        s.connect((_HOST, _PORT))
        s.sendall(message.encode('utf-8'))
        s.close()
        return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


def start_listener(on_message) -> threading.Thread:
    """
    Start a background TCP listener.
    Calls on_message(str) for each incoming connection.
    Non-blocking — runs in a daemon thread.
    """
    def _serve():
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind((_HOST, _PORT))
        except OSError:
            return  # Port already in use — another instance won the race
        srv.listen(5)
        while True:
            try:
                conn, _ = srv.accept()
                conn.settimeout(2.0)
                chunks = []
                try:
                    while True:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        chunks.append(chunk)
                except (OSError, TimeoutError):
                    pass
                conn.close()
                data = b''.join(chunks).decode('utf-8', errors='replace').strip()
                if data:
                    on_message(data)
            except Exception:
                pass

    t = threading.Thread(target=_serve, daemon=True, name='ipc-listener')
    t.start()
    return t
