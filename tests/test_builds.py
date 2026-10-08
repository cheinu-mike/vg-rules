# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Packaging integrity and failure checks, using generated temporary inputs."""

import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import build_addon
import build_extension


ROOT = Path(__file__).resolve().parents[1]


class Builds(unittest.TestCase):
    def setUp(self):
        artifacts = ROOT / "tests/.artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="build-", dir=artifacts)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.assertTrue(self.root.is_relative_to(artifacts.resolve()))
        (self.root / "vg_rules").mkdir()
        for name in (*build_addon.FILES, build_extension.MANIFEST):
            shutil.copy2(ROOT / "vg_rules" / name, self.root / "vg_rules" / name)
        self.blender = self.root / "blender.exe"
        self.blender.write_bytes(b"Only used with a mocked subprocess")
        self.legacy = self.root / "dist/vg_rules-0.1.0.zip"
        self.extension = self.root / "dist/blender_extensions/vg_rules-0.1.0.zip"
        self.extension.parent.mkdir(parents=True)
        self.legacy.write_bytes(b"Existing add-on: preserve on failure")
        self.extension.write_bytes(b"Existing extension: preserve on failure")

    def snapshot(self):
        return (self.legacy.read_bytes(), self.extension.read_bytes(),
                frozenset(path.relative_to(self.root) for path in self.root.rglob("*")))

    def build_extension(self):
        return build_extension.build(self.root, blender=self.blender)

    def safe_failure(self, action, error=Exception):
        before = self.snapshot()
        with self.assertRaises(error):
            action()
        self.assertEqual(self.snapshot(), before)

    def test_addon_has_exact_source_and_leaves_extension_untouched(self):
        old_extension = self.extension.read_bytes()
        self.assertEqual(build_addon.build(self.root), self.legacy)
        self.assertEqual(self.extension.read_bytes(), old_extension)
        with ZipFile(self.legacy) as archive:
            self.assertEqual(set(archive.namelist()), {f"vg_rules/{name}" for name in build_addon.FILES})
            self.assertIsNone(archive.testzip())
            for name in build_addon.FILES:
                self.assertEqual(archive.read(f"vg_rules/{name}"), (self.root / "vg_rules" / name).read_bytes())

    def test_extension_validates_offline_and_changes_only_metadata(self):
        old_addon = self.legacy.read_bytes()
        with patch.object(build_extension.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "valid", "")) as run:
            self.assertEqual(self.build_extension(), self.extension)
        self.assertEqual(self.legacy.read_bytes(), old_addon)
        command = run.call_args.args[0]
        self.assertEqual(command[:7], [str(self.blender), "--background", "--factory-startup",
                                     "--offline-mode", "--command", "extension", "validate"])
        stage = Path(command[7])
        self.assertEqual(stage.parent, self.extension.parent)
        self.assertFalse(stage.exists())
        profile = Path(run.call_args.kwargs["env"]["BLENDER_USER_RESOURCES"])
        self.assertTrue(profile.is_relative_to(self.extension.parent))
        self.assertFalse(profile.exists())
        with ZipFile(self.extension) as archive:
            self.assertEqual(set(archive.namelist()), set(build_addon.FILES) | {build_extension.MANIFEST})
            manifest = tomllib.loads(archive.read(build_extension.MANIFEST).decode())
            self.assertEqual(manifest["version"], "0.1.0")
            original = ast.parse((self.root / "vg_rules/__init__.py").read_bytes())
            original.body = [node for node in original.body if not (
                isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and
                target.id == "bl_info" for target in node.targets))]
            self.assertEqual(ast.dump(ast.parse(archive.read("__init__.py"))), ast.dump(original))
            for name in build_addon.FILES[1:]:
                self.assertEqual(archive.read(name), (self.root / "vg_rules" / name).read_bytes())

    def test_missing_source_preserves_both_outputs(self):
        (self.root / "vg_rules/engine.py").unlink()
        self.safe_failure(lambda: build_addon.build(self.root), FileNotFoundError)
        self.safe_failure(self.build_extension, FileNotFoundError)

    def test_missing_manifest_preserves_extension(self):
        (self.root / "vg_rules/blender_manifest.toml").unlink()
        self.safe_failure(self.build_extension, FileNotFoundError)

    def test_mismatched_version_fails_before_validation(self):
        manifest = self.root / "vg_rules/blender_manifest.toml"
        manifest.write_text(manifest.read_text().replace('version = "0.1.0"', 'version = "9.9.9"'))
        with patch.object(build_extension.subprocess, "run") as run:
            self.safe_failure(self.build_extension, ValueError)
        run.assert_not_called()

    def test_missing_blender_preserves_outputs(self):
        self.safe_failure(lambda: build_extension.build(self.root, blender=self.root / "absent.exe"), FileNotFoundError)

    def test_validator_rejection_preserves_outputs_and_reports_diagnostic(self):
        with patch.object(build_extension.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "Invalid tag")):
            with self.assertRaisesRegex(ValueError, "Invalid tag"):
                before = self.snapshot()
                self.build_extension()
            self.assertEqual(self.snapshot(), before)

    def test_validation_timeout_and_launch_failure_preserve_outputs(self):
        for error in (subprocess.TimeoutExpired("blender", 120), OSError("Cannot launch Blender")):
            with self.subTest(error=type(error).__name__), patch.object(build_extension.subprocess, "run", side_effect=error):
                self.safe_failure(self.build_extension)

    def test_changed_staged_zip_is_rejected_after_validation(self):
        def corrupt(command, **kwargs):
            Path(command[-1]).write_bytes(b"Changed staged archive")
            return subprocess.CompletedProcess(command, 0, "", "")
        with patch.object(build_extension.subprocess, "run", side_effect=corrupt):
            self.safe_failure(self.build_extension)

    def test_commit_failure_preserves_previous_builds(self):
        for builder in (lambda: build_addon.build(self.root), self.build_extension):
            with patch.object(build_extension.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")), \
                 patch.object(build_extension.os, "replace", side_effect=PermissionError("Cannot replace output")):
                self.safe_failure(builder, PermissionError)

    def test_future_version_uses_metadata_for_both_filenames(self):
        source = self.root / "vg_rules/__init__.py"
        source.write_text(source.read_text().replace('"version": (0, 1, 0)', '"version": (0, 1, 1)'))
        manifest = self.root / "vg_rules/blender_manifest.toml"
        manifest.write_text(manifest.read_text().replace('version = "0.1.0"', 'version = "0.1.1"'))
        before = (self.legacy.read_bytes(), self.extension.read_bytes())
        self.assertEqual(build_addon.build(self.root), self.root / "dist/vg_rules-0.1.1.zip")
        with patch.object(build_extension.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")):
            self.assertEqual(self.build_extension(), self.root / "dist/blender_extensions/vg_rules-0.1.1.zip")
        self.assertEqual((self.legacy.read_bytes(), self.extension.read_bytes()), before)

    def test_cli_requires_blender(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "build_extension.py")],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--blender", result.stderr)

    @unittest.skipUnless(os.environ.get("VGR_TEST_BLENDER"), "Set VGR_TEST_BLENDER to exercise official validation rejection")
    def test_real_blender_rejects_invalid_manifest_without_replacing_output(self):
        manifest = self.root / "vg_rules/blender_manifest.toml"
        manifest.write_text(manifest.read_text().replace('tags = ["Rigging"]', 'tags = ["NotAValidExtensionTag"]'))
        self.safe_failure(lambda: build_extension.build(self.root, blender=os.environ["VGR_TEST_BLENDER"]), ValueError)


if __name__ == "__main__":
    unittest.main()
