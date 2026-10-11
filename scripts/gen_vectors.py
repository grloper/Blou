"""Emit deterministic parity vectors from the Python reference, without network access."""
import json
from dataclasses import asdict
from pathlib import Path

from blou.dvc import DisplayControlEncoder
from blou.layout import LayoutBuilder
from blou.security import CertificatePinningVerifier, HardwareKeystorePolicy
from blou.viewport import CoordinateMapper, Rect, SwipeNavigationController, ViewportDimensions


def generate_vectors():
    layouts = []
    for count in range(1, 5):
        layout = LayoutBuilder.create_horizontal_row(count=count)
        layouts.append({
            "kind": "row", "count": count,
            "bounds": [layout.bounding_width, layout.bounding_height],
            "monitors": [asdict(m) for m in layout.monitors],
            "dvc": list(DisplayControlEncoder.encode_monitor_layout_pdu(layout)),
        })
    grid = LayoutBuilder.create_grid_2x2()
    layouts.append({
        "kind": "grid", "count": 4, "bounds": [grid.bounding_width, grid.bounding_height],
        "monitors": [asdict(m) for m in grid.monitors],
        "dvc": list(DisplayControlEncoder.encode_monitor_layout_pdu(grid)),
    })
    row = LayoutBuilder.create_horizontal_row(count=3)
    viewport = []
    for phone in [(2340, 1080), (1080, 2340), (1000, 500)]:
        for monitor in range(3):
            mapper = CoordinateMapper(row, ViewportDimensions(*phone), monitor)
            screens = [(210, 0), (1170, 540), (50, 540), (phone[0] / 2, phone[1] / 2)]
            servers = [(960, 540), (2000, 500), (3840, 0)]
            damage = [Rect(2000, 100, 500, 300), Rect(100, 100, 500, 300), Rect(1500, 0, 1000, 500)]
            viewport.append({
                "phone": phone, "monitor": monitor,
                "transform": [mapper.scale, mapper.offset_x, mapper.offset_y],
                "screen": [{"input": p, "output": mapper.screen_to_server(*p)} for p in screens],
                "server": [{"input": p, "output": mapper.server_to_screen(*p)} for p in servers],
                "damage": [{"input": asdict(d), "output": asdict(c) if (c := mapper.clip_damage_rect(d)) else None} for d in damage],
            })
    swipes = []
    for initial, start, end in [(0, 500, 200), (0, 500, 450), (2, 200, 600), (0, 200, 600), (2, 800, 200)]:
        mapper = CoordinateMapper(row, ViewportDimensions(1000, 500), initial)
        controller = SwipeNavigationController(mapper)
        controller.on_touch_down(start, 250)
        delta = controller.on_touch_move(end, 250)
        switched = controller.on_touch_up(end, 250)
        swipes.append({"initial": initial, "start": start, "end": end, "delta": delta, "switched": switched, "active": mapper.active_monitor_index})
    synthetic = b"MIIB...SAMPLE_X509_CERTIFICATE_DER_BYTES...1234567890"
    fingerprint = CertificatePinningVerifier.compute_cert_fingerprint(synthetic)
    return {
        "scope": "offline Python parity; synthetic security bytes; DVC cross-checked against pinned IronRDP",
        "layouts": layouts, "viewport": viewport, "swipes": swipes,
        "caps": list(DisplayControlEncoder.encode_caps_pdu(4, 1)),
        "pin": {"synthetic": list(synthetic), "sha256": fingerprint},
        "keystore": HardwareKeystorePolicy.get_security_manifest(),
    }


if __name__ == "__main__":
    output = Path(__file__).resolve().parents[1] / "tests/vectors/portable-core.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(generate_vectors(), indent=2) + "\n", encoding="utf-8")
    print("generated tests/vectors/portable-core.json")
