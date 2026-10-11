"""The checked-in parity oracle must remain exactly reproducible from Python."""
import json
from pathlib import Path
import unittest

from scripts.gen_vectors import generate_vectors


class TestGoldenVectors(unittest.TestCase):
    def test_python_vectors_are_current(self):
        path = Path(__file__).resolve().parent / "vectors/portable-core.json"
        expected = json.loads(path.read_text(encoding="utf-8"))
        # JSON normalises tuples to arrays; compare the complete generated document.
        self.assertEqual(expected, json.loads(json.dumps(generate_vectors())))
