# // GREEN PHONE EDIT
# greenscreen v2: step friendly remote screen page for Green Phone.
# v2 talks to droidVNC-NG with a built in VNC client written in plain
# Python, so nothing has to be installed with pip. Only Pillow is used,
# and that comes from the Termux python-pillow package.
# Every page load takes a fresh screenshot. Clicking the screenshot taps
# that spot on the phone. Plain HTML forms only, no JavaScript.

import html
import os
import secrets
import socket
import struct
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from PIL import Image

TOKEN = os.environ["GS_TOKEN"]
VNC_PASS = os.environ["GS_VNC_PASS"]
VNC_HOST = os.environ.get("GS_VNC_HOST", "127.0.0.1")
VNC_PORT = int(os.environ.get("GS_VNC_PORT", "5900"))
PORT = int(os.environ.get("GS_PORT", "8765"))
HERE = os.path.dirname(os.path.abspath(__file__))
SHOT = os.path.join(HERE, "shot.png")
SETTLE = float(os.environ.get("GS_SETTLE", "0.9"))

# ---------- plain Python DES, used only for the VNC password check ----------

_PC1 = [57, 49, 41, 33, 25, 17, 9, 1, 58, 50, 42, 34, 26, 18, 10, 2, 59, 51, 43, 35,
        27, 19, 11, 3, 60, 52, 44, 36, 63, 55, 47, 39, 31, 23, 15, 7, 62, 54, 46, 38,
        30, 22, 14, 6, 61, 53, 45, 37, 29, 21, 13, 5, 28, 20, 12, 4]
_PC2 = [14, 17, 11, 24, 1, 5, 3, 28, 15, 6, 21, 10, 23, 19, 12, 4, 26, 8, 16, 7, 27,
        20, 13, 2, 41, 52, 31, 37, 47, 55, 30, 40, 51, 45, 33, 48, 44, 49, 39, 56,
        34, 53, 46, 42, 50, 36, 29, 32]
_SHIFTS = [1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1]
_IP = [58, 50, 42, 34, 26, 18, 10, 2, 60, 52, 44, 36, 28, 20, 12, 4, 62, 54, 46, 38,
       30, 22, 14, 6, 64, 56, 48, 40, 32, 24, 16, 8, 57, 49, 41, 33, 25, 17, 9, 1,
       59, 51, 43, 35, 27, 19, 11, 3, 61, 53, 45, 37, 29, 21, 13, 5, 63, 55, 47, 39,
       31, 23, 15, 7]
_FP = [40, 8, 48, 16, 56, 24, 64, 32, 39, 7, 47, 15, 55, 23, 63, 31, 38, 6, 46, 14,
       54, 22, 62, 30, 37, 5, 45, 13, 53, 21, 61, 29, 36, 4, 44, 12, 52, 20, 60, 28,
       35, 3, 43, 11, 51, 19, 59, 27, 34, 2, 42, 10, 50, 18, 58, 26, 33, 1, 41, 9,
       49, 17, 57, 25]
_E = [32, 1, 2, 3, 4, 5, 4, 5, 6, 7, 8, 9, 8, 9, 10, 11, 12, 13, 12, 13, 14, 15, 16,
      17, 16, 17, 18, 19, 20, 21, 20, 21, 22, 23, 24, 25, 24, 25, 26, 27, 28, 29,
      28, 29, 30, 31, 32, 1]
_P = [16, 7, 20, 21, 29, 12, 28, 17, 1, 15, 23, 26, 5, 18, 31, 10, 2, 8, 24, 14, 32,
      27, 3, 9, 19, 13, 30, 6, 22, 11, 4, 25]
_S = [
    [14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7, 0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8,
     4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0, 15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13],
    [15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10, 3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5,
     0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15, 13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9],
    [10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8, 13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1,
     13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7, 1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12],
    [7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15, 13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9,
     10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4, 3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14],
    [2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9, 14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6,
     4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14, 11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3],
    [12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11, 10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8,
     9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6, 4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13],
    [4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1, 13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6,
     1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2, 6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12],
    [13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7, 1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2,
     7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8, 2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11],
]


