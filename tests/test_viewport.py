"""
Unit tests for Blou Viewport and Coordinate Translation Subsystem.
"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from blou.layout import LayoutBuilder
from blou.viewport import CoordinateMapper, ViewportDimensions, Rect, SwipeNavigationController


class TestCoordinateMapper(unittest.TestCase):
    def setUp(self):
        # 3x 1920x1080 side-by-side: 5760x1080 total
        self.layout = LayoutBuilder.create_horizontal_row(count=3, monitor_width=1920, monitor_height=1080)
        # S24 Ultra screen: 1080x2340 (portrait) or 2340x1080 (landscape)
        self.landscape_phone = ViewportDimensions(width=2340, height=1080)
        self.mapper = CoordinateMapper(self.layout, self.landscape_phone, initial_monitor=0)

    def test_initial_state_on_monitor_zero(self):
        self.assertEqual(self.mapper.active_monitor_index, 0)
        mon = self.mapper.active_monitor
        self.assertEqual(mon.x, 0)
        self.assertEqual(mon.y, 0)
        self.assertEqual(mon.width, 1920)
        self.assertEqual(mon.height, 1080)

    def test_screen_to_server_monitor_zero(self):
        # In landscape (2340x1080), 1920x1080 monitor fits vertically (scale = 1.0)
        # Pillarbox offset_x = (2340 - 1920) / 2 = 210 px
        self.assertEqual(self.mapper.scale, 1.0)
        self.assertEqual(self.mapper.offset_x, 210.0)
        self.assertEqual(self.mapper.offset_y, 0.0)

        # Touch at left edge of monitor: (210, 0) -> should map to server (0, 0)
        server_pt = self.mapper.screen_to_server(210.0, 0.0)
        self.assertIsNotNone(server_pt)
        self.assertEqual(server_pt, (0, 0))

        # Touch at center of monitor: (210 + 960, 540) = (1170, 540) -> server (960, 540)
        center_pt = self.mapper.screen_to_server(1170.0, 540.0)
        self.assertEqual(center_pt, (960, 540))

        # Touch at pillarbox margin: (50, 540) -> should be rejected (None)
        margin_pt = self.mapper.screen_to_server(50.0, 540.0)
        self.assertIsNone(margin_pt)

    def test_screen_to_server_monitor_one(self):
        self.mapper.set_active_monitor(1)
        self.assertEqual(self.mapper.active_monitor_index, 1)

        # Monitor 1 origin is at x=1920
        # Touch at left edge of rendered monitor: (210, 0) -> server (1920, 0)
        pt = self.mapper.screen_to_server(210.0, 0.0)
        self.assertIsNotNone(pt)
        self.assertEqual(pt, (1920, 0))

        # Touch at center: (1170, 540) -> server (1920 + 960, 540) = (2880, 540)
        center_pt = self.mapper.screen_to_server(1170.0, 540.0)
        self.assertEqual(center_pt, (2880, 540))

    def test_screen_to_server_monitor_two(self):
        self.mapper.set_active_monitor(2)
        # Monitor 2 origin is at x=3840
        pt = self.mapper.screen_to_server(210.0, 0.0)
        self.assertEqual(pt, (3840, 0))

    def test_server_to_screen_mapping(self):
        # On monitor 0: server point (960, 540) maps to screen (1170, 540)
        self.mapper.set_active_monitor(0)
        screen_pt = self.mapper.server_to_screen(960, 540)
        self.assertEqual(screen_pt, (1170.0, 540.0))

        # Server point on monitor 1 (e.g. 2000, 500) returns None while on monitor 0
        offscreen_pt = self.mapper.server_to_screen(2000, 500)
        self.assertIsNone(offscreen_pt)

        # Switch to monitor 1 -> point maps successfully
        self.mapper.set_active_monitor(1)
        on_screen_pt = self.mapper.server_to_screen(2000, 500)
        self.assertIsNotNone(on_screen_pt)

    def test_damage_rect_clipping(self):
        self.mapper.set_active_monitor(1)  # Active monitor is [1920..3840, 0..1080]

        # Damage fully inside monitor 1
        damage_inside = Rect(x=2000, y=100, width=500, height=300)
        clipped = self.mapper.clip_damage_rect(damage_inside)
        self.assertIsNotNone(clipped)
        self.assertEqual(clipped.x, 80)  # 2000 - 1920
        self.assertEqual(clipped.y, 100)
        self.assertEqual(clipped.width, 500)
        self.assertEqual(clipped.height, 300)

        # Damage on monitor 0 only
        damage_mon0 = Rect(x=100, y=100, width=500, height=300)
        self.assertIsNone(self.mapper.clip_damage_rect(damage_mon0))

        # Damage straddling monitor 0 and monitor 1: [1500..2500]
        damage_straddle = Rect(x=1500, y=0, width=1000, height=500)
        clipped_straddle = self.mapper.clip_damage_rect(damage_straddle)
        self.assertIsNotNone(clipped_straddle)
        # Should clip from monitor 1 start (1920) to 2500 -> width 580
        self.assertEqual(clipped_straddle.x, 0)
        self.assertEqual(clipped_straddle.width, 580)


class TestSwipeNavigationController(unittest.TestCase):
    def setUp(self):
        self.layout = LayoutBuilder.create_horizontal_row(count=3, monitor_width=1920, monitor_height=1080)
        self.phone = ViewportDimensions(width=1000, height=500)
        self.mapper = CoordinateMapper(self.layout, self.phone, initial_monitor=0)
        self.controller = SwipeNavigationController(self.mapper)

    def test_swipe_left_switches_to_next_monitor(self):
        # Threshold = 20% of 1000 = 200px
        self.controller.on_touch_down(x=500, y=250)
        self.controller.on_touch_move(x=200, y=250)  # delta = -300px (exceeds 200px threshold)
        switched = self.controller.on_touch_up(x=200, y=250)

        self.assertTrue(switched)
        self.assertEqual(self.mapper.active_monitor_index, 1)

    def test_small_drag_does_not_switch(self):
        self.controller.on_touch_down(x=500, y=250)
        self.controller.on_touch_move(x=450, y=250)  # delta = -50px (below threshold)
        switched = self.controller.on_touch_up(x=450, y=250)

        self.assertFalse(switched)
        self.assertEqual(self.mapper.active_monitor_index, 0)

    def test_swipe_right_switches_to_previous_monitor(self):
        self.mapper.set_active_monitor(2)
        self.controller.on_touch_down(x=200, y=250)
        self.controller.on_touch_move(x=600, y=250)  # delta = +400px (swipe right)
        switched = self.controller.on_touch_up(x=600, y=250)

        self.assertTrue(switched)
        self.assertEqual(self.mapper.active_monitor_index, 1)

    def test_cannot_swipe_past_boundaries(self):
        # On monitor 0, swiping right cannot go below 0
        self.mapper.set_active_monitor(0)
        self.controller.on_touch_down(x=200, y=250)
        switched = self.controller.on_touch_up(x=600, y=250)
        self.assertFalse(switched)
        self.assertEqual(self.mapper.active_monitor_index, 0)

        # On monitor 2, swiping left cannot go above 2
        self.mapper.set_active_monitor(2)
        self.controller.on_touch_down(x=800, y=250)
        switched = self.controller.on_touch_up(x=200, y=250)
        self.assertFalse(switched)
        self.assertEqual(self.mapper.active_monitor_index, 2)


if __name__ == "__main__":
    unittest.main()
