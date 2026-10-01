"""Real Windows capture/loopback proof; never saves desktop pixels."""
import io
import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from blou.desktop import Session, monitors, serve

session = Session(monitors())
server = serve(session)
session.consent(True)
results = []
try:
    for index, monitor in enumerate(session.displays):
        start = time.perf_counter()
        req = Request(f"http://127.0.0.1:{server.server_port}/frame?monitor={index}",
                      headers={"Authorization":"Bearer "+session.token})
        with urlopen(req,timeout=10) as response:
            data = response.read()
            image = Image.open(io.BytesIO(data))
            image.load()
            results.append({"monitor":vars(monitor),"decoded_size":image.size,
                            "jpeg_bytes":len(data),"capture_ms":float(response.headers["X-Capture-Ms"]),
                            "loopback_ms":round((time.perf_counter()-start)*1000,2)})
    print(json.dumps({"real_capture_loopback":results,"input_injection":"not exercised",
                      "desktop_pixels_saved":False},indent=2))
finally:
    session.consent(False)
    server.shutdown()
    server.server_close()
