# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Runtime regressions for shared source and the installed extension namespace."""

import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ["VGR_TEST_ARTIFACT_DIR"]).resolve()
assert ARTIFACTS.is_relative_to(Path(os.environ["VGR_TEST_RUN_ROOT"]).resolve())
ARTIFACTS.mkdir(parents=True, exist_ok=True)
if "addon" not in globals():
    sys.path.insert(0, str(ROOT))
    import vg_rules as addon
if not addon.VGR_Settings.is_registered:
    addon.register()


def snapshot(obj):
    return ([(group.name, group.lock_weight) for group in obj.vertex_groups],
            [[(entry.group, entry.weight) for entry in vertex.groups] for vertex in obj.data.vertices],
            [(modifier.name, modifier.use_mirror_vertex_groups) for modifier in obj.modifiers
             if modifier.type == 'MIRROR'])


def mesh(name, scene):
    data = bpy.data.meshes.new(name)
    data.from_pydata([(1, 0, 0), (2, 0, 0), (1, 1, 0)], [], [(0, 1, 2)])
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.vertex_groups.new(name="Cleanup").add([0, 1], 0.25, 'REPLACE')
    obj.modifiers.new("Mirror", 'MIRROR').use_mirror_vertex_groups = False
    return obj


def expect_error(action, message):
    try:
        result = action()
    except (RuntimeError, ValueError, OSError) as error:
        assert message in str(error), (message, error)
    else:
        assert result == {'CANCELLED'}, result


def assert_enabled_registration():
    assert all(cls.is_registered for cls in addon.CLASSES)
    assert bpy.types.Scene.bl_rna.properties["vgr_settings"].fixed_type == addon.VGR_Settings.bl_rna


def assert_clean_registration():
    assert not hasattr(bpy.types.Scene, "vgr_settings")
    assert all(not cls.is_registered for cls in addon.CLASSES)


def foreign_handler(_):
    pass


def foreign_timer():
    return None


bpy.app.handlers.load_post.append(foreign_handler)
bpy.app.timers.register(foreign_timer, first_interval=60.0)
addon.load_rules(bpy.context.scene, {
    "Saved Registration Rule": {"enabled": False, "delete_exact": ["Cleanup"]},
})
saved_settings = addon.snapshot_property_group(bpy.context.scene.vgr_settings)
saved_handlers = tuple(bpy.app.handlers.load_post)
for _ in range(3):
    assert_enabled_registration()
    addon.unregister()
    assert_clean_registration()
    assert tuple(bpy.app.handlers.load_post) == saved_handlers
    assert bpy.app.timers.is_registered(foreign_timer)
    with patch.object(bpy.app.timers, "register", side_effect=AssertionError("Enable must not schedule scene work")), \
         patch.object(addon.presets, "validate_rules", side_effect=AssertionError("Enable must not validate saved rules")), \
         patch.object(addon, "update_rule_target", side_effect=AssertionError("Enable must not rewrite saved targets")):
        addon.register()
    assert_enabled_registration()
    assert tuple(bpy.app.handlers.load_post) == saved_handlers
    assert addon.snapshot_property_group(bpy.context.scene.vgr_settings) == saved_settings
bpy.app.handlers.load_post.remove(foreign_handler)
bpy.app.timers.unregister(foreign_timer)
print("PASS: enable/disable preserves saved rules and unrelated callbacks without handlers, timers, validation or target rewrites")

scene = bpy.context.scene
other = bpy.data.scenes.new("Runtime Other Scene")
local = mesh("Runtime Local", scene)
outside = mesh("Runtime Outside", other)
values = {"delete_exact": ["Cleanup"], "assign_all_vertices": ["Local Weight"]}
addon.load_rules(scene, {local.name: values, outside.name: values})
settings = scene.vgr_settings
ready_before = addon.snapshot_property_group(settings)
local.name = "Renamed Runtime Local"
layout = MagicMock()
with patch.object(bpy.app.timers, "register", side_effect=AssertionError("Drawing must not schedule scene work")), \
     patch.object(addon.presets, "validate_rules", side_effect=AssertionError("Drawing must not validate saved rules")), \
     patch.object(addon, "update_rule_target", side_effect=AssertionError("Drawing must not rewrite saved targets")):
    addon.VGR_PT_rules.draw(SimpleNamespace(layout=layout), bpy.context)
    assert addon.rule_name(settings.rules[0]) == local.name
    assert addon.target_object(settings.rules[0]) == local
