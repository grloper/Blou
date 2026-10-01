"""Run the Python protocol core with synthetic input; no RDP connection."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from blou.layout import LayoutBuilder
from blou.security import CertificatePinningVerifier
from blou.viewport import CoordinateMapper, ViewportDimensions

layout = LayoutBuilder.create_horizontal_row(count=3)
mapper = CoordinateMapper(layout, ViewportDimensions(1920, 1080), initial_monitor=2)
synthetic_certificate = b"explicit synthetic fixture, not an X.509 certificate"
verifier = CertificatePinningVerifier(hashlib.sha256(synthetic_certificate).hexdigest())
result = {
    "input_kind": "synthetic local fixture; no RDP or TLS connection",
    "monitor_count": layout.count,
    "composite_size": [layout.bounding_width, layout.bounding_height],
    "active_monitor": mapper.active_monitor_index,
    "touch_100_100_maps_to": mapper.screen_to_server(100, 100),
    "matching_synthetic_bytes": verifier.verify_certificate(synthetic_certificate),
    "malformed_peer_input": verifier.verify_certificate("invalid fingerprint"),
}
output = Path(__file__).resolve().parents[1] / "docs/verification/local-core-demo.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
