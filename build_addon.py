# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Build the installable Gumroad add-on ZIP from shared VG Rules source."""

import ast
import os
from pathlib import Path
import sys
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent


def zip_info(filename):
    """Use fixed metadata so CI and local builds identify the same payload."""
    info = ZipInfo(filename, date_time=(2026, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = ZIP_DEFLATED
    return info
FILES = ("__init__.py", "engine.py", "regex_guard.py", "presets.py", "NOTICE.txt", "COPYING.txt")


def read_metadata(data):
    """Read literal add-on metadata without importing Blender or running source."""
    tree = ast.parse(data.decode("utf-8"))
    assignments = [node.value for node in tree.body
                   if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "bl_info"
                           for target in node.targets)]
    if len(assignments) != 1:
        raise ValueError("The add-on must contain exactly one literal bl_info assignment.")
    metadata = ast.literal_eval(assignments[0])
    if not isinstance(metadata, dict):
        raise ValueError("bl_info must be a dictionary.")
    version = metadata.get("version")
    if (not isinstance(version, (tuple, list)) or len(version) != 3
            or any(type(part) is not int or part < 0 for part in version)):
        raise ValueError("bl_info version must contain three nonnegative integers.")
    minimum = metadata.get("blender")
    if (not isinstance(minimum, (tuple, list)) or len(minimum) != 3
            or any(type(part) is not int or part < 0 for part in minimum)):
        raise ValueError("bl_info blender must contain three nonnegative integers.")
    author = metadata.get("author")
    if not isinstance(author, str) or not author.strip():
        raise ValueError("bl_info author must be a nonempty string.")
    return metadata


def verify_archive(path, expected_files, expected_metadata):
    """Reject incomplete, unexpected or changed installer content before commit."""
    names = [f"vg_rules/{filename}" for filename in FILES]
    if set(expected_files) != set(names):
        raise ValueError("Expected source inputs must contain exactly the six add-on files.")
    with ZipFile(path) as archive:
        entries = archive.infolist()
        if any(entry.orig_filename != entry.filename for entry in entries):
            raise ValueError("Installer contains altered or unsafe entry names.")
        actual_names = [entry.filename for entry in entries]
        # Exact names and count also reject duplicates, directories and unsafe paths.
        if len(actual_names) != len(names) or set(actual_names) != set(names):
            raise ValueError("Installer must contain exactly the six add-on files, without duplicate or unexpected paths.")
        if any(entry.flag_bits & 1 for entry in entries):
            raise ValueError("Installer entries must not be encrypted.")
        for entry in entries:
            if entry.file_size != len(expected_files[entry.filename]):
                raise ValueError(f"Installer size does not match its validated input: {entry.filename}")
        bad_entry = archive.testzip()
        if bad_entry is not None:
            raise ValueError(f"Installer CRC check failed: {bad_entry}")
        for name in names:
            if archive.read(name) != expected_files[name]:
                raise ValueError(f"Installer source does not match its validated input: {name}")
        if read_metadata(archive.read("vg_rules/__init__.py")) != expected_metadata:
            raise ValueError("Installer metadata does not match its validated source.")


def cleanup_file(path):
    """A leftover temporary file must not turn a committed build into failure."""
    try:
        path.unlink(missing_ok=True)
    except OSError as error:
        try:
            print(f"Warning: could not remove temporary build file {path}: {error}", file=sys.stderr)
        except OSError:
            pass


def build(root=ROOT):
    """Validate inputs and a staged ZIP, then atomically replace the installer."""
    root = Path(root).resolve()
    package = root / "vg_rules"
    source_bytes = {}
    source_info = {}
    # Complete preflight before creating any output or opening an existing deliverable.
    for filename in FILES:
        path = package / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing add-on source file: {path}")
        data = path.read_bytes()
        if not data:
            raise ValueError(f"Add-on source file is empty: {path}")
        text = data.decode("utf-8")
        if filename.endswith(".py"):
            ast.parse(text, filename=str(path))
        name = f"vg_rules/{filename}"
        source_bytes[name] = data
        source_info[name] = zip_info(name)
    metadata = read_metadata(source_bytes["vg_rules/__init__.py"])
    version = ".".join(str(part) for part in metadata["version"])
    destination = root / "dist" / f"vg_rules-{version}.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, stage_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp",
                                             dir=destination.parent)
    stage = Path(stage_name)
    try:
        os.close(descriptor)
        with ZipFile(stage, "w", compression=ZIP_DEFLATED) as archive:
            for name, data in source_bytes.items():
                archive.writestr(source_info[name], data)
        verify_archive(stage, source_bytes, metadata)
        os.replace(stage, destination)
    finally:
        cleanup_file(stage)
    return destination


if __name__ == "__main__":
    print(f"Built and verified {build()}")
