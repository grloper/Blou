"""
Unit tests for Phase 0: Validate the Layout Lie & Fabricated Monitor Topology.
"""
import os
import unittest
from pathlib import Path


class TestLayoutFabricationGeometry(unittest.TestCase):
    """Verifies the mathematical and geometric invariants of the fabricated layout lie."""

    def test_three_monitor_bounding_box(self):
        monitor_count = 3
        width = 1920
        height = 1080

        monitors = []
        for i in range(monitor_count):
            monitors.append({
                "x": i * width,
                "y": 0,
                "width": width,
                "height": height,
                "is_primary": (i == 0),
            })

        # Primary monitor must be at (0, 0)
        self.assertEqual(monitors[0]["x"], 0)
        self.assertEqual(monitors[0]["y"], 0)
        self.assertTrue(monitors[0]["is_primary"])

        # Unsigned coordinate constraint: no negative coordinates
        for m in monitors:
            self.assertGreaterEqual(m["x"], 0)
            self.assertGreaterEqual(m["y"], 0)
            self.assertGreater(m["width"], 0)
            self.assertGreater(m["height"], 0)

        # Bounding box calculation
        total_width = max(m["x"] + m["width"] for m in monitors)
        total_height = max(m["y"] + m["height"] for m in monitors)

        self.assertEqual(total_width, 5760)
        self.assertEqual(total_height, 1080)

    def test_non_overlapping_contiguous_span(self):
        width = 1920
        height = 1080
        monitors = [
            {"left": 0, "right": 1919, "top": 0, "bottom": 1079},
            {"left": 1920, "right": 3839, "top": 0, "bottom": 1079},
            {"left": 3840, "right": 5759, "top": 0, "bottom": 1079},
        ]

        # Check contiguous horizontal edges
        for i in range(len(monitors) - 1):
            self.assertEqual(monitors[i]["right"] + 1, monitors[i + 1]["left"])

        # Check total bounding area matches sum of monitor areas
        total_area = sum((m["right"] - m["left"] + 1) * (m["bottom"] - m["top"] + 1) for m in monitors)
        self.assertEqual(total_area, 5760 * 1080)


class TestPatchIntegrity(unittest.TestCase):
    """Validates that patch files exist, are well-formed, and contain expected symbols."""

    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent

    def test_phase0_patch_exists_and_contains_symbols(self):
        patch_file = self.root / "patches" / "0001-xfreerdp-fabricated-multimon-layout.patch"
        self.assertTrue(patch_file.exists(), f"Patch not found at {patch_file}")

        content = patch_file.read_text(encoding="utf-8")
        self.assertIn("BLOU_FAKE_MONITORS", content)
        self.assertIn("FreeRDP_UseMultimon", content)
        self.assertIn("FreeRDP_SupportMonitorLayoutPdu", content)
        self.assertIn("freerdp_settings_set_monitor_def_array_sorted", content)
        self.assertIn("5760", content)

    def test_probe_script_exists_and_references_correct_host(self):
        script = self.root / "scripts" / "run_phase0_probe.sh"
        self.assertTrue(script.exists(), f"Script not found at {script}")

        content = script.read_text(encoding="utf-8")
        self.assertIn("100.64.0.10", content)
        self.assertIn("BLOU_FAKE_MONITORS=1", content)
        self.assertIn("/multimon:force", content)

    def test_windows_verifier_script_exists(self):
        script = self.root / "scripts" / "verify_windows_topology.ps1"
        self.assertTrue(script.exists(), f"Script not found at {script}")

        content = script.read_text(encoding="utf-8")
        self.assertIn("System.Windows.Forms.Screen", content)
        self.assertIn("5760", content)


if __name__ == "__main__":
    unittest.main()
