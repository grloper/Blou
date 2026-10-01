"""Consent-gated, loopback-only Windows desktop preview transport.

This is not RDP. JPEG over authenticated local HTTP is deliberately a small,
inspectable transport for validating monitor capture and coordinate handling.
"""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import io
import json
import math
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

from PIL import ImageGrab


@dataclass(frozen=True)
class Monitor:
    name: str
    left: int
    top: int
    width: int
    height: int

    def point(self, x, y):
        if isinstance(x, bool) or isinstance(y, bool):
            raise ValueError("Invalid point")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError("Invalid point")
        if not math.isfinite(x) or not math.isfinite(y) or not 0 <= x < 1 or not 0 <= y < 1:
            raise ValueError("Point must be inside monitor")
        return self.left + int(x * self.width), self.top + int(y * self.height)


def monitors():
    user = ctypes.windll.user32
    result = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HDC,
                                      ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    def found(handle, dc, rect, data):
        r = rect.contents
        result.append(Monitor(f"Display {len(result) + 1}", r.left, r.top,
                              r.right - r.left, r.bottom - r.top))
        return True
    callback = callback_type(found)
    if not user.EnumDisplayMonitors(None, None, callback, 0):
        raise ctypes.WinError()
    return result


def capture(monitor):
    image = ImageGrab.grab(bbox=(monitor.left, monitor.top,
                                monitor.left + monitor.width,
                                monitor.top + monitor.height), all_screens=True)
    image.thumbnail((1280, 720))
    output = io.BytesIO()
    image.convert("RGB").save(output, "JPEG", quality=75)
    return output.getvalue()


def move_pointer(x, y):
    if not ctypes.windll.user32.SetCursorPos(x, y):
        raise ctypes.WinError()


class Session:
    def __init__(self, displays, grab=capture, pointer=move_pointer):
        self.displays = displays
        self.grab = grab
        self.pointer = pointer
        self.token = secrets.token_urlsafe(32)
        self.active = False
        self.control = False
        self.lock = threading.RLock()
        self.capture_lock = threading.Lock()
        self.generation = 0
        self.sequence = 0
        self.last_frame = 0.0

    def consent(self, active, control=False):
        with self.lock:
            self.generation += 1
            self.active = bool(active)
            self.control = bool(control) and self.active

    def display(self, index):
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(self.displays):
            raise ValueError("Unknown monitor")
        return self.displays[index]

    def frame(self, index):
        with self.lock:
            if not self.active:
                raise PermissionError("Host has not consented")
            generation = self.generation
            display = self.display(index)
        with self.capture_lock:
            # Bound capture CPU even if the client polls too aggressively.
            delay = 0.1 - (time.monotonic() - self.last_frame)
            if delay > 0:
                time.sleep(delay)
            start = time.perf_counter()
            with self.lock:
                if not self.active or generation != self.generation:
                    raise PermissionError("Host revoked consent")
            data = self.grab(display)
            self.last_frame = time.monotonic()
            with self.lock:
                if not self.active or generation != self.generation:
                    raise PermissionError("Host revoked consent")
                self.sequence += 1
                return data, self.sequence, (time.perf_counter() - start) * 1000

    def input(self, index, x, y):
        with self.lock:
            if not self.active or not self.control:
                raise PermissionError("Pointer control is disabled by host")
            point = self.display(index).point(x, y)
            self.pointer(*point)
            return point


def serve(session, port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log bearer tokens or desktop content.

        def send(self, status, data, content_type="application/json", extra=None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            for key, value in (extra or {}).items():
                self.send_header(key, str(value))
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            # Exact Host rejects DNS rebinding. No CORS; POSTs require a
            # non-simple bearer header, blocking cross-origin browser requests.
            expected = f"127.0.0.1:{self.server.server_port}"
            return (self.headers.get("Host") == expected and
                    secrets.compare_digest(self.headers.get("Authorization", "").encode("utf-8"),
                                           ("Bearer " + session.token).encode("ascii")))

        def do_GET(self):
            if not self.authorized():
                self.send(403, b'{"error":"Unauthorized"}')
                return
            path = urlsplit(self.path)
            try:
                if path.path == "/monitors":
                    data = [vars(m) for m in session.displays]
                    self.send(200, json.dumps(data).encode())
                elif path.path == "/frame":
                    index = int(parse_qs(path.query).get("monitor", ["0"])[0])
                    data, seq, elapsed = session.frame(index)
                    self.send(200, data, "image/jpeg", {"X-Sequence": seq,
                              "X-Capture-Ms": round(elapsed, 2)})
                else:
                    self.send(404, b'{"error":"Unknown route"}')
            except PermissionError:
                self.send(403, b'{"error":"Host consent required"}')
            except (ValueError, TypeError):
                self.send(400, b'{"error":"Invalid monitor"}')
            except OSError:
                self.send(503, b'{"error":"Desktop capture unavailable"}')

        def do_POST(self):
            if not self.authorized():
                self.send(403, b'{"error":"Unauthorized"}')
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 512 or self.path != "/pointer":
                    raise ValueError()
                payload = json.loads(self.rfile.read(size))
                point = session.input(payload["monitor"], payload["x"], payload["y"])
                self.send(200, json.dumps({"point": point}).encode())
            except PermissionError:
                self.send(403, b'{"error":"Host control consent required"}')
            except (ValueError, KeyError, TypeError):
                self.send(400, b'{"error":"Invalid pointer request"}')
            except OSError:
                self.send(503, b'{"error":"Pointer unavailable"}')

        def setup(self):
            super().setup()
            self.connection.settimeout(2)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
