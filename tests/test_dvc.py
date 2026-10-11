"""
Unit tests for Blou Display Update Virtual Channel (MS-RDPEDISP) Protocol Encoder.
"""
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from blou.layout import LayoutBuilder
from blou.dvc import (
    DisplayControlEncoder,
    DISPLAYCONTROL_PDU_TYPE_CAPS,
    DISPLAYCONTROL_PDU_TYPE_LAYOUT,
    DISPLAYCONTROL_MONITOR_PRIMARY
)


class TestDisplayControlEncoder(unittest.TestCase):
    def test_encode_caps_pdu(self):
        caps = DisplayControlEncoder.encode_caps_pdu(max_num_monitors=4, max_monitor_area_factor=1)
        self.assertEqual(len(caps), 20)

        pdu_type, length, max_mon, area_a, area_b = struct.unpack("<IIIII", caps)
        self.assertEqual(pdu_type, DISPLAYCONTROL_PDU_TYPE_CAPS)
        self.assertEqual(length, 20)
        self.assertEqual(max_mon, 4)
        self.assertEqual(area_a, 1)
        self.assertEqual(area_b, 1)

    def test_encode_3_monitor_layout_pdu(self):
        layout = LayoutBuilder.create_horizontal_row(count=3, monitor_width=1920, monitor_height=1080)
        pdu = DisplayControlEncoder.encode_monitor_layout_pdu(layout)

        # Header is 16 bytes, 3 monitors * 40 bytes = 120 bytes -> total 136 bytes
        expected_len = 16 + (3 * 40)
        self.assertEqual(len(pdu), expected_len)

        pdu_type, length, flags, num_mon = struct.unpack("<IIII", pdu[:16])
        self.assertEqual(pdu_type, DISPLAYCONTROL_PDU_TYPE_LAYOUT)
        self.assertEqual(length, expected_len)
        self.assertEqual(num_mon, 3)

        # Inspect monitor 0 (primary at 0, 0)
        m0_flags, m0_left, m0_top, m0_w, m0_h = struct.unpack("<IiiII", pdu[16:36])
        self.assertEqual(m0_flags & DISPLAYCONTROL_MONITOR_PRIMARY, DISPLAYCONTROL_MONITOR_PRIMARY)
        self.assertEqual((m0_left, m0_top), (0, 0))
        self.assertEqual((m0_w, m0_h), (1920, 1080))

        # Inspect monitor 1 (secondary at 1920, 0)
        m1_flags, m1_left, m1_top, m1_w, m1_h = struct.unpack("<IiiII", pdu[56:76])
        self.assertEqual(m1_flags & DISPLAYCONTROL_MONITOR_PRIMARY, 0)
        self.assertEqual((m1_left, m1_top), (1920, 0))
        self.assertEqual((m1_w, m1_h), (1920, 1080))

        # Inspect monitor 2 (secondary at 3840, 0)
        m2_flags, m2_left, m2_top, m2_w, m2_h = struct.unpack("<IiiII", pdu[96:116])
        self.assertEqual(m2_flags & DISPLAYCONTROL_MONITOR_PRIMARY, 0)
        self.assertEqual((m2_left, m2_top), (3840, 0))
        self.assertEqual((m2_w, m2_h), (1920, 1080))


class TestDisplayControlProtocolRegression(unittest.TestCase):
    def test_layout_entry_size_and_unknown_physical_dimensions(self):
        for count in range(1, 5):
            pdu = DisplayControlEncoder.encode_monitor_layout_pdu(LayoutBuilder.create_horizontal_row(count=count))
            self.assertEqual(struct.unpack_from("<I", pdu, 8)[0], 40)
            for i in range(count):
                self.assertEqual(struct.unpack_from("<IIIII", pdu, 16 + i * 40 + 20), (0, 0, 0, 100, 100))

    def test_odd_width_is_rejected_without_rounding(self):
        layout = LayoutBuilder.create_horizontal_row(count=3, monitor_width=1921)
        with self.assertRaises(ValueError):
            DisplayControlEncoder.encode_monitor_layout_pdu(layout)
        self.assertEqual(layout.get_monitor(1).x, 1921)
        self.assertEqual(layout.get_monitor(1).width, 1921)

    def test_reject_out_of_product_or_protocol_range(self):
        for count in (5, 16):
            with self.assertRaises(ValueError):
                DisplayControlEncoder.encode_monitor_layout_pdu(LayoutBuilder.create_horizontal_row(count=count))
        for w, h in ((199, 1080), (8194, 1080), (1920, 199), (1920, 8193)):
            with self.assertRaises(ValueError):
                DisplayControlEncoder.encode_monitor_layout_pdu(LayoutBuilder.create_horizontal_row(count=1, monitor_width=w, monitor_height=h))


if __name__ == "__main__":
    unittest.main()
