"""Probe configuration checks never launch a network client."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class TestPhase0Runner(unittest.TestCase):
    def run_probe(self, *args, **changes):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "launched"
            binary = Path(directory) / "fake-xfreerdp"
            binary.write_text('#!/usr/bin/env bash\nprintf launched > "$MARKER"\n')
            binary.chmod(0o755)
            env = os.environ.copy()
            for name in ("HOST", "USERNAME", "CERT_SHA256", "FREERDP_BIN"):
                env.pop(name, None)
            env.update(FREERDP_BIN=str(binary), MARKER=str(marker), **changes)
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/run_phase0_probe.sh"), *args],
                env=env, text=True, capture_output=True, check=False,
            )
            self.assertFalse(marker.exists(), "configuration must never start a client")
            return result

    def valid(self):
        return {"HOST": "100.64.0.10", "USERNAME": "PLACEHOLDER_USER",
                "CERT_SHA256": "ab" * 32}

    def test_help_is_offline_and_describes_required_inputs(self):
        result = self.run_probe("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for item in ("HOST", "USERNAME", "CERT_SHA256", "--prepare", "UNVERIFIED"):
            self.assertIn(item, result.stdout)

    def test_no_defaults_and_missing_configuration_rejected(self):
        for name in self.valid():
            config = self.valid()
            del config[name]
            result = self.run_probe("--prepare", **config)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn(name, result.stderr)

    def test_pin_requires_exact_sha256_hex_without_cli_option_injection(self):
        for pin in ("", "ab" * 31, "ab" * 33, "zz" * 32, "ab" * 32 + ",ignore"):
            config = self.valid()
            config["CERT_SHA256"] = pin
            result = self.run_probe("--prepare", **config)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("CERT_SHA256", result.stderr)

    def test_prepare_reports_blocker_and_does_not_expose_connection_identity(self):
        result = self.run_probe("--prepare", **self.valid())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ExternalCertificateManagement", result.stdout)
        self.assertIn("UNVERIFIED", result.stdout)
        for value in self.valid().values():
            self.assertNotIn(value, result.stdout + result.stderr)

    def test_live_execution_is_blocked_even_with_complete_configuration(self):
        result = self.run_probe(**self.valid())
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn("strict pin", result.stderr)

    def test_unknown_arguments_are_rejected(self):
        result = self.run_probe("--cert-ignore", **self.valid())
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("unknown argument", result.stderr)