def _perm(val, table, nbits):
    out = 0
    for pos in table:
        out = (out << 1) | ((val >> (nbits - pos)) & 1)
    return out


def _subkeys(key8):
    k = _perm(int.from_bytes(key8, "big"), _PC1, 64)
    c, d = k >> 28, k & 0xFFFFFFF
    keys = []
    for s in _SHIFTS:
        c = ((c << s) | (c >> (28 - s))) & 0xFFFFFFF
        d = ((d << s) | (d >> (28 - s))) & 0xFFFFFFF
        keys.append(_perm((c << 28) | d, _PC2, 56))
    return keys


def _des_block(block8, keys):
    v = _perm(int.from_bytes(block8, "big"), _IP, 64)
    left, right = v >> 32, v & 0xFFFFFFFF
    for k in keys:
        x = _perm(right, _E, 32) ^ k
        out = 0
        for i in range(8):
            six = (x >> (42 - 6 * i)) & 0x3F
            row = ((six & 0x20) >> 4) | (six & 1)
            col = (six >> 1) & 0xF
            out = (out << 4) | _S[i][row * 16 + col]
        left, right = right, left ^ _perm(out, _P, 32)
    return _perm((right << 32) | left, _FP, 64).to_bytes(8, "big")


def vnc_auth_response(password, challenge16):
    pw = password.encode("latin-1")[:8].ljust(8, b"\0")
    key = bytes(int("{:08b}".format(b)[::-1], 2) for b in pw)
    keys = _subkeys(key)
    return _des_block(challenge16[:8], keys) + _des_block(challenge16[8:], keys)


# ---------- minimal VNC (RFB) client ----------

KS = {"esc": 0xFF1B, "home": 0xFF50, "enter": 0xFF0D, "bsp": 0xFF08,
      "ctrl": 0xFFE3, "shift": 0xFFE1}


