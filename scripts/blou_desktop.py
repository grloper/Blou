"""Launch Blou's local host/client validation workbench."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ctypes
import io
import json
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from urllib.request import Request, urlopen
from PIL import Image, ImageTk
from blou.desktop import Session, monitors, serve


def main():
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    root.title("Blou | Local desktop workbench")
    root.geometry("1080x780")
    root.configure(bg="#111923")
    session = Session(monitors())
    server = serve(session)
    base = f"http://127.0.0.1:{server.server_port}"
    ttk.Label(root, text="BLOU  /  LOCAL DESKTOP WORKBENCH", font=("Segoe UI", 18, "bold")).pack(pady=14)
    ttk.Label(root, text="Loopback only • JPEG preview • No background access • Close to end session").pack()
    bar = ttk.Frame(root)
    bar.pack(pady=12)
    sharing, control = tk.BooleanVar(), tk.BooleanVar()
    def consent():
        session.consent(sharing.get(), control.get())
        if not sharing.get():
            canvas.delete("all")
    ttk.Checkbutton(bar, text="Allow local screen preview", variable=sharing, command=consent).pack(side="left", padx=12)
    ttk.Checkbutton(bar, text="Allow pointer movement (no clicks/keys)", variable=control, command=consent).pack(side="left", padx=12)
    choice = ttk.Combobox(bar, state="readonly", width=24, values=[
        f"{m.name}: {m.width} × {m.height}" for m in session.displays])
    choice.current(0)
    choice.pack(side="left")
    canvas = tk.Canvas(root, bg="#080e15", highlightthickness=0)
    canvas.pack(fill="both", expand=True, padx=20, pady=8)
    status = ttk.Label(root, text="Preview paused. Host consent is required.")
    status.pack(pady=12)
    state = {"monitor": 0, "bounds": None, "last_pointer": 0}
    def select_monitor(event):
        state.update(monitor=choice.current(), bounds=None)
        canvas.delete("all")
    choice.bind("<<ComboboxSelected>>", select_monitor)
    inbox = queue.Queue(maxsize=1)
    stopped = threading.Event()
    def request(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(base + path, data=data, headers={"Authorization": "Bearer " + session.token,
                                                      "Content-Type": "application/json"})
        return urlopen(req, timeout=2)
    def worker():
        while not stopped.is_set():
            index = state["monitor"]
            try:
                start = time.perf_counter()
                with request(f"/frame?monitor={index}") as response:
                    raw = response.read()
                    image = Image.open(io.BytesIO(raw))
                    image.load()
                    result = (index, image, f"Frame {response.headers['X-Sequence']} | capture {response.headers['X-Capture-Ms']} ms | loopback {(time.perf_counter()-start)*1000:.1f} ms | {len(raw)//1024} KiB")
            except Exception:
                result = (index, None, "Paused or disconnected. Retrying automatically…")
                stopped.wait(0.3)
            try:
                inbox.put_nowait(result)
            except queue.Full:
                pass
    threading.Thread(target=worker, daemon=True).start()
    def refresh():
        try:
            index, image, message = inbox.get_nowait()
            if index == state["monitor"] and sharing.get() and image is not None:
                image.thumbnail((max(1, canvas.winfo_width()), max(1, canvas.winfo_height())))
                photo = ImageTk.PhotoImage(image)
                canvas.photo = photo
                x, y = (canvas.winfo_width()-image.width)//2, (canvas.winfo_height()-image.height)//2
                canvas.delete("all")
                canvas.create_image(x, y, image=photo, anchor="nw")
                state["bounds"] = (x, y, image.width, image.height)
            else:
                state["bounds"] = None
                canvas.delete("all")
            status.configure(text=message)
        except queue.Empty:
            pass
        if not stopped.is_set():
            root.after(40, refresh)
    def pointer(event):
        bounds = state["bounds"]
        if not control.get() or not sharing.get() or bounds is None:
            return
        x, y, width, height = bounds
        nx, ny = (event.x-x)/width, (event.y-y)/height
        if not 0 <= nx < 1 or not 0 <= ny < 1 or time.monotonic()-state["last_pointer"] < 0.1:
            return
        state["last_pointer"] = time.monotonic()
        payload = {"monitor": state["monitor"], "x": nx, "y": ny}
        def send():
            try:
                with request("/pointer", payload):
                    pass
            except Exception:
                pass
        threading.Thread(target=send, daemon=True).start()
    canvas.bind("<Button-1>", pointer)
    def close():
        session.consent(False)
        stopped.set()
        server.shutdown()
        server.server_close()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", close)
    refresh()
    root.mainloop()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        # Frozen-import and transport smoke test; no desktop capture or input.
        from blou.desktop import Monitor
        from PIL import Image
        image = Image.new("RGB", (64, 32), "#1b7e99")
        encoded = io.BytesIO()
        image.save(encoded, "JPEG")
        session = Session([Monitor("Fixture", 0, 0, 64, 32)], lambda m: encoded.getvalue())
        session.consent(True)
        server = serve(session)
        req = Request(f"http://127.0.0.1:{server.server_port}/frame",
                      headers={"Authorization": "Bearer " + session.token})
        with urlopen(req, timeout=3) as response:
            decoded = Image.open(io.BytesIO(response.read()))
            assert decoded.size == (64,32)
        server.shutdown()
        server.server_close()
    else:
        main()
