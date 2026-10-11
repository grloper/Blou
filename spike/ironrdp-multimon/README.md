# IronRDP multi-monitor spike (offline)

Question: can IronRDP declare a client-fabricated 3x1920x1080 layout (Blou's "layout lie")?

Run: `cargo test` (needs network once to fetch the pinned git rev; no RDP server needed).

Pinned: Devolutions/IronRDP `e4143f26306a6639a889d80c1c484ca69c365a8f` (master, 2026-10-10).
`Config::monitor_layout` is NOT in crates.io `ironrdp-connector 0.10.0` (2026-07-10); it landed in PR #1675 (`063efcdc`, 2026-08-16).

What the tests prove (offline):
- `ClientMonitorData` encodes to the exact MS-RDPBCGR TS_UD_CS_MONITOR body (flags, count=3, 3x20 bytes, inclusive right/bottom, primary at 0,0).
- Driving the real `ClientConnector` (X.224 request -> synthetic HYBRID confirm -> NLA step -> Basic Settings) emits an MCS Connect-Initial whose decoded GCC client blocks carry those 3 monitors, a 5760x1080 core desktop size, and SUPPORT_MONITOR_LAYOUT_PDU.
- The monitor block is omitted unless the server confirm sets EXTENDED_CLIENT_DATA_SUPPORTED.
- `ironrdp-displaycontrol` encodes a 3-monitor DISPLAYCONTROL_MONITOR_LAYOUT_PDU; odd widths are silently rounded down.

What it does NOT prove (UNVERIFIED, Phase 0 gate): that a real Windows host creates 3 displays; NLA/TLS against a real host; Android linking/rendering.