assert layout.row.return_value.template_list.called
assert addon.snapshot_property_group(settings) == ready_before
assert tuple(bpy.app.handlers.load_post) == tuple(handler for handler in saved_handlers if handler is not foreign_handler)
assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
assert settings.rules[0].object_name == local.name
addon.load_rules(scene, {local.name: values, outside.name: values})
print("PASS: the sidebar reads saved rules and live names immediately without mutation; Preview refreshes binding metadata on use")
assert settings.rules[0].target == local and settings.rules[1].target is None
assert addon.target_object(settings.rules[1]) is None
assert addon.mesh_poll(settings.rules[0], local)
assert not addon.mesh_poll(settings.rules[0], outside)
addon.load_rules(other, {outside.name: values, local.name: values})
assert other.vgr_settings.rules[0].target == outside and other.vgr_settings.rules[1].target is None
assert addon.target_object(settings.rules[0], other) is None
before = snapshot(outside)
settings.rule_index = 1
for operation in (bpy.ops.vgr.preview, bpy.ops.vgr.apply):
    assert operation(scope='ACTIVE') == {'FINISHED'}
    assert snapshot(outside) == before
    assert "Object was not found in scene" in settings.log[0].message
settings.rules[1].target = outside
outside.name = "Renamed Runtime Outside"
for operation in (bpy.ops.vgr.preview, bpy.ops.vgr.apply):
    assert operation(scope='ACTIVE', **({"allow_shared_data": True} if operation == bpy.ops.vgr.apply else {})) == {'FINISHED'}
    assert snapshot(outside) == before and settings.rules[1].target == outside
    assert "outside executing scene" in settings.log[0].message and scene.name in settings.log[0].message
assert addon.export_rules(scene)[outside.name]["assign_all_vertices"] == ["Local Weight"]
assert bpy.ops.vgr.apply(scope='ALL') == {'FINISHED'}
assert local.vertex_groups.get("Cleanup") is None and local.vertex_groups.get("Local Weight") is not None
assert snapshot(outside) == before
# Binding history survives unlinking and relinking the same object.
scene.collection.objects.unlink(local)
settings.rule_index = 0
assert addon.target_object(settings.rules[0]) is None and settings.rules[0].target == local
before_local = snapshot(local)
assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
assert snapshot(local) == before_local and "outside executing scene" in settings.log[0].message
scene.collection.objects.link(local)
assert addon.target_object(settings.rules[0]) == local
with bpy.context.temp_override(scene=other):
    assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
assert outside.vertex_groups.get("Local Weight") is not None
print("PASS: import, fallback, picker, Preview/Apply and context override resolve only in their scene; outside pointers and relinked identities survive")

single = mesh("Single Object Two Scenes", scene)
other.collection.objects.link(single)
assert len([obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.data == single.data]) == 1
addon.load_rules(scene, {single.name: values})
before = snapshot(single)
assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'} and snapshot(single) == before
warnings = [line.message for line in settings.log if line.kind == 'WARNING']
assert len(warnings) == 1 and all(name in warnings[0] for name in (single.name, scene.name, other.name))
assert bpy.ops.vgr.apply(scope='ALL') == {'CANCELLED'} and snapshot(single) == before
assert bpy.ops.vgr.apply(scope='ALL', allow_shared_data=True) == {'FINISHED'}
assert single.vertex_groups.get("Local Weight") is not None
assert other.objects.get(single.name) == single
# A separate mesh user includes all of its scenes and unlinked users in the warning.
sibling = single.copy()
sibling.name = "Outside Shared User"
other.collection.objects.link(sibling)
unlinked = single.copy()
unlinked.name = "Unlinked Shared User"
assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
message = next(line.message for line in settings.log if line.kind == 'WARNING')
assert all(name in message for name in (single.name, sibling.name, unlinked.name, scene.name, other.name))
assert "no scene (unlinked)" in message
print("PASS: single-object multi-scene edits require confirmation; warnings map all shared users to their scenes")

# Rejected cross-scene shared-mesh batches preserve every user and an earlier
# independent target, including each object's own Mirror modifier settings.
earlier = mesh('Cross-scene Earlier Independent', scene)
cross = mesh('Cross-scene Shared Target', scene)
alias = cross.copy()
alias.name = 'Cross-scene Shared Alias'
other.collection.objects.link(alias)
alias.modifiers['Mirror'].use_mirror_vertex_groups = True
scene.collection.objects.link(alias)
mirror_values = {'delete_exact': ['Cleanup'], 'assign_all_vertices': [
    {'group': 'Cross Pair', 'side': 'L', 'mirror': True}]}
