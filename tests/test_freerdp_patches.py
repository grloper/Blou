"""Hermetic application checks against exact upstream Android CMake fixtures."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PATCH = ROOT / "patches/0002-android-cmake-cross-compile-fixes.patch"


class TestFreeRdpPatches(unittest.TestCase):
    def patched_tree(self, directory):
        tree = Path(directory) / "source"
        shutil.copytree(ROOT / "tests/fixtures/freerdp-3.31.1", tree)
        result = subprocess.run(
            ["git", "apply", "--check", str(PATCH)], cwd=tree,
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        subprocess.run(["git", "apply", str(PATCH)], cwd=tree, check=True)
        return tree / "client/Android/cmake"

    def test_patch_applies_without_missing_helper_or_crypto_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = self.patched_tree(directory)
            openssl = (tree / "ExternalOpenSSL.cmake").read_text()
            self.assertNotIn("PATCH_COMMAND", openssl)
            self.assertNotIn("patch_openssl.py", openssl)
            self.assertNotIn("cmake_policy_compat.cmake", PATCH.read_text())
            self.assertEqual(
                [line for line in PATCH.read_text().splitlines() if line.startswith("+++ b/")],
                ["+++ b/client/Android/cmake/ExternalDeps.cmake",
                 "+++ b/client/Android/cmake/ExternalOpenSSL.cmake"],
            )

    def test_policy_default_is_forwarded_without_lowering_existing_minimum(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = self.patched_tree(directory)
            self.assertIn("-DCMAKE_POLICY_DEFAULT_CMP0057:STRING=NEW",
                          (tree / "ExternalDeps.cmake").read_text())
            self.assertNotIn("ExternalCJSON.cmake", PATCH.read_text())

    def test_openssl_commands_quote_paths_and_preserve_all_ndk_variables(self):
        with tempfile.TemporaryDirectory() as directory:
            content = (self.patched_tree(directory) / "ExternalOpenSSL.cmake").read_text()
            self.assertIn('string(REPLACE ";" "|" OSSL_ENV_PATH "$ENV{PATH}")', content)
            self.assertIn('set(OSSL_ENV_PATH "${NDK_TOOLCHAIN_BIN}:$ENV{PATH}")', content)
            self.assertEqual(content.count('"PATH=${OSSL_ENV_PATH}"'), 3)
            for variable in ("ANDROID_NDK", "ANDROID_NDK_ROOT", "ANDROID_NDK_HOME"):
                self.assertEqual(content.count(f'"{variable}=${{NDK_ROOT_SLASH}}"'), 3)
            self.assertNotIn("CC=clang", content)

    def test_checker_rejects_missing_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/check_patches.sh"), str(Path(directory) / "missing")],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("pinned FreeRDP checkout required", result.stderr)

    def test_checker_rejects_other_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", "-q", directory], check=True)
            subprocess.run(
                ["git", "-C", directory, "-c", "user.name=Test", "-c",
                 "user.email=test@example.invalid", "commit", "-qm", "fixture", "--allow-empty"],
                check=True,
            )
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/check_patches.sh"), directory],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("unexpected FreeRDP revision", result.stderr)
