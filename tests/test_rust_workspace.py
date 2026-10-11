"""Keep the portable core separate from the RDP engine as the workspace grows."""

import json
from pathlib import Path
import subprocess
import unittest


class TestRustWorkspace(unittest.TestCase):
    def test_core_has_no_ironrdp_dependency(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["cargo", "metadata", "--offline", "--locked", "--no-deps", "--format-version", "1"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        packages = json.loads(result.stdout)["packages"]
        core = next(package for package in packages if package["name"] == "blou-core")
        self.assertEqual(core["edition"], "2021")
        self.assertEqual(core["publish"], [])
        self.assertFalse(
            any(dependency["name"].startswith("ironrdp") for dependency in core["dependencies"])
        )
