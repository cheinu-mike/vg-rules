# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Install and exercise the extension ZIP; launched by run_blender.py."""

import hashlib
from contextlib import contextmanager
import csv
import io
import json
import os
from pathlib import Path
import runpy
import stat
import subprocess
import sys
import tomllib
from zipfile import ZipFile
from unittest.mock import patch

import bpy


ROOT = Path(__file__).resolve().parents[1]
PROFILE = Path(os.environ["VGR_EXTENSION_TEST_DIR"]).resolve()
assert PROFILE.is_relative_to(Path(os.environ['VGR_TEST_RUN_ROOT']).resolve())
for key in ("BLENDER_USER_RESOURCES", "BLENDER_USER_CONFIG", "BLENDER_USER_SCRIPTS",
            "BLENDER_USER_DATAFILES", "BLENDER_USER_EXTENSIONS"):
    assert Path(os.environ[key]).resolve().is_relative_to(PROFILE), key
assert not bpy.app.online_access
release = tomllib.loads((ROOT / "vg_rules/blender_manifest.toml").read_text(encoding="utf-8"))
ZIP = Path(os.environ['VGR_TEST_ARCHIVE']).resolve()
REPORT = PROFILE.parent / f"{PROFILE.name}_results.json"
report = {"blender": bpy.app.version_string, "zip": str(ZIP), "checks": [],
          "sha256": hashlib.sha256(ZIP.read_bytes()).hexdigest(), "status": "FAIL"}


def snapshot(obj):
    return ([group.name for group in obj.vertex_groups],
            [[(item.group, item.weight) for item in vertex.groups] for vertex in obj.data.vertices])


@contextmanager
def read_only(directory):
    """Enforce read-only access, then restore only permissions changed here."""
    before = {path.relative_to(directory): path.read_bytes()
              for path in directory.rglob("*") if path.is_file()}
    if os.name == "nt":
        identity = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"],
                                  check=True, capture_output=True, text=True)
        sid = next(csv.reader(io.StringIO(identity.stdout)))[1]
        acl_environment = os.environ.copy()
        # Do not pass a PowerShell Core module path to Windows PowerShell.
        for key in tuple(acl_environment):
            if key.upper() == "PSMODULEPATH":
                del acl_environment[key]
        acl_environment["VGR_ACL_TARGET"] = str(directory)
        read_acl = "(Get-Acl -LiteralPath $env:VGR_ACL_TARGET).GetSecurityDescriptorSddlForm([System.Security.AccessControl.AccessControlSections]::Access)"
        original_acl = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", read_acl],
                                      env=acl_environment, check=True, capture_output=True, text=True).stdout.strip()
    else:
        modes = {path: stat.S_IMODE(path.stat().st_mode) for path in (directory, *directory.rglob("*"))}
        for path, mode in modes.items():
            path.chmod(mode & ~0o222)
    probe = directory / ".write-probe"
    try:
        if os.name == "nt":
            # Generic W also denies synchronization needed for reads on Windows.
            subprocess.run(["icacls", str(directory), "/deny",
                            f"*{sid}:(OI)(CI)(WD,AD,WEA,WA,DE,DC)", "/q"],
                           check=True, capture_output=True)
        assert (directory / "__init__.py").read_bytes()
        try:
            with (directory / "__init__.py").open("r+b"):
                pass
        except PermissionError:
            pass
        else:
            raise AssertionError("Installed files must reject write access.")
        try:
            probe.write_bytes(b"must fail")
        except PermissionError:
            pass
        else:
            raise AssertionError("Read-only test needs enforced write denial; do not run as root.")
        yield
        after = {path.relative_to(directory): path.read_bytes()
                 for path in directory.rglob("*") if path.is_file()}
        assert after == before, "Extension runtime changed installed files."
    finally:
        if os.name == "nt":
            acl_environment["VGR_ORIGINAL_DACL"] = original_acl
            restore_acl = "$acl = [System.Security.AccessControl.DirectorySecurity]::new(); $acl.SetSecurityDescriptorSddlForm($env:VGR_ORIGINAL_DACL, [System.Security.AccessControl.AccessControlSections]::Access); Set-Acl -LiteralPath $env:VGR_ACL_TARGET -AclObject $acl"
            subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", restore_acl],
                           env=acl_environment, check=True, capture_output=True)
            restored = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", read_acl],
                                     env=acl_environment, check=True, capture_output=True, text=True).stdout.strip()
            assert restored == original_acl, "Original directory permissions were not restored."
        else:
            for path, mode in modes.items():
                path.chmod(mode)
        probe.unlink(missing_ok=True)