class VNC:
    def __init__(self, host, port, password):
        self.s = socket.create_connection((host, port), timeout=15)
        self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.read(12)
        self.s.sendall(b"RFB 003.008\n")
        n = self.read(1)[0]
        if n == 0:
            raise RuntimeError(self.read_str().decode("utf-8", "replace"))
        types = self.read(n)
        if 2 in types:
            self.s.sendall(b"\x02")
            self.s.sendall(vnc_auth_response(password, self.read(16)))
        elif 1 in types:
            self.s.sendall(b"\x01")
        else:
            raise RuntimeError("no supported VNC security type")
        if struct.unpack(">I", self.read(4))[0] != 0:
            raise RuntimeError("VNC password rejected")
        self.s.sendall(b"\x01")
        self.w, self.h = struct.unpack(">HH", self.read(4))
        self.read(16)
        self.read_str()
        pf = struct.pack(">BBBBHHHBBB3x", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
        self.s.sendall(b"\x00\x00\x00\x00" + pf)
        self.s.sendall(struct.pack(">BxHii", 2, 2, 0, -223))
        self.fb = bytearray(self.w * self.h * 4)

    def read(self, n):
        buf = bytearray()
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("VNC connection closed")
            buf += chunk
        return bytes(buf)

    def read_str(self):
        return self.read(struct.unpack(">I", self.read(4))[0])

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass

    def capture(self, path):
        while True:
            self.s.sendall(struct.pack(">BBHHHH", 3, 0, 0, 0, self.w, self.h))
            resized = False
            while True:
                t = self.read(1)[0]
                if t == 0:
                    self.read(1)
                    nrects = struct.unpack(">H", self.read(2))[0]
                    for _ in range(nrects):
                        x, y, w, h, enc = struct.unpack(">HHHHi", self.read(12))
                        if enc == 0:
                            data = self.read(w * h * 4)
                            row = w * 4
                            for r in range(h):
                                o = ((y + r) * self.w + x) * 4
                                self.fb[o:o + row] = data[r * row:(r + 1) * row]
                        elif enc == -223:
                            self.w, self.h = w, h
                            self.fb = bytearray(w * h * 4)
                            resized = True
                        else:
                            raise RuntimeError("unexpected VNC encoding %d" % enc)
                    break
                elif t == 1:
                    self.read(3)
                    self.read(struct.unpack(">H", self.read(2))[0] * 6)
                elif t == 2:
                    pass
                elif t == 3:
                    self.read(3)
                    self.read_str()
                else:
                    raise RuntimeError("unexpected VNC message %d" % t)
            if not resized:
                break
        img = Image.frombuffer("RGB", (self.w, self.h), bytes(self.fb), "raw", "BGRX", 0, 1)
        img.save(path, optimize=False, compress_level=1)

    def pointer(self, mask, x, y):
        x = max(0, min(self.w - 1, x))
        y = max(0, min(self.h - 1, y))
        self.s.sendall(struct.pack(">BBHH", 5, mask, x, y))

    def key(self, keysym, down):
        self.s.sendall(struct.pack(">BBxxI", 4, 1 if down else 0, keysym))

    def press(self, *keysyms):
        for k in keysyms:
            self.key(k, True)
        for k in reversed(keysyms):
            self.key(k, False)


# ---------- actions ----------

lock = threading.Lock()
state = {"vnc": None, "last": "page opened"}


def run(fn):
    with lock:
        for attempt in (1, 2):
            try:
                if state["vnc"] is None:
                    state["vnc"] = VNC(VNC_HOST, VNC_PORT, VNC_PASS)
                return fn(state["vnc"])
            except Exception:
                if state["vnc"] is not None:
                    state["vnc"].close()
                state["vnc"] = None
                if attempt == 2:
                    raise


def tap(c, x, y):
    c.pointer(0, x, y)
    c.pointer(1, x, y)
    time.sleep(0.05)
    c.pointer(0, x, y)


def long_press(c, x, y):
    c.pointer(0, x, y)
    c.pointer(1, x, y)
    time.sleep(1.2)
    c.pointer(0, x, y)


def swipe(c, direction):
    w, h = c.w, c.h
    cx, cy = w // 2, h // 2
    paths = {
        "up": ((cx, int(h * 0.75)), (cx, int(h * 0.25))),
        "down": ((cx, int(h * 0.25)), (cx, int(h * 0.75))),
        "left": ((int(w * 0.85), cy), (int(w * 0.15), cy)),
        "right": ((int(w * 0.15), cy), (int(w * 0.85), cy)),
        "notif": ((cx, 2), (cx, int(h * 0.6))),
    }
    (x1, y1), (x2, y2) = paths[direction]
    c.pointer(0, x1, y1)
    c.pointer(1, x1, y1)
    steps = 12
    for i in range(1, steps + 1):
        c.pointer(1, x1 + (x2 - x1) * i // steps, y1 + (y2 - y1) * i // steps)
        time.sleep(0.02)
    c.pointer(0, x2, y2)


def do_key(c, k):
    if k == "back":
        c.press(KS["esc"])
    elif k == "home":
        c.press(KS["home"])
    elif k == "recents":
        c.press(KS["ctrl"], KS["shift"], KS["esc"])
    elif k == "enter":
        c.press(KS["enter"])
    elif k == "backspace":
        c.press(KS["bsp"])
    else:
        raise KeyError(k)


def type_text(c, text):
    for ch in text:
        if ch == "\n":
            c.press(KS["enter"])
        elif 32 <= ord(ch) < 127:
            c.press(ord(ch))
        time.sleep(0.01)


PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Green Phone screen</title>
<style>
body {{ background:#fafafa; color:#111; font-family:sans-serif; margin:12px; }}
.bar {{ margin:8px 0; }}
button, input[type=submit] {{ font-size:16px; padding:8px 12px; margin:2px; }}
input[type=text] {{ font-size:16px; padding:8px; width:320px; }}
.scr {{ border:2px solid #333; display:block; }}
.status {{ font-size:14px; color:#333; }}
</style></head><body>
<div class="status">Last action: {last}. Screenshot taken at {stamp}. Screen size {w} by {h}.</div>
<form method="get" action="/{tok}/tap">
<div class="bar">
<label><input type="radio" name="mode" value="tap" checked> Tap mode</label>
<label><input type="radio" name="mode" value="long"> Long press mode</label>
</div>
<input class="scr" type="image" name="p" alt="Green Phone screen, click to tap"
 src="/{tok}/shot.png?n={nonce}" width="{w}" height="{h}">
</form>
<form method="get" action="/{tok}/key" class="bar">
<button name="k" value="back">Back</button>
<button name="k" value="home">Home</button>
<button name="k" value="recents">Recent apps</button>
<button name="k" value="enter">Enter key</button>
<button name="k" value="backspace">Backspace</button>
</form>
<form method="get" action="/{tok}/swipe" class="bar">
<button name="d" value="up">Swipe up (scroll down)</button>
<button name="d" value="down">Swipe down (scroll up)</button>
<button name="d" value="left">Swipe left</button>
<button name="d" value="right">Swipe right</button>
<button name="d" value="notif">Open notifications</button>
</form>
<form method="get" action="/{tok}/type" class="bar">
<input type="text" name="t" placeholder="Text to type into the focused field" autocomplete="off">
<input type="submit" value="Type it">
</form>
<form method="get" action="/{tok}/" class="bar">
<input type="submit" value="Refresh screenshot">
</form>
</body></html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Robots-Tag", "noindex")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def back_to_page(self):
        time.sleep(SETTLE)
        self.send_response(303)
        self.send_header("Location", "/" + TOKEN + "/")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        parts = u.path.strip("/").split("/")
        q = urllib.parse.parse_qs(u.query)
        if not parts or not secrets.compare_digest(parts[0], TOKEN):
            return self.send(404, b"not found", "text/plain")
        action = parts[1] if len(parts) > 1 else ""
        try:
            if action == "":
                size = run(lambda c: (c.capture(SHOT), (c.w, c.h))[1])
                body = PAGE.format(tok=TOKEN, last=html.escape(state["last"]),
                                   stamp=time.strftime("%H:%M:%S"), w=size[0], h=size[1],
                                   nonce=secrets.token_hex(4))
                return self.send(200, body.encode())
            if action == "shot.png":
                with lock, open(SHOT, "rb") as f:
                    data = f.read()
                return self.send(200, data, "image/png")
            if action == "tap":
                x = int(q["p.x"][0])
                y = int(q["p.y"][0])
                if q.get("mode", ["tap"])[0] == "long":
                    run(lambda c: long_press(c, x, y))
                    state["last"] = "long press at %d,%d" % (x, y)
                else:
                    run(lambda c: tap(c, x, y))
                    state["last"] = "tap at %d,%d" % (x, y)
                return self.back_to_page()
            if action == "key":
                k = q["k"][0]
                run(lambda c: do_key(c, k))
                state["last"] = "key " + k
                return self.back_to_page()
            if action == "swipe":
                d = q["d"][0]
                run(lambda c: swipe(c, d))
                state["last"] = "swipe " + d
                return self.back_to_page()
            if action == "type":
                t = q.get("t", [""])[0]
                run(lambda c: type_text(c, t))
                state["last"] = "typed %d characters" % len(t)
                return self.back_to_page()
        except (KeyError, ValueError):
            return self.send(400, b"bad request", "text/plain")
        except Exception as e:
            return self.send(502, ("VNC error: %s. Is droidVNC-NG started?" % e).encode(),
                             "text/plain; charset=utf-8")
        return self.send(404, b"not found", "text/plain")


if __name__ == "__main__":
    print("greenscreen v2 listening on 127.0.0.1:%d" % PORT, flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
