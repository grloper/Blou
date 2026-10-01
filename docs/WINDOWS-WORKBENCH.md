# Windows desktop workbench

Blou now has a runnable local host/viewer prototype. It captures a selected
physical Windows monitor, encodes JPEG, transports it over authenticated loopback
HTTP, and decodes it in a resizable Tk viewer. This is a development milestone,
not an RDP replacement or an internet-ready remote-access service.

## Run

Install Python 3.13, then from this checkout:

```powershell
python -m pip install -r requirements-desktop.txt
python scripts/blou_desktop.py
```

Enable **Allow local screen preview** to begin capture. Choose a monitor.
The viewer fits the image without changing aspect ratio. Enable pointer movement
only when wanted; clicking inside the preview then moves the Windows pointer.
It does not send clicks or keystrokes. Uncheck sharing to revoke capture and
control. Close the window to terminate the listener. Nothing starts at boot.

Build the unsigned executable with `scripts/build_windows.ps1`. Run
`dist/Blou-Local.exe`; Python does not need to be installed on the target machine.
`Blou-Local.exe --self-test` runs a fixture transport/package smoke test without
screen capture or input. Rebuilding is supported; bit-for-bit binary identity
across hosts has not been established. No code-signing certificate is bundled.

## Session boundary

The server binds exclusively to `127.0.0.1` on a random port, checks the exact
Host header and a random 256-bit bearer secret, permits no CORS, and never logs
the secret or desktop bytes. Capture and pointer movement start disabled.
Revoking consent during capture discards the captured frame. The UI clears its
old frame on monitor changes and retries a disconnected/paused stream. Local
processes with access to this process are outside the protection boundary.
No firewall, VPN, port-forwarding or persistent-access changes are made.

## Executed evidence — October 1, 2026

36 tests passed, including actual localhost HTTP requests, JPEG decode,
negative-origin monitor coordinates, invalid/NaN input rejection, Host/bearer
rejection, non-ASCII headers, reconnect, capture errors and revocation during
slow capture. Fixture pointer callbacks prove mapping, not OS input delivery.

On Windows 11/Python 3.13, actual enumeration found two physical displays:
1920×1080 at (-1920,0), and 2560×1440 at (0,0). Outside the restricted sandbox,
`scripts/verify_desktop.py` captured and transported both through localhost,
decoding each to 1280×720 JPEG. One sample measured 361.62/311.78 ms capture and
433.21/425.41 ms total loopback request/decode. This is a small sample, not a
latency benchmark or a low-latency streaming claim. Desktop pixels were neither
saved nor uploaded. Sandbox capture failed with `OSError: screen grab failed`.

Independent source review identified stale monitor bounds, delayed revocation
and malformed-header handling; those were fixed before final packaging.

## Remaining work

Real OS pointer delivery, visible packaged UI interaction and captured demo
footage still require an accessible interactive desktop automation session.
The current environment exposes no `node_repl` Computer Use tool. Audio,
keyboard/click injection, hardware video codecs, unattended operation, Android,
TLS remote sessions, network pairing, NAT traversal and virtual monitor drivers
are not implemented or tested here. No production security claim is made.

## Architecture direction and primary sources

Keep the existing fabricated RDP topology helpers separate from physical
monitor coordinates, which can be negative. For a full remote product, evaluate
a pinned FreeRDP client or a compatible licensed streaming backend before
introducing custom codecs or drivers. Do not merge GPL components into a
proprietary distribution without deciding license compatibility.

- [Microsoft EnumDisplayMonitors](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumdisplaymonitors)
- [Microsoft SetCursorPos](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setcursorpos)
- [Pillow ImageGrab](https://pillow.readthedocs.io/en/stable/reference/ImageGrab.html)
- [Sunshine source and license](https://github.com/LizardByte/Sunshine)
- [Moonlight Qt source and license](https://github.com/moonlight-stream/moonlight-qt)
- [FreeRDP source and license](https://github.com/FreeRDP/FreeRDP)
