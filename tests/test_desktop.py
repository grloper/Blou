import io
import json
import sys
import unittest
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from blou.desktop import Monitor, Session, serve


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.points = []
        image = Image.new("RGB", (320, 180), "blue")
        data = io.BytesIO()
        image.save(data, "JPEG")
        self.session = Session([Monitor("Left", -1920, -200, 1920, 1080),
                                Monitor("Right", 0, 0, 2560, 1440)],
                               lambda m: data.getvalue(), lambda x,y: self.points.append((x,y)))
        self.server = serve(self.session)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.session.consent(False)
        self.server.shutdown()
        self.server.server_close()

    def get(self, path, payload=None, headers=None):
        req = Request(self.base + path, data=None if payload is None else json.dumps(payload).encode(),
                      headers=headers or {"Authorization": "Bearer " + self.session.token})
        return urlopen(req, timeout=3)

    def rejected(self, path, status, payload=None, headers=None):
        with self.assertRaises(HTTPError) as error:
            self.get(path, payload, headers)
        self.assertEqual(error.exception.code, status)
        error.exception.close()

    def test_auth_and_dns_rebinding(self):
        self.rejected("/monitors", 403, headers={"Authorization": "Bearer wrong"})
        self.rejected("/monitors", 403, headers={"Authorization": "Bearer é"})
        self.rejected("/monitors", 403, headers={"Authorization": "Bearer " + self.session.token,
                                                "Host": "evil.example"})

    def test_frames_consent_decode_and_reconnect(self):
        self.rejected("/frame", 403)
        self.session.consent(True)
        for sequence in (1,2):
            with self.get("/frame?monitor=1") as response:
                image = Image.open(io.BytesIO(response.read()))
                self.assertEqual(image.size, (320,180))
                self.assertEqual(int(response.headers["X-Sequence"]), sequence)
        self.session.consent(False)
        self.rejected("/frame", 403)
        self.session.consent(True)
        with self.get("/frame") as response:
            self.assertEqual(response.status, 200)

    def test_pointer_gates_and_negative_monitor_origin(self):
        payload = {"monitor": 0, "x": .5, "y": .5}
        self.session.consent(True)
        self.rejected("/pointer",403,payload)
        self.assertEqual(self.points, [])
        self.session.consent(True,True)
        with self.get("/pointer",payload) as response:
            self.assertEqual(json.load(response)["point"],[-960,340])
        self.session.consent(False,True)
        self.rejected("/pointer",403,payload)
        self.assertEqual(self.points,[(-960,340)])

    def test_invalid_geometry_and_payload(self):
        self.session.consent(True,True)
        for index in (-1,2):
            self.rejected(f"/frame?monitor={index}",400)
        for x in (-.01,1,True,float("nan"),"0.2"):
            self.rejected("/pointer",400,{"monitor":0,"x":x,"y":.2})
        self.rejected("/pointer",400,{"monitor":True,"x":.1,"y":.2})
        self.assertEqual(self.points,[])

    def test_capture_failure_is_retryable(self):
        self.session.consent(True)
        def fail(m):
            raise OSError("Desktop locked")
        self.session.grab=fail
        self.rejected("/frame",503)

    def test_revoke_during_slow_capture_discards_frame(self):
        entered, released = threading.Event(), threading.Event()
        errors = []
        def slow(m):
            entered.set()
            released.wait(2)
            return b"private frame"
        self.session.grab = slow
        self.session.consent(True)
        def grab():
            try:
                self.session.frame(0)
            except PermissionError:
                errors.append("revoked")
        thread = threading.Thread(target=grab)
        thread.start()
        self.assertTrue(entered.wait(1))
        self.session.consent(False)
        released.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors,["revoked"])


if __name__ == "__main__":
    unittest.main()