addon.load_rules(scene, {earlier.name: mirror_values, cross.name: mirror_values, alias.name: mirror_values})
cross_before = [snapshot(obj) for obj in (earlier, cross, alias)]
for operation in (bpy.ops.vgr.preview, bpy.ops.vgr.apply):
    assert operation(scope='ALL') == {'CANCELLED'}
    assert [snapshot(obj) for obj in (earlier, cross, alias)] == cross_before
# One rule can Preview, but execution without confirmation cancels the whole batch.
settings.rules[2].enabled = False
assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
assert all(name in next(line.message for line in settings.log if line.kind == 'WARNING')
           for name in (cross.name, alias.name, scene.name, other.name))
assert bpy.ops.vgr.apply(scope='ALL') == {'CANCELLED'}
assert [snapshot(obj) for obj in (earlier, cross, alias)] == cross_before
scene.collection.objects.unlink(cross)
settings.rule_index = 1
assert bpy.ops.vgr.apply(scope='ACTIVE', allow_shared_data=True) == {'FINISHED'}
assert [snapshot(obj) for obj in (earlier, cross, alias)] == cross_before
assert settings.rules[1].target == cross and 'outside executing scene' in settings.log[0].message
print('PASS: cross-scene shared meshes, cancelled confirmation and removed-scene targets preserve groups, weights and per-object modifiers')

addon.load_rules(scene, {local.name: {"assign_all_vertices": ["Export Weight"]}})
destination = ARTIFACTS / "atomic_export.json"
destination.write_bytes(b'{"existing": "preset"}\n')
before = destination.read_bytes()
entries = set(ARTIFACTS.iterdir())
for function in ("fdopen", "fsync", "replace"):
    with patch.object(addon.presets.os, function, side_effect=OSError("Injected export failure")):
        expect_error(lambda: bpy.ops.vgr.export_rules(filepath=str(destination)), "Injected export")
    assert destination.read_bytes() == before and set(ARTIFACTS.iterdir()) == entries
assert bpy.ops.vgr.export_rules(filepath=str(destination)) == {'FINISHED'}
assert json.loads(destination.read_text()) == addon.export_rules(scene)
package = Path(addon.__file__).resolve().parent
for path in (package / "__init__.py", package / "regex_guard.py", package / "COPYING.txt",
             package / "new_preset.json", package / ".." / package.name / "__init__.py"):
    before = path.read_bytes() if path.exists() else None
    with patch.object(addon.presets.tempfile, "mkstemp") as stage:
        expect_error(lambda: bpy.ops.vgr.export_rules(filepath=str(path)), "outside the installed")
        stage.assert_not_called()
    assert (path.read_bytes() if path.exists() else None) == before
print("PASS: atomic export roundtrips JSON; write/replace failures preserve existing bytes and clean staging; installed files and path aliases are blocked before writing")

disabled_repository = ARTIFACTS / "disabled_repository"
disabled_package = disabled_repository / "vg_rules"
disabled_package.mkdir(parents=True)
disabled_file = disabled_package / "__init__.py"
disabled_file.write_bytes(b"Synthetic disabled installation: keep intact")
repo = bpy.context.preferences.extensions.repos.new(name="Disabled VG Rules test", module="vgr_disabled_test",
                                                    custom_directory=str(disabled_repository))
repo.use_remote_url = False
try:
    expect_error(lambda: bpy.ops.vgr.export_rules(filepath=str(disabled_file)), "outside the installed")
    assert disabled_file.read_bytes() == b"Synthetic disabled installation: keep intact"
finally:
    bpy.context.preferences.extensions.repos.remove(repo)
legacy_package = ARTIFACTS / "legacy_addons/vg_rules"
legacy_package.mkdir(parents=True)
legacy_file = legacy_package / "__init__.py"
legacy_file.write_bytes(b"Synthetic legacy installation: keep intact")
with patch.object(bpy.utils, "script_paths", return_value=[str(legacy_package.parent)]):
    expect_error(lambda: bpy.ops.vgr.export_rules(filepath=str(legacy_file)), "outside the installed")
assert legacy_file.read_bytes() == b"Synthetic legacy installation: keep intact"
print("PASS: exports also protect disabled extension repositories and legacy add-on installations")

regex_obj = mesh("Worker Failure Target", scene)
regex_obj.vertex_groups["Cleanup"].lock_weight = True
regex_values = {"delete_regex": ["^Cleanup$"],
                "assign_all_vertices": [{"group": "Worker Pair", "side": "L", "mirror": True}]}
