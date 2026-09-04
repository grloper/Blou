"""
Unit tests for Blou Layout Fabrication & Invariant Enforcement.
"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from blou.layout import LayoutBuilder, DesktopLayout, VirtualMonitor


class TestLayoutBuilder(unittest.TestCase):
    def test_create_horizontal_row_defaults(self):
        layout = LayoutBuilder.create_horizontal_row(count=3, monitor_width=1920, monitor_height=1080)
        self.assertEqual(layout.count, 3)
        self.assertEqual(layout.bounding_width, 5760)
        self.assertEqual(layout.bounding_height, 1080)

        # Check monitors
        m0 = layout.get_monitor(0)
        self.assertEqual((m0.x, m0.y, m0.width, m0.height), (0, 0, 1920, 1080))
        self.assertTrue(m0.is_primary)

        m1 = layout.get_monitor(1)
        self.assertEqual((m1.x, m1.y, m1.width, m1.height), (1920, 0, 1920, 1080))
        self.assertFalse(m1.is_primary)

        m2 = layout.get_monitor(2)
        self.assertEqual((m2.x, m2.y, m2.width, m2.height), (3840, 0, 1920, 1080))
        self.assertFalse(m2.is_primary)

    def test_create_grid_2x2(self):
        layout = LayoutBuilder.create_grid_2x2(monitor_width=1920, monitor_height=1080)
        self.assertEqual(layout.count, 4)
        self.assertEqual(layout.bounding_width, 3840)
        self.assertEqual(layout.bounding_height, 2160)

        self.assertEqual((layout.get_monitor(0).x, layout.get_monitor(0).y), (0, 0))
        self.assertEqual((layout.get_monitor(1).x, layout.get_monitor(1).y), (1920, 0))
        self.assertEqual((layout.get_monitor(2).x, layout.get_monitor(2).y), (0, 1080))
        self.assertEqual((layout.get_monitor(3).x, layout.get_monitor(3).y), (1920, 1080))

    def test_reject_primary_not_at_origin(self):
        invalid_monitors = [
            VirtualMonitor(0, 100, 0, 1920, 1080, is_primary=True),  # Primary not at (0,0)
            VirtualMonitor(1, 2020, 0, 1920, 1080, is_primary=False),
        ]
        layout = DesktopLayout(invalid_monitors, 4000, 1080)
        with self.assertRaises(ValueError) as ctx:
            LayoutBuilder.validate_layout(layout)
        self.assertIn("Primary monitor MUST be positioned at (0, 0)", str(ctx.exception))

    def test_reject_multiple_primary_monitors(self):
        invalid_monitors = [
            VirtualMonitor(0, 0, 0, 1920, 1080, is_primary=True),
            VirtualMonitor(1, 1920, 0, 1920, 1080, is_primary=True),  # Second primary
        ]
        layout = DesktopLayout(invalid_monitors, 3840, 1080)
        with self.assertRaises(ValueError) as ctx:
            LayoutBuilder.validate_layout(layout)
        self.assertIn("Layout must contain exactly 1 primary monitor", str(ctx.exception))

    def test_reject_overlapping_monitors(self):
        invalid_monitors = [
            VirtualMonitor(0, 0, 0, 1920, 1080, is_primary=True),
            VirtualMonitor(1, 1000, 0, 1920, 1080, is_primary=False),  # Overlaps [0..1920]
        ]
        layout = DesktopLayout(invalid_monitors, 3840, 1080)
        with self.assertRaises(ValueError) as ctx:
            LayoutBuilder.validate_layout(layout)
        self.assertIn("overlap in coordinate space", str(ctx.exception))

    def test_reject_negative_coordinates(self):
        invalid_monitors = [
            VirtualMonitor(0, 0, 0, 1920, 1080, is_primary=True),
            VirtualMonitor(1, -1920, 0, 1920, 1080, is_primary=False),  # Negative x
        ]
        layout = DesktopLayout(invalid_monitors, 3840, 1080)
        with self.assertRaises(ValueError) as ctx:
            LayoutBuilder.validate_layout(layout)
        self.assertIn("negative coordinate", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
