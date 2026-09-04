"""
Blou Display Update Virtual Channel (MS-RDPEDISP) Protocol Encoder.

Implements DISPLAYCONTROL_MONITOR_LAYOUT PDU construction for dynamic
monitor layout reconfiguration mid-session without reconnecting.
"""
import struct
from typing import List
from .layout import DesktopLayout, VirtualMonitor

# PDU Types per [MS-RDPEDISP] §2.2.2
DISPLAYCONTROL_PDU_TYPE_CAPS = 0x00000005
DISPLAYCONTROL_PDU_TYPE_LAYOUT = 0x00000002

DISPLAYCONTROL_MONITOR_PRIMARY = 0x00000001


class DisplayControlEncoder:
    """Encodes MS-RDPEDISP dynamic monitor layout PDUs."""

    @staticmethod
    def encode_caps_pdu(max_num_monitors: int = 4, max_monitor_area_factor: int = 1) -> bytes:
        """
        Encodes DISPLAYCONTROL_CAPS_PDU (§2.2.2.1):
        - type (uint32)
        - length (uint32)
        - maxNumMonitors (uint32)
        - maxMonitorAreaFactorA (uint32)
        - maxMonitorAreaFactorB (uint32)
        """
        pdu_type = DISPLAYCONTROL_PDU_TYPE_CAPS
        length = 20
        return struct.pack(
            "<IIIII",
            pdu_type,
            length,
            max_num_monitors,
            max_monitor_area_factor,
            1  # factor B
        )

    @staticmethod
    def encode_monitor_layout_pdu(layout: DesktopLayout) -> bytes:
        """
        Encodes DISPLAYCONTROL_MONITOR_LAYOUT_PDU (§2.2.2.2):
        Header:
          - type (uint32) = 0x00000002
          - length (uint32) = 16 + (NumMonitors * 40)
          - flags (uint32) = 0
          - numMonitors (uint32)
        Per-Monitor Entries (40 bytes each):
          - flags (uint32): bit 0 = DISPLAYCONTROL_MONITOR_PRIMARY
          - left (int32)
          - top (int32)
          - width (uint32)
          - height (uint32)
          - physicalWidth (uint32)
          - physicalHeight (uint32)
          - orientation (uint32): 0 = ORIENTATION_LANDSCAPE
          - desktopScaleFactor (uint32): 100 = 100%
          - deviceScaleFactor (uint32): 100 = 100%
        """
        pdu_type = DISPLAYCONTROL_PDU_TYPE_LAYOUT
        num_monitors = layout.count
        monitor_entry_size = 40
        total_length = 16 + (num_monitors * monitor_entry_size)

        payload = bytearray()
        payload.extend(struct.pack("<IIII", pdu_type, total_length, 0, num_monitors))

        for mon in layout.monitors:
            flags = DISPLAYCONTROL_MONITOR_PRIMARY if mon.is_primary else 0
            payload.extend(
                struct.pack(
                    "<IiiIIIIIII",
                    flags,
                    mon.x,
                    mon.y,
                    mon.width,
                    mon.height,
                    mon.width,   # physical width mm placeholder
                    mon.height,  # physical height mm placeholder
                    0,           # ORIENTATION_LANDSCAPE
                    100,         # desktopScaleFactor
                    100          # deviceScaleFactor
                )
            )

        return bytes(payload)