try:
    namespace = os.environ['VGR_TEST_NAMESPACE']
    repository = PROFILE / "extensions" / namespace
    repository.mkdir(parents=True, exist_ok=True)
    assert not (repository / "vg_rules").exists(), "Use a fresh profile."
    repo = bpy.context.preferences.extensions.repos.new(
        name="VG Rules verification", module=namespace, custom_directory=str(repository))
    repo.use_remote_url = False
    assert Path(repo.directory).resolve() == repository
    assert bpy.ops.extensions.package_install_files(
        filepath=str(ZIP), repo=repo.module, enable_on_install=False) == {'FINISHED'}
    module_name = f"bl_ext.{repo.module}.vg_rules"
    with read_only(repository / 'vg_rules'):
        assert bpy.ops.preferences.addon_enable(module=module_name) == {'FINISHED'}
        module = sys.modules[module_name]
        assert Path(module.__file__).resolve().parent == repository / "vg_rules"
        assert module.__package__ == module_name
        with ZipFile(ZIP) as archive:
            manifest = tomllib.loads(archive.read("blender_manifest.toml").decode("utf-8"))
            assert manifest["version"] == release["version"] and manifest["id"] == "vg_rules"
            for name in archive.namelist():
                assert (repository / "vg_rules" / name).read_bytes() == archive.read(name), name
        report["checks"].append("extension install/enable and installed-byte parity")
        module.initialize_pending_scenes()
        assert module.export_rules(bpy.context.scene) == {}
        cube = bpy.context.scene.objects["Cube"]
        cube.vertex_groups.new(name="Keep").add([0], 0.25, 'REPLACE')
        cube.vertex_groups.new(name="Delete").add([1], 0.5, 'REPLACE')
        module.load_rules(bpy.context.scene, {cube.name: {
            "keep_regex": ["^Keep$"], "delete_regex": ["^(Keep|Delete)$"],
            "assign_all_vertices": ["Extension Weight"],
        }})
        before = snapshot(cube)
        assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
        assert snapshot(cube) == before
        assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
        assert cube.vertex_groups.get("Delete") is None
        assert cube.vertex_groups["Keep"].weight(0) == 0.25
        assert all(cube.vertex_groups["Extension Weight"].weight(vertex.index) == 1.0
                   for vertex in cube.data.vertices)
        report["checks"].append("Preview preserves data; regex Keep/Delete and full weights Apply")
        preset = PROFILE / "rules.json"
        expected = module.export_rules(bpy.context.scene)
        assert bpy.ops.vgr.export_rules(filepath=str(preset)) == {'FINISHED'}
        module.load_rules(bpy.context.scene, {})
        assert bpy.ops.vgr.import_rules(filepath=str(preset)) == {'FINISHED'}
        assert module.export_rules(bpy.context.scene) == expected
        report["checks"].append("JSON preset export/import")
        module.load_rules(bpy.context.scene, {})
        with patch('socket.create_connection', side_effect=AssertionError('Offline runtime attempted networking')), \
             patch('urllib.request.urlopen', side_effect=AssertionError('Offline runtime attempted HTTP')):
            runpy.run_path(str(ROOT / 'tests/verify_addon.py'), init_globals={'addon': module})
        report['checks'].append('full integration suite in installed extension namespace')
        assert not hasattr(bpy.types.Scene, 'vgr_settings')
        assert bpy.ops.preferences.addon_disable(module=module_name) == {'FINISHED'}
        assert bpy.ops.preferences.addon_enable(module=module_name) == {'FINISHED'}
        module = sys.modules[module_name]
        with patch('socket.create_connection', side_effect=AssertionError('Offline runtime attempted networking')), \
             patch('urllib.request.urlopen', side_effect=AssertionError('Offline runtime attempted HTTP')):
            runpy.run_path(str(ROOT / 'tests/verify_runtime.py'), init_globals={'addon': module})
        report['checks'].append('offline flag remains false with Python network entry points blocked')
        report['checks'].append('runtime compliance regressions in installed extension namespace')
        assert bpy.ops.preferences.addon_disable(module=module_name) == {'FINISHED'}
        assert not hasattr(bpy.types.Scene, "vgr_settings")
        assert module.initialize_loaded_scenes not in bpy.app.handlers.load_post
        assert not bpy.app.timers.is_registered(module.initialize_pending_scenes)
        report["checks"].append("disable cleans Scene property, handler and timer")
        assert bpy.ops.preferences.addon_enable(module=module_name) == {'FINISHED'}
        assert module.owns_scene_property()
        assert bpy.ops.preferences.addon_disable(module=module_name) == {'FINISHED'}
        report['checks'].append('disable/re-enable/disable preserves installation ownership')
        report["status"] = "PASS"
    report['checks'].append('enable, operations, worker, export and disable with enforced read-only installation')
finally:
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
