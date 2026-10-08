# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Install and exercise the extension ZIP; launched by run_blender.py."""

import hashlib
import json
import os
from pathlib import Path
import sys
import tomllib
from zipfile import ZipFile

import bpy


ROOT = Path(__file__).resolve().parents[1]
PROFILE = Path(os.environ["VGR_EXTENSION_TEST_DIR"]).resolve()
assert PROFILE.is_relative_to(ROOT / "tests")
for key in ("BLENDER_USER_RESOURCES", "BLENDER_USER_CONFIG", "BLENDER_USER_SCRIPTS",
            "BLENDER_USER_DATAFILES", "BLENDER_USER_EXTENSIONS"):
    assert Path(os.environ[key]).resolve().is_relative_to(PROFILE), key
assert not bpy.app.online_access
release = tomllib.loads((ROOT / "vg_rules/blender_manifest.toml").read_text(encoding="utf-8"))
ZIP = ROOT / "dist/blender_extensions" / f'{release["id"]}-{release["version"]}.zip'
REPORT = PROFILE.parent / f"{PROFILE.name}_results.json"
report = {"blender": bpy.app.version_string, "zip": str(ZIP), "checks": [],
          "sha256": hashlib.sha256(ZIP.read_bytes()).hexdigest(), "status": "FAIL"}


def snapshot(obj):
    return ([group.name for group in obj.vertex_groups],
            [[(item.group, item.weight) for item in vertex.groups] for vertex in obj.data.vertices])


try:
    repository = PROFILE / "extensions" / "vgr_verification"
    repository.mkdir(parents=True, exist_ok=True)
    assert not (repository / "vg_rules").exists(), "Use a fresh profile."
    repo = bpy.context.preferences.extensions.repos.new(
        name="VG Rules verification", module="vgr_verification", custom_directory=str(repository))
    repo.use_remote_url = False
    assert Path(repo.directory).resolve() == repository
    assert bpy.ops.extensions.package_install_files(
        filepath=str(ZIP), repo=repo.module, enable_on_install=True) == {'FINISHED'}
    module_name = f"bl_ext.{repo.module}.vg_rules"
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
    assert bpy.ops.preferences.addon_disable(module=module_name) == {'FINISHED'}
    assert not hasattr(bpy.types.Scene, "vgr_settings")
    assert module.initialize_loaded_scenes not in bpy.app.handlers.load_post
    assert not bpy.app.timers.is_registered(module.initialize_pending_scenes)
    report["checks"].append("disable cleans Scene property, handler and timer")
    report["status"] = "PASS"
finally:
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
