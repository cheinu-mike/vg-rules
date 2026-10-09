# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Build and validate VG Rules separately from the Gumroad add-on ZIP.

Run with Python 3.11 or newer. The shared source keeps bl_info for the legacy
builder; only the extension's packaged __init__.py omits that metadata.
"""

import argparse
import ast
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
from zipfile import ZIP_DEFLATED, ZipFile

from build_addon import FILES, ROOT, cleanup_file, read_metadata, zip_info


MANIFEST = "blender_manifest.toml"
QUICK_START = "QUICK_START.txt"
EXTRA_FILES = (MANIFEST, QUICK_START)


def extension_init(data):
    """Remove the complete metadata assignment without rewriting runtime code."""
    text = data.decode("utf-8")
    tree = ast.parse(text)
    assignment = next(node for node in tree.body
                      if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "bl_info"
                              for target in node.targets))
    lines = text.splitlines(keepends=True)
    del lines[assignment.lineno - 1:assignment.end_lineno]
    result = "".join(lines)
    ast.parse(result)
    return result.encode("utf-8")


def read_manifest(data, metadata):
    """Require shared release metadata to agree before producing an installer."""
    manifest = tomllib.loads(data.decode("utf-8"))
    expected = {
        "schema_version": "1.0.0",
        "id": "vg_rules",
        "version": ".".join(str(part) for part in metadata["version"]),
        "name": metadata["name"],
        "maintainer": metadata["author"],
        "type": "add-on",
        "blender_version_min": ".".join(str(part) for part in metadata["blender"]),
        "license": ["SPDX:GPL-3.0-or-later"],
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"Manifest {key} must match the release metadata: {value!r}")
    tagline = manifest.get("tagline")
    if not isinstance(tagline, str) or not tagline.strip() or len(tagline) > 64:
        raise ValueError("Manifest tagline must be nonempty and at most 64 characters.")
    if not manifest.get("permissions", {}).get("files"):
        raise ValueError("The extension must declare file access for preset import/export.")
    return manifest


def verify_archive(path, expected_files, metadata):
    """Verify exact, unencrypted package contents before replacing the output."""
    with ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(expected_files) or set(names) != set(expected_files):
            raise ValueError("Extension ZIP contains missing, duplicate or unexpected files.")
        if any(entry.orig_filename != entry.filename or entry.flag_bits & 1 for entry in entries):
            raise ValueError("Extension ZIP contains unsafe names or encrypted entries.")
        bad_entry = archive.testzip()
        if bad_entry is not None:
            raise ValueError(f"Extension ZIP CRC check failed: {bad_entry}")
        for name, data in expected_files.items():
            if archive.read(name) != data:
                raise ValueError(f"Extension ZIP differs from validated input: {name}")
        read_manifest(archive.read(MANIFEST), metadata)


def validate_with_blender(blender, archive, directory):
    """Validate offline with a disposable profile, using the official command."""
    with tempfile.TemporaryDirectory(prefix=".validation-", dir=directory) as profile:
        profile = Path(profile)
        environment = os.environ.copy()
        environment["BLENDER_USER_RESOURCES"] = str(profile)
        for key, name in (("BLENDER_USER_CONFIG", "config"),
                          ("BLENDER_USER_SCRIPTS", "scripts"),
                          ("BLENDER_USER_DATAFILES", "datafiles"),
                          ("BLENDER_USER_EXTENSIONS", "extensions")):
            environment[key] = str(profile / name)
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        try:
            result = subprocess.run(
                [str(blender), "--background", "--factory-startup", "--offline-mode",
                 "--command", "extension", "validate", str(archive)],
                env=environment, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120, **options)
        except subprocess.TimeoutExpired as error:
            raise ValueError("Blender extension validation timed out after 120 seconds.") from error
        if result.returncode != 0:
            details = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
            raise ValueError(f"Blender extension validation failed (exit {result.returncode}):\n{details}")


def build(root=ROOT, *, blender):
    """Validate a staged extension ZIP before atomically replacing the output."""
    root = Path(root).resolve()
    blender = Path(blender).expanduser().resolve()
    if not blender.is_file():
        raise FileNotFoundError(f"Blender executable not found: {blender}")
    package = root / "vg_rules"
    payloads = {}
    for filename in (*FILES, *EXTRA_FILES):
        path = package / filename
        data = path.read_bytes()
        if not data:
            raise ValueError(f"Extension input is empty: {path}")
        if filename.endswith(".py"):
            ast.parse(data.decode("utf-8"), filename=str(path))
        payloads[filename] = data
    metadata = read_metadata(payloads["__init__.py"])
    manifest = read_manifest(payloads[MANIFEST], metadata)
    payloads["__init__.py"] = extension_init(payloads["__init__.py"])
    version = ".".join(str(part) for part in metadata["version"])
    payloads[QUICK_START] = payloads[QUICK_START].replace(b"@VERSION@", version.encode("ascii"))
    destination = root / "dist" / "blender_extensions" / f'{manifest["id"]}-{version}.zip'
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, stage_name = tempfile.mkstemp(prefix=f".{destination.stem}.", suffix=".zip",
                                             dir=destination.parent)
    stage = Path(stage_name)
    try:
        os.close(descriptor)
        with ZipFile(stage, "w", compression=ZIP_DEFLATED) as archive:
            for name, data in payloads.items():
                archive.writestr(zip_info(name), data)
        verify_archive(stage, payloads, metadata)
        validate_with_blender(blender, stage, destination.parent)
        verify_archive(stage, payloads, metadata)
        os.replace(stage, destination)
    finally:
        cleanup_file(stage)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", type=Path, required=True,
                        help="Path to Blender 4.2 or newer; official validation is required")
    arguments = parser.parse_args()
    try:
        destination = build(blender=arguments.blender)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Build failed: {error}\n")
    print(f"Built and validated {destination}")