addon.load_rules(scene, {regex_obj.name: regex_values})
guard = addon.engine.regex_guard
bundled = guard._bundled_interpreter("Delete Regex")
assert bundled.is_relative_to((Path(bpy.utils.resource_path('LOCAL')) / "python").resolve())
before = snapshot(regex_obj)
assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
assert snapshot(regex_obj) == before and not any(line.kind == 'WARNING' for line in settings.log)
# The successful decision is cached; a missing or external interpreter must still block it.
external = ARTIFACTS / "python.exe"
external.write_bytes(b"External interpreter fixture: must never launch")
for executable in (str(ARTIFACTS / "missing_python.exe"), str(external), ""):
    with patch.object(guard.sys, "executable", executable), patch.object(guard.subprocess, "run") as worker:
        assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
        assert snapshot(regex_obj) == before and len(settings.log) == 1
        assert "Blender's Python interpreter" in settings.log[0].message
        worker.assert_not_called()
with patch.object(guard, "__file__", str(ARTIFACTS / "missing_worker.py")), \
     patch.object(guard.subprocess, "run") as worker:
    assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
    assert snapshot(regex_obj) == before and "worker is unavailable" in settings.log[0].message
    worker.assert_not_called()
for failure in (OSError("Worker launch failed"), subprocess.TimeoutExpired("python", 1)):
    guard._cached_matches.cache_clear()
    with patch.object(guard.subprocess, "run", side_effect=failure):
        assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
    assert snapshot(regex_obj) == before and len(settings.log) == 1 and settings.log[0].kind == 'WARNING'
for code, output in ((1, ""), (0, "not JSON"), (0, "[1]"), (0, "[]")):
    guard._cached_matches.cache_clear()
    with patch.object(guard.subprocess, "run", return_value=subprocess.CompletedProcess([], code, output, "")):
        assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
    assert snapshot(regex_obj) == before and len(settings.log) == 1
guard._cached_matches.cache_clear()
with patch.object(guard.subprocess, "run", wraps=subprocess.run) as worker:
    assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
    assert worker.call_args.args[0] == [
        str(bundled), *bpy.app.python_args, "-B", "-c", guard._WORKER_BOOTSTRAP,
        str(guard._worker_path("Delete Regex")),
    ]
assert snapshot(regex_obj) == before

# Forward Blender's Python arguments exactly, including an empty tuple.
for python_args in (("-E", "-s"), ()):
    worker_bpy = SimpleNamespace(app=SimpleNamespace(python_args=python_args),
                                utils=bpy.utils)
    with patch.dict(sys.modules, {"bpy": worker_bpy}), \
         patch.object(guard.subprocess, "run",
                      return_value=subprocess.CompletedProcess([], 0, "[true]", "")) as worker:
        assert guard._run_matches((), (("^Cleanup$", 0),), ("Cleanup",),
                                  ((False, False),)) == (True,)
        assert worker.call_args.args[0] == [
            str(bundled), *python_args, "-B", "-c", guard._WORKER_BOOTSTRAP,
            str(guard._worker_path("Delete Regex")),
        ]
valid = mesh("Valid Rule With Failed Worker", scene)
addon.load_rules(scene, {regex_obj.name: regex_values,
                         valid.name: {"assign_all_vertices": ["Other Valid Weight"]}})
with patch.object(guard.sys, "executable", ""):
    assert bpy.ops.vgr.apply(scope='ALL') == {'FINISHED'}
assert snapshot(regex_obj) == before
assert all(valid.vertex_groups["Other Valid Weight"].weight(vertex.index) == 1.0 for vertex in valid.data.vertices)
assert "Applied 1 rule(s)" in settings.status and "1 warning(s)" in settings.status
print("PASS: bundled interpreter works; missing/external interpreter, timeout, failed/malformed worker skip all mutation, including with cached decisions")
for mode in ("literal protected", "no groups"):
    obj = mesh("Unavailable Worker " + mode, scene)
    values = {"delete_regex": ["^Cleanup$"], "assign_all_vertices": ["Must Not Assign"]}
    if mode == "literal protected":
        values["keep_exact"] = ["Cleanup"]
    else:
        obj.vertex_groups.clear()
    addon.load_rules(scene, {obj.name: values})
    before = snapshot(obj)
    with patch.object(guard.sys, "executable", ""):
        assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
    assert snapshot(obj) == before and len(settings.log) == 1
    assert "Blender's Python interpreter" in settings.log[0].message
print("PASS: unavailable workers also block assignment in empty or fully literal-protected regex rules")
print("ALL RUNTIME COMPLIANCE CHECKS PASSED")
