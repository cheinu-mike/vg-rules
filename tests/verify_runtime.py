# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Runtime regressions for shared source and the installed extension namespace."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import bpy


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ["VGR_TEST_ARTIFACT_DIR"]).resolve()
assert ARTIFACTS.is_relative_to(Path(os.environ["VGR_TEST_RUN_ROOT"]).resolve())
ARTIFACTS.mkdir(parents=True, exist_ok=True)
if "addon" not in globals():
    sys.path.insert(0, str(ROOT))
    import vg_rules as addon
if not addon.owns_scene_property():
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


def registration_snapshot():
    return (bpy.types.Scene.bl_rna.properties["vgr_settings"].as_pointer(),
            tuple(addon.registered_class(cls) for cls in addon.CLASSES),
            tuple(bpy.app.handlers.load_post),
            bpy.app.timers.is_registered(addon.initialize_pending_scenes))


before = registration_snapshot()
with patch.object(bpy.utils, "register_class") as register:
    expect_error(addon.register, "conflicts")
    register.assert_not_called()
assert registration_snapshot() == before
spec = importlib.util.spec_from_file_location("vgr_conflict_test", addon.__file__,
                                             submodule_search_locations=[str(Path(addon.__file__).parent)])
conflict = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = conflict
spec.loader.exec_module(conflict)
with patch.object(bpy.utils, "register_class") as register:
    expect_error(conflict.register, "conflicts")
    register.assert_not_called()
conflict.unregister()
assert registration_snapshot() == before
print("PASS: duplicate source/extension installations reject before any resource change; foreign unregister is harmless")

addon.unregister()


def assert_clean_registration():
    assert not hasattr(bpy.types.Scene, "vgr_settings")
    assert all(addon.registered_class(cls) is None for cls in addon.CLASSES)
    assert addon.initialize_loaded_scenes not in bpy.app.handlers.load_post
    assert not bpy.app.timers.is_registered(addon.initialize_pending_scenes)
    assert not addon._registered_classes


assert_clean_registration()
original_register = bpy.utils.register_class
for failed_class in (addon.CLASSES[0], addon.VGR_Settings, addon.CLASSES[-1]):
    def fail_after_registration(cls):
        original_register(cls)
        if cls is failed_class:
            raise RuntimeError("Injected class registration failure")
    with patch.object(bpy.utils, "register_class", side_effect=fail_after_registration):
        expect_error(addon.register, "Injected class")
    assert_clean_registration()
original_timer = bpy.app.timers.register


def fail_after_timer(*args, **kwargs):
    original_timer(*args, **kwargs)
    raise RuntimeError("Injected timer registration failure")


with patch.object(bpy.app.timers, "register", side_effect=fail_after_timer):
    expect_error(addon.register, "Injected timer")
assert_clean_registration()
# Catch class/operator collisions even when a prior installation has no Scene property.
foreign_pattern = type("VGR_Pattern", (bpy.types.PropertyGroup,), {})


class ForeignOperator(bpy.types.Operator):
    bl_idname = "vgr.apply"
    bl_label = "Foreign operator"

    def execute(self, context):
        return {'FINISHED'}


for foreign in (foreign_pattern, ForeignOperator):
    original_register(foreign)
    try:
        with patch.object(bpy.utils, "register_class") as register:
            expect_error(addon.register, "conflicts")
            register.assert_not_called()
        addon.unregister()
        assert foreign.is_registered
    finally:
        bpy.utils.unregister_class(foreign)
    assert_clean_registration()
print("PASS: early/late class and timer failures fully roll back; isolated class/operator conflicts are detected")


def foreign_handler(_):
    pass


def foreign_timer():
    return None


bpy.app.handlers.load_post.append(foreign_handler)
bpy.app.timers.register(foreign_timer, first_interval=60.0)
addon.register()
bpy.types.Scene.vgr_settings = bpy.props.IntProperty(default=7)
addon.unregister()
assert bpy.types.Scene.bl_rna.properties["vgr_settings"].type == 'INT'
assert bpy.context.scene.vgr_settings == 7
assert foreign_handler in bpy.app.handlers.load_post and bpy.app.timers.is_registered(foreign_timer)
del bpy.types.Scene.vgr_settings
bpy.app.handlers.load_post.remove(foreign_handler)
bpy.app.timers.unregister(foreign_timer)
assert_clean_registration()
addon.register()
addon.initialize_pending_scenes()
print("PASS: unregister preserves a replacement Scene property and foreign handlers/timers; re-enable works")

scene = bpy.context.scene
other = bpy.data.scenes.new("Runtime Other Scene")
local = mesh("Runtime Local", scene)
outside = mesh("Runtime Outside", other)
values = {"delete_exact": ["Cleanup"], "assign_all_vertices": ["Local Weight"]}
addon.load_rules(scene, {local.name: values, outside.name: values})
settings = scene.vgr_settings
assert not addon.scene_needs_initialization(scene)
ready_before = addon.snapshot_property_group(settings)
with patch.object(addon, "update_rule_target", side_effect=AssertionError("Ready scenes must not rewrite target properties")):
    addon.initialize_scene(scene)
assert addon.snapshot_property_group(settings) == ready_before
local.name = "Renamed Runtime Local"
assert addon.scene_needs_initialization(scene)
addon.request_scene_initialization()
addon.request_scene_initialization()
assert bpy.app.timers.is_registered(addon.initialize_pending_scenes)
addon.initialize_pending_scenes()
assert not addon.scene_needs_initialization(scene)
assert settings.rules[0].object_name == local.name
# A saved mixed-pattern rule is migrated by the writable initializer.
legacy = settings.rules[0].patterns.add()
legacy.kind, legacy.value = "keep_only_prefixes", "Legacy"
settings.rules[0].pattern_lists_split = False
assert addon.scene_needs_initialization(scene)
addon.initialize_pending_scenes()
assert not addon.scene_needs_initialization(scene)
assert settings.rules[0].keep_patterns[0].value == "Legacy"
addon.load_rules(scene, {local.name: values, outside.name: values})
print("PASS: ready scene initialization does not write properties; deferred initialization refreshes names and migrates saved rules")
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
    assert worker.call_args.args[0][:3] == [str(bundled), "-I", "-B"]
assert snapshot(regex_obj) == before
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
