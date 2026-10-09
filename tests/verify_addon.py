# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Blender integration tests, using a disposable factory-startup scene."""

from pathlib import Path
import json
import re
import sys
import os

import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ["VGR_TEST_ARTIFACT_DIR"]).resolve()
assert ARTIFACTS.is_relative_to(Path(os.environ["VGR_TEST_RUN_ROOT"]).resolve())
ARTIFACTS.mkdir(parents=True, exist_ok=True)
if "addon" not in globals():
    sys.path.insert(0, str(ROOT))
    import vg_rules as addon


def reset():
    if bpy.context.object is not None and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    addon.load_rules(bpy.context.scene, {})


def mesh_object(name, x=2.0, mirror=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(x, 0, 0), (x + 0.1, 0.2, 0), (x - 0.1, 0, 0.2)], [], [(0, 1, 2)])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if mirror:
        modifier = obj.modifiers.new("Mirror", 'MIRROR')
        modifier.use_mirror_merge = False
        modifier.use_mirror_vertex_groups = False
    bpy.context.view_layer.update()
    return obj


def add_group(obj, name, weight=0.25, indices=None):
    group = obj.vertex_groups.new(name=name)
    group.add(indices if indices is not None else [0, 1, 2], weight, 'REPLACE')
    return group


def linked_copy(obj, name, collection=None):
    copy = obj.copy()
    copy.name = name
    (collection or bpy.context.collection).objects.link(copy)
    assert copy.data == obj.data
    return copy


def snapshot(obj):
    return (
        [(group.name, group.lock_weight) for group in obj.vertex_groups],
        [[(membership.group, membership.weight) for membership in vertex.groups] for vertex in obj.data.vertices],
        [(modifier.name, modifier.use_mirror_vertex_groups) for modifier in obj.modifiers if modifier.type == 'MIRROR'],
    )


def assert_full(obj, name):
    for vertex in obj.data.vertices:
        assert abs(obj.vertex_groups[name].weight(vertex.index) - 1.0) < 1e-6


def raw_settings_snapshot(settings):
    """Read editable fields directly; exporting would migrate incomplete legacy rows."""
    rule_fields = ("enabled", "target", "object_name", "target_was_set", "pattern_index", "pattern_lists_split",
                   "keep_pattern_index", "keep_case_sensitive", "delete_pattern_index",
                   "delete_case_sensitive", "assignment_index")
    return (
        tuple(getattr(settings, name) for name in
              ("initialized", "rule_index", "log_index", "status", "show_log")),
        tuple((line.kind, line.message) for line in settings.log),
        tuple((
            tuple(getattr(rule, name) for name in rule_fields),
            tuple((entry.kind, entry.value) for entry in rule.patterns),
            tuple((entry.kind, entry.value) for entry in rule.keep_patterns),
            tuple((entry.kind, entry.value) for entry in rule.delete_patterns),
            tuple((entry.group_name, entry.side, entry.mirror) for entry in rule.assignments),
        ) for rule in settings.rules),
    )


if not addon.owns_scene_property():
    addon.register()
assert hasattr(bpy.types.Scene, "vgr_settings")
assert addon.export_rules(bpy.context.scene) == {}
assert not bpy.context.scene.vgr_settings.log
assert bpy.context.scene.vgr_settings.initialized
assert addon.VGR_PT_rules.is_registered
fresh_scene = bpy.data.scenes.new("Fresh Scene")
for _ in range(2):
    addon.initialize_loaded_scenes(None)
    assert addon.export_rules(fresh_scene) == {}
    assert fresh_scene.vgr_settings.initialized
    assert not fresh_scene.vgr_settings.log
assert bpy.ops.vgr.preview(scope='ALL') == {'CANCELLED'}
assert bpy.ops.vgr.apply(scope='ALL') == {'CANCELLED'}
print("PASS: registration and new scenes start empty; no bundled-rule restore operator")

reset()
obj = mesh_object("Keep Only Test")
for name in ("DEF-tongue", "Shell", "Other Group"):
    add_group(obj, name)
for settings in ({}, {"keep_only_prefixes": ["DEF-tongue"]},
                 {"keep_exact": ["DEF-tongue"]}, {"keep_contains": ["tongue"]},
                 {"keep_suffixes": ["tongue"]}, {"keep_regex": [r"^DEF-.*$"]}):
    addon.load_rules(bpy.context.scene, {obj.name: settings})
    before = snapshot(obj)
    bpy.ops.vgr.preview(scope='ALL')
    assert not any(line.kind == "DELETE" for line in bpy.context.scene.vgr_settings.log)
    bpy.ops.vgr.apply(scope='ALL')
    assert snapshot(obj) == before
print("PASS: no deletion rules or any Keep-only type preserves all groups and weights")

reset()
obj = mesh_object("Keep Overrides Delete")
add_group(obj, "DEF-eye.L")
add_group(obj, "Unmatched")
before = snapshot(obj)
keep_cases = {
    "keep_only_prefixes": ["def-eye"],
    "keep_exact": ["def-EYE.l"],
    "keep_contains": ["EyE"],
    "keep_suffixes": [".l"],
    "keep_regex": [r"^def-eye[.]l$"],
}
delete_cases = {
    "delete_exact": ["DEF-eye.L"],
    "delete_prefixes": ["DEF-"],
    "delete_contains": ["eye"],
    "delete_suffixes": [".L"],
    "delete_regex": [r"eye[.]L$"],
}
for keep_key, keep_values in keep_cases.items():
    for delete_key, delete_values in delete_cases.items():
        assert addon.engine.should_delete_group("DEF-eye.L", {delete_key: delete_values})
        values = {keep_key: keep_values, delete_key: delete_values}
        addon.load_rules(bpy.context.scene, {obj.name: values})
        bpy.ops.vgr.preview(scope='ACTIVE')
        assert not any(line.kind == "DELETE" for line in bpy.context.scene.vgr_settings.log)
        bpy.ops.vgr.apply(scope='ACTIVE')
        assert snapshot(obj) == before
assert addon.engine.should_delete_group("DEF-eye.L.001", {
    "keep_exact": ["DEF-eye.L"], "delete_prefixes": ["DEF-"],
})
assert not addon.engine.should_delete_group("DEF-eye.L.001", {
    "keep_contains": ["eye"], "delete_prefixes": ["DEF-"],
})
print("PASS: all 25 Keep/Delete type combinations, case-insensitive precedence and Exact/Contains boundaries")

for key, values in keep_cases.items():
    rules = {key: values, "delete_regex": [".*"]}
    assert not addon.engine.should_delete_group("DEF-eye.L", rules)
    rules["keep_case_sensitive"] = True
    assert addon.engine.should_delete_group("DEF-eye.L", rules), key
    rules[key] = {"keep_only_prefixes": ["DEF-eye"], "keep_exact": ["DEF-eye.L"],
                  "keep_contains": ["eye"], "keep_suffixes": [".L"],
                  "keep_regex": [r"^DEF-eye[.]L$"]}[key]
    assert not addon.engine.should_delete_group("DEF-eye.L", rules), key
for key in delete_cases:
    values = {"delete_exact": ["def-eye.l"], "delete_prefixes": ["def-"],
              "delete_contains": ["EYE"], "delete_suffixes": [".l"],
              "delete_regex": [r"^def-eye[.]l$"]}[key]
    rules = {key: values, "keep_case_sensitive": True}
    assert addon.engine.should_delete_group("DEF-eye.L", rules), key
    rules["delete_case_sensitive"] = True
    assert not addon.engine.should_delete_group("DEF-eye.L", rules), key
    assert not addon.engine.should_delete_group("DEF-eye.L", {
        key: delete_cases[key], "delete_case_sensitive": True, "keep_exact": ["def-eye.l"],
    }), key
assert not addon.engine.should_delete_group("DEF-eye.L.001", {"delete_suffixes": [".L"]})
assert addon.engine.should_delete_group("DEF-eye.L.001", {"delete_regex": [r"eye[.]L"]})
assert not addon.engine.should_delete_group("DEF-eye.L.001", {"delete_regex": [r"^DEF-eye[.]L$"]})
assert addon.engine.should_delete_group("Eye", {"delete_regex": [r"^\D+$"]})
assert not addon.engine.should_delete_group("123", {"delete_regex": [r"^\D+$"]})
assert addon.engine.should_delete_group("123", {"delete_regex": [r"^\d+$"]})
print("PASS: independent case sensitivity for all ten filters, literal suffix boundaries, regex search/anchors and uppercase regex escapes")

reset()
obj = mesh_object("Suffix and Regex Cleanup")
for name in ("DEF-eye.L", "DEF-eye.R", "bad123", "BAD123", "badX", "Shell"):
    add_group(obj, name)
addon.load_rules(bpy.context.scene, {obj.name: {
    "keep_suffixes": [".L"], "keep_regex": [r"^BAD\d+$"], "keep_case_sensitive": True,
    "delete_suffixes": [".r"], "delete_regex": [r"^bad\d+$"],
}})
before = snapshot(obj)
bpy.ops.vgr.preview(scope='ACTIVE')
assert snapshot(obj) == before
assert len([line for line in bpy.context.scene.vgr_settings.log if line.kind == "DELETE"]) == 2
bpy.ops.vgr.apply(scope='ACTIVE')
assert [group.name for group in obj.vertex_groups] == ["DEF-eye.L", "BAD123", "badX", "Shell"]
print("PASS: suffix/regex cleanup applies only explicit matches and preserves protected groups and unrelated weights")

for section in ("keep", "delete"):
    reset()
    obj = mesh_object("Invalid Regex")
    add_group(obj, "Shell")
    addon.load_rules(bpy.context.scene, {obj.name: {
        "keep_exact": ["Shell"], "delete_exact": ["Shell"], "assign_all_vertices": ["Shell", "New Weight"],
    }})
    rule = addon.active_rule(bpy.context.scene)
    collection = rule.keep_patterns if section == "keep" else rule.delete_patterns
    entry = collection.add()
    entry.kind, entry.value = f"{section}_regex", "["
    before = snapshot(obj)
    for operation in (bpy.ops.vgr.preview, bpy.ops.vgr.apply):
        operation(scope='ACTIVE')
        assert snapshot(obj) == before
        log = bpy.context.scene.vgr_settings.log
        assert len(log) == 1 and log[0].kind == "WARNING"
        assert f"Invalid {section.title()} Regex" in log[0].message
    empty = mesh_object("Empty Group List")
    try:
        addon.engine.make_plan(empty, {f"{section}_regex": ["["], "assign_all_vertices": ["New"]})
    except ValueError as error:
        assert f"Invalid {section.title()} Regex" in str(error)
    else:
        raise AssertionError("Invalid regex must fail even before any groups exist")
    for flag in addon.engine.CASE_KEYS:
        try:
            addon.presets.validate_rules({obj.name: {flag: "false"}})
        except ValueError as error:
            assert "true or false" in str(error)
        else:
            raise AssertionError("Case flags must be boolean")
    addon.load_rules(bpy.context.scene, {obj.name: {"keep_suffixes": ["ell"]}})
    preserved = addon.export_rules(bpy.context.scene)
    try:
        addon.load_rules(bpy.context.scene, {obj.name: {f"{section}_regex": ["[" ]}})
    except ValueError as error:
        assert "Regex" in str(error)
    else:
        raise AssertionError("Invalid regex preset must be rejected")
    assert addon.export_rules(bpy.context.scene) == preserved
print("PASS: malformed Keep/Delete regex is reported before any cleanup or assignment, including protected/empty groups; invalid presets preserve current rules")

regex_compile_cases = (
    ("overflow", "a{999999999999999999999999999999}", OverflowError,
     "Repetition count is too large; reduce its bound."),
    ("nesting", "(" * 1500 + "a" + ")" * 1500, RecursionError,
     "Pattern nesting is too deep; simplify the expression."),
)
for failure_name, expression, compiler_error, reason in regex_compile_cases:
    try:
        re.compile(expression)
    except compiler_error:
        pass
    else:
        raise AssertionError(f"{failure_name}: the real regex compiler must raise {compiler_error.__name__}")
    for section in ("keep", "delete"):
        reset()
        earlier = mesh_object("Valid Before Bad Regex", mirror=True)
        invalid_target = mesh_object("Bad Compiler Regex Target", mirror=True)
        later = mesh_object("Valid After Bad Regex", mirror=True)
        targets = (earlier, invalid_target, later)
        for target in targets:
            add_group(target, "Existing", 0.35, indices=[0, 2]).lock_weight = True
        key = f"{section}_regex"
        invalid_values = {"keep_exact": ["Existing"], "delete_exact": ["Existing"],
                          key: [r"^Valid Before Invalid$", expression],
                          "assign_all_vertices": [{"group": "Skipped Pair", "side": "L", "mirror": True}]}
        empty_mesh = bpy.data.meshes.new("Empty Compiler Regex Mesh")
        empty = bpy.data.objects.new("Empty Compiler Regex Target", empty_mesh)
        bpy.context.collection.objects.link(empty)
        before = [snapshot(target) for target in targets]
        for operation in (
            lambda: addon.engine.GroupFilters(invalid_values, section),
            lambda: addon.engine.should_delete_group("Existing", invalid_values),
            lambda: addon.engine.make_plan(invalid_target, invalid_values),
            lambda: addon.engine.make_plan(empty, {key: [expression], "assign_all_vertices": ["New"]}),
            lambda: addon.presets.validate_rules({invalid_target.name: invalid_values}),
        ):
            try:
                operation()
            except ValueError as error:
                assert type(error) is ValueError, (failure_name, section, type(error))
                assert f"Invalid {section.title()} Regex" in str(error) and reason in str(error)
                assert len(str(error)) < 400
            else:
                raise AssertionError(f"{failure_name} {section}: compiler failure must be a friendly validation error")
            assert [snapshot(target) for target in targets] == before
            assert not empty.vertex_groups
        addon.load_rules(bpy.context.scene, {
            earlier.name: {"delete_exact": ["Existing"], "assign_all_vertices": [
                {"group": "Earlier Pair", "side": "L", "mirror": True},
            ]},
            invalid_target.name: {"keep_exact": ["Existing"], "delete_exact": ["Existing"],
                                  "assign_all_vertices": [{"group": "Skipped Pair", "side": "L", "mirror": True}]},
            later.name: {"delete_exact": ["Existing"], "assign_all_vertices": [
                {"group": "Later Pair", "side": "R", "mirror": True},
            ]},
        })
        settings = bpy.context.scene.vgr_settings
        settings.rule_index = 1
        bad_rule = addon.active_rule(bpy.context.scene)
        patterns = bad_rule.keep_patterns if section == "keep" else bad_rule.delete_patterns
        entry = patterns.add()
        entry.kind, entry.value = key, expression
        for operation, verb in ((bpy.ops.vgr.preview, "Previewed"), (bpy.ops.vgr.apply, "Applied")):
            assert operation(scope='ACTIVE') == {'FINISHED'}
            assert [snapshot(target) for target in targets] == before
            assert len(settings.log) == 1 and settings.log[0].kind == "WARNING"
            assert f"Invalid {section.title()} Regex" in settings.log[0].message
            assert reason in settings.log[0].message
            assert settings.status == f"{verb} 0 rule(s): 0 deletion(s), 0 assignment(s), 1 warning(s)."
        assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
        assert [snapshot(target) for target in targets] == before
        assert settings.status == "Previewed 2 rule(s): 2 deletion(s), 2 assignment(s), 1 warning(s)."
        warnings = [line.message for line in settings.log if line.kind == "WARNING"]
        assert len(warnings) == 1 and invalid_target.name in warnings[0] and reason in warnings[0]
        assert len([line for line in settings.log if line.kind == "DELETE"]) == 2
        assert len([line for line in settings.log if line.kind == "ASSIGN"]) == 2
        assert bpy.ops.vgr.apply(scope='ALL') == {'FINISHED'}
        assert settings.status == "Applied 2 rule(s): 2 deletion(s), 2 assignment(s), 1 warning(s)."
        assert snapshot(invalid_target) == before[1]
        for target, group_name in ((earlier, "Earlier Pair.L"), (later, "Later Pair.R")):
            assert target.vertex_groups.get("Existing") is None
            assert_full(target, group_name)
            assert target.modifiers["Mirror"].use_mirror_vertex_groups
        warnings = [line.message for line in settings.log if line.kind == "WARNING"]
        assert len(warnings) == 1 and invalid_target.name in warnings[0] and reason in warnings[0]
        assert len([line for line in settings.log if line.kind == "DELETE"]) == 2
        assert len([line for line in settings.log if line.kind == "ASSIGN"]) == 2

        # Preserve current invalid UI text and cleared binding history on import rejection.
        cleared = settings.rules.add()
        cleared.target, cleared.enabled = earlier, False
        cleared.target = None
        cleared.pattern_lists_split = True
        assert cleared.target_was_set
        settings.rule_index, settings.log_index, settings.show_log = 1, 1, False
        preserved_raw = raw_settings_snapshot(settings)
        preserved_meshes = [snapshot(target) for target in targets]
        rejected_rules = {
            earlier.name: {"assign_all_vertices": ["Valid Replacement Before Invalid"]},
            invalid_target.name: invalid_values,
            later.name: {"assign_all_vertices": ["Valid Replacement After Invalid"]},
        }
        for operation in (addon.presets.validate_rules, lambda values: addon.load_rules(bpy.context.scene, values)):
            try:
                operation(rejected_rules)
            except ValueError as error:
                assert type(error) is ValueError
                assert f"Invalid {section.title()} Regex" in str(error) and reason in str(error)
                assert len(str(error)) < 400
            else:
                raise AssertionError("Compiler failures must reject presets before clearing current rules")
            assert raw_settings_snapshot(settings) == preserved_raw
            assert [snapshot(target) for target in targets] == preserved_meshes
        for suffix in (".json", ".py"):
            path = ARTIFACTS / ("regex_compile_import_regression" + suffix)
            source = (json.dumps(rejected_rules) if suffix == ".json"
                      else "OBJECT_RULES = " + repr(rejected_rules) + "\nraise RuntimeError('MUST NOT EXECUTE')\n")
            path.write_text(source, encoding="utf-8")
            try:
                try:
                    outcome = bpy.ops.vgr.import_rules(filepath=str(path))
                except RuntimeError as error:
                    assert f"Invalid {section.title()} Regex" in str(error) and reason in str(error)
                    assert ("Pattern nesting" if failure_name == "nesting" else "Repetition count") in str(error)
                    assert "... truncated" not in str(error)
                    assert len(str(error)) < 400
                else:
                    assert outcome == {'CANCELLED'}
                assert raw_settings_snapshot(settings) == preserved_raw
                assert [snapshot(target) for target in targets] == preserved_meshes
            finally:
                path.unlink()
print("PASS: real repetition OverflowError and nesting RecursionError become friendly Keep/Delete validation warnings before cleanup on protected/empty meshes; Active skips without mutation, All executes valid rules before/after with correct totals, and actual JSON/literal-Python import rejection preserves raw rules, binding history, indexes, results, weights and Mirror flags")

safe_regex_cases = (
    (r"^DEF-(?:eye|jaw)(?:[.][LR])?$", "DEF-eye.L", True),
    (r"eye[.]L", "prefix-eye.L.001", True),
    (r"^eye[.]L$", "prefix-eye.L.001", True),
    (r"^[\w-]+[.]L$", "É眼-hand.L", True),
    (r"^\D+$", "Eye", True), (r"^\D+$", "123", True),
    (r"^\d+$", "١٢٣", True),
    (r"^[A-Z]+$", "İıſK", False), (r"^[A-Z]+$", "İıſK", True),
    (r"\beye\b", "eye.L", True), (r"\beye\b", "eyelid", True),
    (r"^eye$", "eye\n", True), (r"^eye\Z", "eye\n", True),
    (r"(?s)^.*$", "a\nb", True), (r"(?m)^eye$", "bad\neye\nbad", True),
    (r"(?i:eye)", "EYE", True),
    (r"(?<=DEF-)eye(?=[.]L$)", "DEF-eye.L", True),
    (r"^(eye)\1[.]L$", "eyeeye.L", True),
    (r"(?>a+)+$", "a" * 62 + "!", True),
    (r"a++$", "a" * 62 + "!", True),
)
for expression, name, case_sensitive in safe_regex_cases:
    expected = re.search(expression, name, 0 if case_sensitive else re.IGNORECASE) is not None
    for section in ("keep", "delete"):
        values = {f"{section}_regex": [expression], f"{section}_case_sensitive": case_sensitive}
        assert addon.engine.GroupFilters(values, section).matches(name) == expected
    assert addon.engine.should_delete_group(name, {
        "delete_regex": [expression], "delete_case_sensitive": case_sensitive,
    }) == expected
    assert addon.engine.should_delete_group(name, {
        "keep_regex": [expression], "keep_case_sensitive": case_sensitive, "delete_exact": [name],
    }) == (not expected)
cache_rules = {"delete_regex": [r"^eye[.]L$"]}
assert addon.engine.should_delete_group("eye.L", cache_rules)
assert not addon.engine.should_delete_group("eye.L", {**cache_rules, "keep_exact": ["eye.L"]})
assert addon.engine.should_delete_group("eye.L", cache_rules)
assert not addon.engine.should_delete_group("eye.L.001", cache_rules)
assert not addon.engine.should_delete_group("eye.L", {
    "keep_regex": cache_rules["delete_regex"], "delete_exact": ["eye.L"],
})
assert addon.engine.should_delete_group("EYE.L", cache_rules)
assert not addon.engine.should_delete_group("EYE.L", {**cache_rules, "delete_case_sensitive": True})
for section in ("keep", "delete"):
    for expressions in (["a" * 4097], ["Safe"] * 65):
        try:
            addon.presets.validate_rules({"Regex Cap": {f"{section}_regex": expressions}})
        except ValueError as error:
            assert f"Invalid {section.title()} Regex" in str(error) and "at most" in str(error).lower()
        else:
            raise AssertionError("Regex expression length/count caps must be enforced")
    addon.presets.validate_rules({"Regex Boundary": {f"{section}_regex": ["a" * 4096]}})
    addon.presets.validate_rules({"Regex Boundary": {f"{section}_regex": ["Safe"] * 64}})
print("PASS: bounded regex matching retains stdlib search semantics for safe groups, lookarounds, backrefs, Unicode/case, scoped flags, anchors, atomic/possessive repeats; cache separates names, roles, literals and flags; regex count/length boundaries validate")

pathological_expression = r"(a+)+$"
for section in ("keep", "delete"):
    reset()
    earlier = mesh_object("Valid Before Timed Regex", mirror=True)
    invalid_target = mesh_object("Timed Regex Target", mirror=True)
    later = mesh_object("Valid After Timed Regex", mirror=True)
    for target in (earlier, later):
        add_group(target, "Cleanup", 0.35, indices=[0, 2]).lock_weight = True
    dangerous_name = "a" * 32 + "!"
    for name in (dangerous_name, "Cleanup"):
        add_group(invalid_target, name, 0.35, indices=[0, 2]).lock_weight = True
    imported_rules = {
        earlier.name: {"delete_exact": ["Cleanup"], "assign_all_vertices": ["Earlier Timed Weight"]},
        invalid_target.name: {f"{section}_regex": [pathological_expression], "delete_exact": ["Cleanup"],
                              "assign_all_vertices": [{"group": "Timed Pair", "side": "L", "mirror": True}]},
        later.name: {"delete_exact": ["Cleanup"], "assign_all_vertices": ["Later Timed Weight"]},
    }
    assert addon.presets.validate_rules(imported_rules) == imported_rules
    addon.load_rules(bpy.context.scene, imported_rules)
    settings = bpy.context.scene.vgr_settings
    settings.rule_index = 1
    targets = (earlier, invalid_target, later)
    before = [snapshot(target) for target in targets]
    for operation, verb in ((bpy.ops.vgr.preview, "Previewed"), (bpy.ops.vgr.apply, "Applied")):
        assert operation(scope='ACTIVE') == {'FINISHED'}
        assert [snapshot(target) for target in targets] == before
        assert settings.status == f"{verb} 0 rule(s): 0 deletion(s), 0 assignment(s), 1 warning(s)."
        assert len(settings.log) == 1 and settings.log[0].kind == "WARNING"
        assert f"{section.title()} Regex" in settings.log[0].message
        assert "1-second time limit" in settings.log[0].message and "simplify" in settings.log[0].message
    assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
    assert [snapshot(target) for target in targets] == before
    assert settings.status == "Previewed 2 rule(s): 2 deletion(s), 2 assignment(s), 1 warning(s)."
    assert bpy.ops.vgr.apply(scope='ALL') == {'FINISHED'}
    assert settings.status == "Applied 2 rule(s): 2 deletion(s), 2 assignment(s), 1 warning(s)."
    assert snapshot(invalid_target) == before[1]
    for target, group_name in ((earlier, "Earlier Timed Weight"), (later, "Later Timed Weight")):
        assert target.vertex_groups.get("Cleanup") is None
        assert_full(target, group_name)
    warnings = [line for line in settings.log if line.kind == "WARNING"]
    assert len(warnings) == 1 and "1-second time limit" in warnings[0].message
    for suffix in (".json", ".py"):
        path = ARTIFACTS / ("timed_regex_valid_import" + suffix)
        source = (json.dumps(imported_rules) if suffix == ".json"
                  else "OBJECT_RULES = " + repr(imported_rules) + "\nraise RuntimeError('MUST NOT EXECUTE')\n")
        path.write_text(source, encoding="utf-8")
        try:
            assert bpy.ops.vgr.import_rules(filepath=str(path)) == {'FINISHED'}
            assert snapshot(invalid_target) == before[1]
            assert addon.export_rules(bpy.context.scene)[invalid_target.name][f"{section}_regex"] == [pathological_expression]
            settings.rule_index = 1
            assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
            assert snapshot(invalid_target) == before[1]
            assert len(settings.log) == 1 and "1-second time limit" in settings.log[0].message
        finally:
            path.unlink()
    # Literal Keep protection still skips regex evaluation on the protected names.
    addon.load_rules(bpy.context.scene, {invalid_target.name: {
        f"{section}_regex": [pathological_expression], "keep_exact": [dangerous_name, "Cleanup"],
        "delete_exact": [dangerous_name, "Cleanup"], "assign_all_vertices": ["Protected Safe Weight"],
    }})
    assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
    assert snapshot(invalid_target) == before[1]
    assert not any(line.kind == "WARNING" for line in settings.log)
    assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
    assert_full(invalid_target, "Protected Safe Weight")
    for name in (dangerous_name, "Cleanup"):
        assert invalid_target.vertex_groups[name].lock_weight
        assert abs(invalid_target.vertex_groups[name].weight(0) - 0.35) < 1e-6
    assert not invalid_target.modifiers["Mirror"].use_mirror_vertex_groups
    assert not any(line.kind == "WARNING" for line in settings.log)
print("PASS: valid pathological Keep/Delete regex imports successfully but runtime timeout skips the affected rule before cleanup, assignment or Mirror changes; Active preserves every target, All continues valid rules with correct totals, and literal Keep protection retains shortcircuit behavior")

reset()
obj = mesh_object("Separate Lists")
addon.load_rules(bpy.context.scene, {obj.name: {}})
rule = addon.active_rule(bpy.context.scene)
assert {item.identifier for item in addon.VGR_KeepPattern.bl_rna.properties["kind"].enum_items} == set(addon.engine.KEEP_KEYS)
assert {item.identifier for item in addon.VGR_DeletePattern.bl_rna.properties["kind"].enum_items} == set(addon.engine.DELETE_KEYS)
bpy.ops.vgr.edit_list(list_name='KEEP', action='ADD')
rule.keep_patterns[0].value = "DEF-"
bpy.ops.vgr.edit_list(list_name='DELETE', action='ADD')
rule.delete_patterns[0].value = "Shell"
bpy.ops.vgr.edit_list(list_name='KEEP', action='ADD')
rule.keep_patterns[1].kind, rule.keep_patterns[1].value = "keep_exact", "Exact Group"
bpy.ops.vgr.edit_list(list_name='DELETE', action='ADD')
rule.delete_patterns[1].kind, rule.delete_patterns[1].value = "delete_contains", "jaw"
delete_before = [(entry.kind, entry.value) for entry in rule.delete_patterns]
bpy.ops.vgr.edit_list(list_name='KEEP', action='UP')
assert rule.keep_patterns[0].value == "Exact Group"
assert [(entry.kind, entry.value) for entry in rule.delete_patterns] == delete_before
bpy.ops.vgr.edit_list(list_name='KEEP', action='REMOVE')
assert len(rule.keep_patterns) == 1 and rule.keep_patterns[0].value == "DEF-"
assert [(entry.kind, entry.value) for entry in rule.delete_patterns] == delete_before
keep_before = [(entry.kind, entry.value) for entry in rule.keep_patterns]
bpy.ops.vgr.edit_list(list_name='DELETE', action='UP')
bpy.ops.vgr.edit_list(list_name='DELETE', action='REMOVE')
assert [(entry.kind, entry.value) for entry in rule.keep_patterns] == keep_before
assert rule.delete_patterns[0].value == "Shell"
print("PASS: independent Keep/Delete collections, menus, selection, add/remove and reorder controls")

reset()
obj = mesh_object("Legacy Saved Rule")
addon.load_rules(bpy.context.scene, {obj.name: {"assign_all_vertices": ["Saved Weight"]}})
rule = addon.active_rule(bpy.context.scene)
rule.enabled = False
rule.pattern_lists_split = False
# Old .blend rules predate binding history; a live pointer must establish it.
rule.target_was_set = False
obj.name = "Renamed Legacy Saved Rule"
legacy_values = (
    ("keep_only_prefixes", "DEF-"), ("delete_exact", "Shell"),
    ("delete_prefixes", "Bad"), ("delete_contains", "Jaw"),
)
for number, (kind, value) in enumerate(legacy_values):
    entry = rule.patterns.add()
    entry.kind, entry.value = kind, value
    assert entry["kind"] == number
rule.pattern_index = 2
for _ in range(2):
    addon.initialize_loaded_scenes(None)
    assert len(rule.patterns) == 0 and rule.pattern_lists_split
    assert [(entry.kind, entry.value) for entry in rule.keep_patterns] == list(legacy_values[:1])
    assert [(entry.kind, entry.value) for entry in rule.delete_patterns] == list(legacy_values[1:])
    assert rule.delete_pattern_index == 1
    assert rule.target == obj and not rule.enabled
    assert rule.target_was_set and rule.object_name == obj.name
    assert rule.assignments[0].group_name == "Saved Weight"
    assert not rule.keep_case_sensitive and not rule.delete_case_sensitive
print("PASS: old enum values and mixed saved rules migrate once without losing targets, disabled flags, assignments or selection; renamed live legacy pointers acquire binding history")

reset()
obj = mesh_object("Rules Test")
for name in ("KEEP-hand", "keep_JAW.L", "REMOVE_EXACT", "BAD_prefix", "DEF-JAW.L", "Shell"):
    add_group(obj, name)
addon.load_rules(bpy.context.scene, {obj.name: {
    "keep_only_prefixes": ["keep"],
    "delete_exact": ["keep-HAND", "remove_exact"],
    "delete_prefixes": ["KEEP", "bad"],
    "delete_contains": ["jaw"],
}})
before = snapshot(obj)
assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
assert snapshot(obj) == before
assert len([line for line in bpy.context.scene.vgr_settings.log if line.kind == "DELETE"]) == 3
assert bpy.ops.vgr.apply(scope='ALL') == {'FINISHED'}
assert [group.name for group in obj.vertex_groups] == ["KEEP-hand", "keep_JAW.L", "Shell"]
assert abs(obj.vertex_groups["KEEP-hand"].weight(0) - 0.25) < 1e-6
assert abs(obj.vertex_groups["keep_JAW.L"].weight(0) - 0.25) < 1e-6
assert abs(obj.vertex_groups["Shell"].weight(0) - 0.25) < 1e-6
print("PASS: explicit exact, prefix and contains deletion; Keep protection overrides all Delete types; unmatched groups preserved")

reset()
obj = mesh_object("Custom Prop", mirror=True)
existing = add_group(obj, "Attachment Group", indices=[0])
existing.lock_weight = True
add_group(obj, "Other", 0.35)
addon.load_rules(bpy.context.scene, {obj.name: {"assign_all_vertices": ["Attachment Group", "Any Group"]}})
for _ in range(2):
    bpy.ops.vgr.apply(scope='ACTIVE')
    assert_full(obj, "Attachment Group")
    assert_full(obj, "Any Group")
    assert abs(obj.vertex_groups["Other"].weight(0) - 0.35) < 1e-6
    assert obj.vertex_groups["Attachment Group"].lock_weight
    assert not obj.modifiers["Mirror"].use_mirror_vertex_groups
assert len(obj.vertex_groups) == 3
print("PASS: arbitrary group names, missing groups, all vertices, locked weights, multiple assignments and repeat")

for side, x in (("L", 2.0), ("R", -2.0)):
    reset()
    obj = mesh_object("Mirrored Part", x=x, mirror=True)
    for name in ("CustomPair.L", "CustomPair.R"):
        add_group(obj, name)
    addon.load_rules(bpy.context.scene, {obj.name: {
        "assign_all_vertices": [{"group": "CustomPair", "side": "AUTO", "mirror": True}],
    }})
    before = snapshot(obj)
    bpy.ops.vgr.preview(scope='ACTIVE')
    assert snapshot(obj) == before
    bpy.ops.vgr.apply(scope='ACTIVE')
    assert_full(obj, f"CustomPair.{side}")
    other = f'CustomPair.{"R" if side == "L" else "L"}'
    other_index = obj.vertex_groups[other].index
    assert all(all(item.group != other_index for item in vertex.groups) for vertex in obj.data.vertices)
    assert obj.modifiers["Mirror"].use_mirror_vertex_groups
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    assert len(evaluated.data.vertices) == 6
    counts = {obj.vertex_groups[f"CustomPair.{side}"].index: 0, other_index: 0}
    for vertex in evaluated.data.vertices:
        assert len(vertex.groups) == 1
        assert abs(vertex.groups[0].weight - 1.0) < 1e-6
        counts[vertex.groups[0].group] += 1
    assert list(counts.values()) == [3, 3]
print("PASS: generic AUTO sides and actual evaluated Mirror vertex weights")

invalid_name_cases = (
    ("ASCII exact", "a" * 64, "EXACT", False),
    ("ASCII Left mirrored", "a" * 62, "L", True),
    ("ASCII Right mirrored", "a" * 62, "R", True),
    ("ASCII Auto mirrored", "a" * 62, "AUTO", True),
    ("ASCII Auto without Mirror weights", "a" * 62, "AUTO", False),
    ("ASCII exact suffix mirrored", "a" * 62 + ".L", "EXACT", True),
    ("ASCII exact suffix", "a" * 62 + ".R", "EXACT", False),
    ("ASCII explicit replacement suffix", "a" * 62 + ".R", "L", True),
    ("UTF8 exact", "é" * 32, "EXACT", False),
    ("UTF8 Left mirrored", "é" * 31, "L", True),
    ("UTF8 Right mirrored", "é" * 31, "R", True),
    ("UTF8 Auto mirrored", "é" * 31, "AUTO", True),
    ("UTF8 exact suffix mirrored", "é" * 31 + ".R", "EXACT", True),
    ("UTF8 four-byte characters", "🙂" * 15 + "ab", "L", True),
)
for label, name, side, mirror_weights in invalid_name_cases:
    reset()
    obj = mesh_object("Invalid Assignment Name", mirror=True)
    second_mirror = obj.modifiers.new("Already Enabled Mirror", 'MIRROR')
    second_mirror.use_mirror_vertex_groups = True
    for existing in ("Existing", "Early Pair.L", "Early Pair.R"):
        add_group(obj, existing, 0.35, indices=[0, 2]).lock_weight = True
    addon.load_rules(bpy.context.scene, {obj.name: {
        "delete_exact": ["Existing"],
        "assign_all_vertices": [
            {"group": "Early Pair", "side": "L", "mirror": True}, "Placeholder",
        ],
    }})
    # Invalid imported names are rejected; exercise the actual editable UI rows.
    entry = addon.active_rule(bpy.context.scene).assignments[1]
    entry.group_name, entry.side, entry.mirror = name, side, mirror_weights
    assert entry.group_name == name, label
    before = snapshot(obj)
    for scope in ('ACTIVE', 'ALL'):
        for operation in (bpy.ops.vgr.preview, bpy.ops.vgr.apply):
            assert operation(scope=scope) == {'FINISHED'}, label
            assert snapshot(obj) == before, label
            log = bpy.context.scene.vgr_settings.log
            assert len(log) == 1 and log[0].kind == "WARNING", label
            assert "UTF-8 bytes" in log[0].message and "Blender allows 63" in log[0].message, label
print("PASS: oversized exact/Left/Right/Auto/suffixed ASCII and UTF8 UI assignments warn once before any cleanup, earlier assignment, weight/lock or Mirror flag changes")

for name in ("e" * 63, "é" * 31 + "x", "🙂" * 15 + "abc"):
    reset()
    obj = mesh_object("Boundary Exact Name", mirror=True)
    add_group(obj, "Existing", 0.35, indices=[0, 2]).lock_weight = True
    addon.load_rules(bpy.context.scene, {obj.name: {"assign_all_vertices": [name]}})
    before = snapshot(obj)
    assert len(name.encode("utf-8")) == 63
    assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
    assert snapshot(obj) == before
    for _ in range(2):
        assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
        assert_full(obj, name)
        assert [group.name for group in obj.vertex_groups] == ["Existing", name]
        assert obj.vertex_groups["Existing"].lock_weight
        assert abs(obj.vertex_groups["Existing"].weight(0) - 0.35) < 1e-6
        assert not obj.modifiers["Mirror"].use_mirror_vertex_groups
print("PASS: exact 63-byte ASCII, two-byte UTF8 and four-byte UTF8 names preserve their spelling and repeat without duplicate suffixes")

boundary_pair_cases = (
    ("p" * 61, "L", "L", 2.0),
    ("p" * 61, "R", "R", -2.0),
    ("p" * 61, "AUTO", "L", 2.0),
    ("p" * 61, "AUTO", "R", -2.0),
    ("p" * 61 + ".L", "EXACT", "L", 2.0),
    ("p" * 61 + ".R", "EXACT", "R", -2.0),
    ("p" * 61 + ".R", "L", "L", 2.0),
    ("é" * 30 + "x", "L", "L", 2.0),
    ("é" * 30 + "x", "AUTO", "R", -2.0),
    ("é" * 30 + "x.R", "EXACT", "R", -2.0),
    ("🙂" * 15 + "x", "R", "R", -2.0),
)
for case_index, (name, side, resolved_side, x) in enumerate(boundary_pair_cases):
    reset()
    obj = mesh_object("Boundary Mirrored Pair", x=x, mirror=True)
    base = name[:-2] if name.endswith((".L", ".R")) else name
    pair = (base + ".L", base + ".R")
    assert all(len(group.encode("utf-8")) == 63 for group in pair)
    add_group(obj, "Existing", 0.35, indices=[0, 2]).lock_weight = True
    if case_index % 2:
        for group_name in pair:
            add_group(obj, group_name, 0.25, indices=[0]).lock_weight = True
    assignment = {"group": name, "mirror": True}
    if side != "EXACT":
        assignment["side"] = side
    addon.load_rules(bpy.context.scene, {obj.name: {"assign_all_vertices": [assignment]}})
    before = snapshot(obj)
    assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
    assert snapshot(obj) == before
    assigned_name = base + "." + resolved_side
    opposite_name = base + (".R" if resolved_side == "L" else ".L")
    for _ in range(2):
        assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
        assert_full(obj, assigned_name)
        assert sorted(group.name for group in obj.vertex_groups) == sorted(("Existing", *pair))
        opposite_index = obj.vertex_groups[opposite_name].index
        assert all(all(item.group != opposite_index for item in vertex.groups) for vertex in obj.data.vertices)
        assert obj.vertex_groups["Existing"].lock_weight
        assert abs(obj.vertex_groups["Existing"].weight(0) - 0.35) < 1e-6
        if case_index % 2:
            assert all(obj.vertex_groups[group].lock_weight for group in pair)
        assert obj.modifiers["Mirror"].use_mirror_vertex_groups
        bpy.context.view_layer.update()
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        assert len(evaluated.data.vertices) == 6
        counts = {obj.vertex_groups[group].index: 0 for group in pair}
        for vertex in evaluated.data.vertices:
            memberships = [item for item in vertex.groups if item.group in counts]
            assert len(memberships) == 1
            assert abs(memberships[0].weight - 1.0) < 1e-6
            counts[memberships[0].group] += 1
        assert list(counts.values()) == [3, 3]
print("PASS: 61-byte ASCII/UTF8 bases, Left/Right/Auto/Exact and supplied suffixes create exact .L/.R pairs, preserve locks, repeat without .001 and produce actual evaluated Mirror weights")

reset()
obj = mesh_object("Preserved Name Import", mirror=True)
addon.load_rules(bpy.context.scene, {
    obj.name: {"keep_exact": ["Existing"], "assign_all_vertices": ["Safe Name"], "enabled": False},
    "Second Saved Rule": {"delete_contains": ["Unused"], "delete_case_sensitive": True},
})
settings = bpy.context.scene.vgr_settings
settings.rule_index = 1
preserved_config = addon.export_rules(bpy.context.scene)
preserved_targets = [rule.target for rule in settings.rules]
preserved_status = settings.status
invalid_imports = []
for _, name, side, mirror_weights in invalid_name_cases:
    entry = {"group": name, "mirror": mirror_weights}
    if side != "EXACT":
        entry["side"] = side
    invalid_imports.append(entry)
invalid_imports.append({"group": "Embedded\0Null"})
for index, entry in enumerate(invalid_imports):
    invalid = {"Valid Rule Before Invalid": {"assign_all_vertices": ["Fine"]},
               obj.name: {"assign_all_vertices": [entry]}}
    try:
        addon.load_rules(bpy.context.scene, invalid)
    except ValueError as error:
        assert "63" in str(error) or "null" in str(error).lower()
    else:
        raise AssertionError("An invalid assignment name must fail before replacing saved rules")
    assert addon.export_rules(bpy.context.scene) == preserved_config
    assert [rule.target for rule in settings.rules] == preserved_targets
    assert settings.rule_index == 1 and settings.status == preserved_status
    for suffix in (".json", ".py"):
        path = ARTIFACTS / ("invalid_name_import" + suffix)
        source = json.dumps(invalid, ensure_ascii=False) if suffix == ".json" else "OBJECT_RULES = " + repr(invalid) + "\n"
        path.write_text(source, encoding="utf-8")
        try:
            try:
                outcome = bpy.ops.vgr.import_rules(filepath=str(path))
            except RuntimeError as error:
                # Blender promotes an operator ERROR report to Python RuntimeError.
                assert "63" in str(error) or "null" in str(error).lower()
            else:
                assert outcome == {'CANCELLED'}
            assert addon.export_rules(bpy.context.scene) == preserved_config
            assert [rule.target for rule in settings.rules] == preserved_targets
            assert settings.rule_index == 1 and settings.status == preserved_status
        finally:
            path.unlink()
try:
    addon.engine.make_plan(obj, {"assign_all_vertices": ["Embedded\0Null"]})
except ValueError as error:
    assert "null" in str(error).lower()
else:
    raise AssertionError("A NUL in a vertex group name cannot be preserved by Blender")
print("PASS: oversized ASCII/UTF8 and embedded-NUL JSON/Python imports fail before replacing current rule values, target pointers, active selection or status")

reset()
obj = mesh_object("Preserved NUL Import", mirror=True)
second = mesh_object("Preserved Unicode 眼🙂", mirror=True)
for target in (obj, second):
    add_group(target, "Original Weight", 0.35, indices=[0, 2]).lock_weight = True
    add_group(target, "Other Weight", 0.6, indices=[1])
addon.load_rules(bpy.context.scene, {
    obj.name: {"keep_exact": ["Original Weight"], "assign_all_vertices": ["Saved Weight"], "enabled": False},
    second.name: {"delete_contains": ["Unused"], "delete_case_sensitive": True},
})
settings = bpy.context.scene.vgr_settings
settings.rule_index, settings.log_index, settings.show_log = 1, 1, False
for kind, message in (("INFO", "Preserve this result"), ("WARNING", "Preserve this selected warning")):
    entry = settings.log.add()
    entry.kind, entry.message = kind, message
preserved_config = addon.export_rules(bpy.context.scene)
preserved_targets = [rule.target for rule in settings.rules]
preserved_state = (settings.initialized, settings.rule_index, settings.status, settings.show_log,
                   settings.log_index, [(line.kind, line.message) for line in settings.log])
preserved_meshes = (snapshot(obj), snapshot(second))


def assert_nul_import_preserves_state(label):
    assert addon.export_rules(bpy.context.scene) == preserved_config, label
    assert [rule.target for rule in settings.rules] == preserved_targets, label
    assert (settings.initialized, settings.rule_index, settings.status, settings.show_log,
            settings.log_index, [(line.kind, line.message) for line in settings.log]) == preserved_state, label
    assert (snapshot(obj), snapshot(second)) == preserved_meshes, label


nul_cases = [("object suffix", obj.name + "\0Different Target", {}),
             ("object prefix", "\0" + obj.name, {}), ("object NUL only", "\0", {})]
nul_cases.extend((key, obj.name, {key: ["Valid Entry Before Invalid", "Original Weight\0Unmatched"]})
                 for key in addon.engine.PATTERN_KEYS)
nul_cases.extend((
    ("string assignment", obj.name, {"assign_all_vertices": ["Valid Assignment", "Original Weight\0Truncated"]}),
    ("dictionary mirrored assignment", obj.name, {"assign_all_vertices": [
        "Valid Assignment", {"group": "Original Weight\0Truncated", "side": "L", "mirror": True},
    ]}),
))
for label, object_name, invalid_values in nul_cases:
    # The first rule is valid, so a late validation failure must reject the whole import.
    invalid = {second.name: {"delete_exact": ["Original Weight"], "assign_all_vertices": ["Replacement Weight"]},
               object_name: invalid_values}
    for operation in (addon.presets.validate_rules, lambda values: addon.load_rules(bpy.context.scene, values)):
        try:
            operation(invalid)
        except ValueError as error:
            assert "null" in str(error).lower(), (label, str(error))
        else:
            raise AssertionError(f"{label}: embedded NUL must fail before Blender string assignment")
        assert_nul_import_preserves_state(label)
    for suffix in (".json", ".py"):
        path = ARTIFACTS / ("nul_import_regression" + suffix)
        source = (json.dumps(invalid, ensure_ascii=False) if suffix == ".json"
                  else "OBJECT_RULES = " + repr(invalid) + "\nraise RuntimeError('MUST NOT EXECUTE')\n")
        path.write_text(source, encoding="utf-8")
        try:
            try:
                outcome = bpy.ops.vgr.import_rules(filepath=str(path))
            except RuntimeError as error:
                # Blender can promote the operator's ERROR report to RuntimeError.
                assert "null" in str(error).lower(), (label, str(error))
            else:
                assert outcome == {'CANCELLED'}, label
            assert_nul_import_preserves_state(label + suffix)
        finally:
            path.unlink()
print("PASS: embedded NUL in object keys, all ten Keep/Delete filter lists, and string/mirrored assignments fails direct validation/load and actual JSON/literal-Python import; late invalid entries preserve rules, pointers, status, results, selection, weights and Mirror flags")

# Non-NUL Unicode and literal backslashes are valid input, including regex syntax.
safe_values = {key: ["é眼.L", r"literal\0"] for key in addon.engine.PATTERN_KEYS}
safe_values.update({"assign_all_vertices": ["Poids é眼🙂"], "keep_case_sensitive": True})
safe_rules = {second.name: safe_values}
assert addon.presets.validate_rules(safe_rules) == safe_rules
addon.load_rules(bpy.context.scene, safe_rules)
safe_export = addon.export_rules(bpy.context.scene)
assert addon.active_rule(bpy.context.scene).target == second
assert (snapshot(obj), snapshot(second)) == preserved_meshes
for suffix in (".json", ".py"):
    path = ARTIFACTS / ("nul_import_valid_unicode" + suffix)
    source = (json.dumps(safe_rules, ensure_ascii=False) if suffix == ".json"
              else "OBJECT_RULES = " + repr(safe_rules) + "\nraise RuntimeError('MUST NOT EXECUTE')\n")
    path.write_text(source, encoding="utf-8")
    try:
        assert bpy.ops.vgr.import_rules(filepath=str(path)) == {'FINISHED'}
        assert addon.export_rules(bpy.context.scene) == safe_export
        assert addon.active_rule(bpy.context.scene).target == second
        assert (snapshot(obj), snapshot(second)) == preserved_meshes
    finally:
        path.unlink()
print("PASS: safe Unicode object/filter/assignment names and escaped literal backslashes still validate, load and roundtrip through JSON and nonexecuting literal-Python imports")

reset()
obj = mesh_object("Preserved Surrogate Import", mirror=True)
second = mesh_object("Unicode Surrogate Pair 🙂", mirror=True)
for target in (obj, second):
    add_group(target, "Original Weight", 0.35, indices=[0, 2]).lock_weight = True
    add_group(target, "Other Weight", 0.6, indices=[1])
addon.load_rules(bpy.context.scene, {obj.name: {}, second.name: {}})
settings = bpy.context.scene.vgr_settings
legacy, incomplete = settings.rules
legacy.enabled, legacy.object_name, legacy.pattern_lists_split = False, "Stale Legacy Object Label", False
legacy.keep_case_sensitive, legacy.delete_case_sensitive = True, True
legacy.pattern_index, legacy.keep_pattern_index, legacy.delete_pattern_index, legacy.assignment_index = 1, 2, 3, 1
for kind, value in (("keep_only_prefixes", "DEF-"), ("delete_exact", "")):
    entry = legacy.patterns.add()
    entry.kind, entry.value = kind, value
entry = legacy.keep_patterns.add()
entry.kind, entry.value = "keep_exact", "Unsplit Existing Keep"
entry = legacy.delete_patterns.add()
entry.kind, entry.value = "delete_regex", "["
assignment = legacy.assignments.add()
assignment.group_name, assignment.side, assignment.mirror = "", "L", True
incomplete.target, incomplete.object_name = None, "Missing Incomplete Target"
incomplete.pattern_lists_split, incomplete.keep_case_sensitive = True, True
incomplete.keep_pattern_index, incomplete.delete_pattern_index, incomplete.assignment_index = 4, 5, 6
entry = incomplete.keep_patterns.add()
entry.kind, entry.value = "keep_contains", ""
assignment = incomplete.assignments.add()
assignment.group_name, assignment.side, assignment.mirror = "", "AUTO", True
# A cleared pointer retains binding history even when its fallback name still exists.
cleared_binding = settings.rules.add()
cleared_binding.target = obj
cleared_binding.target = None
cleared_binding.pattern_lists_split = True
assert cleared_binding.target_was_set and cleared_binding.object_name == obj.name
settings.initialized, settings.rule_index, settings.log_index, settings.show_log = False, 1, 1, False
settings.status = "Preserve incomplete and legacy editing work"
for kind, message in (("INFO", "Saved result before import"), ("WARNING", "Selected saved warning")):
    entry = settings.log.add()
    entry.kind, entry.message = kind, message
preserved_raw = raw_settings_snapshot(settings)
preserved_meshes = (snapshot(obj), snapshot(second))


def assert_surrogate_import_preserves_state(label):
    assert raw_settings_snapshot(settings) == preserved_raw, label
    assert (snapshot(obj), snapshot(second)) == preserved_meshes, label


surrogate_cases = []
for surrogate_name, surrogate in (("high", "\ud800"), ("low", "\udfff")):
    surrogate_cases.append((surrogate_name + " object key", obj.name + surrogate + "Late Invalid", {}))
    surrogate_cases.extend((surrogate_name + " " + key, obj.name,
                            {key: ["Valid Item Before Invalid", "Original" + surrogate + "Weight"]})
                           for key in addon.engine.PATTERN_KEYS)
    surrogate_cases.extend((
        (surrogate_name + " string assignment", obj.name, {"assign_all_vertices": [
            "Valid Early Assignment", "Weight" + surrogate,
        ]}),
        (surrogate_name + " dictionary assignment", obj.name, {"assign_all_vertices": [
            "Valid Early Assignment", {"group": "Pair" + surrogate, "side": "L", "mirror": True},
        ]}),
        (surrogate_name + " unknown setting key", obj.name, {"unsupported" + surrogate: []}),
        (surrogate_name + " unknown assignment key", obj.name, {"assign_all_vertices": [
            "Valid Early Assignment", {"group": "Pair", "unsupported" + surrogate: True},
        ]}),
        (surrogate_name + " assignment side", obj.name, {"assign_all_vertices": [
            "Valid Early Assignment", {"group": "Pair", "side": surrogate, "mirror": True},
        ]}),
    ))
for label, object_name, invalid_values in surrogate_cases:
    invalid = {second.name: {"assign_all_vertices": ["Valid Earlier Rule"]}, object_name: invalid_values}
    for operation in (addon.presets.validate_rules, lambda values: addon.load_rules(bpy.context.scene, values)):
        try:
            operation(invalid)
        except ValueError as error:
            assert type(error) is ValueError, (label, type(error))
            assert any(word in str(error).lower() for word in ("unicode", "utf-8", "surrogate")), label
        else:
            raise AssertionError(label + ": a lone surrogate must fail before replacement")
        assert_surrogate_import_preserves_state(label)
    for suffix in (".json", ".py"):
        path = ARTIFACTS / ("surrogate_import_regression" + suffix)
        # Escaped JSON and literal Python reproduce characters which cannot be UTF-8 encoded directly.
        source = (json.dumps(invalid, ensure_ascii=True) if suffix == ".json"
                  else "OBJECT_RULES = " + repr(invalid) + "\nraise RuntimeError('MUST NOT EXECUTE')\n")
        path.write_text(source, encoding="utf-8")
        try:
            try:
                outcome = bpy.ops.vgr.import_rules(filepath=str(path))
            except RuntimeError as error:
                assert any(word in str(error).lower() for word in ("unicode", "utf-8", "surrogate")), label
            else:
                assert outcome == {'CANCELLED'}, label
            assert_surrogate_import_preserves_state(label + suffix)
        finally:
            path.unlink()
print("PASS: lone high/low surrogates in object keys, all ten filters, string/dictionary assignments, unknown keys and side values reject direct load and actual JSON/literal-Python imports before replacement with safe diagnostics, preserving raw incomplete/legacy fields, pointers, indexes, results, groups, weights, locks and Mirror flags")

# A failure after replacement starts must also restore unfinished editing work.
replacement = {
    second.name: {"assign_all_vertices": ["Replacement First Weight"]},
    obj.name: {"delete_exact": ["Original Weight"], "assign_all_vertices": ["Replacement Second Weight"]},
}
original_populate = addon.populate_rules
for suffix in (None, ".json", ".py"):
    populated_rows = []

    def fail_partial_population(collection, incoming, scene):
        first_name = next(iter(incoming))
        original_populate(collection, {first_name: incoming[first_name]}, scene)
        populated_rows.extend(rule.object_name for rule in collection)
        settings.log.clear()
        settings.status = "Partially loaded"
        settings.initialized, settings.rule_index, settings.log_index, settings.show_log = True, 0, 0, True
        raise TypeError("Injected partial population failure")

    addon.populate_rules = fail_partial_population
    path = None
    try:
        if suffix is None:
            try:
                addon.load_rules(bpy.context.scene, replacement)
            except ValueError as error:
                assert type(error) is ValueError
                assert "previous configuration restored" in str(error)
                assert "Injected partial population failure" in str(error)
            else:
                raise AssertionError("A partial population failure must reject the replacement")
        else:
            path = ARTIFACTS / ("partial_load_failure_regression" + suffix)
            source = (json.dumps(replacement, ensure_ascii=True) if suffix == ".json"
                      else "OBJECT_RULES = " + repr(replacement) + "\nraise RuntimeError('MUST NOT EXECUTE')\n")
            path.write_text(source, encoding="utf-8")
            try:
                outcome = bpy.ops.vgr.import_rules(filepath=str(path))
            except RuntimeError as error:
                assert "previous configuration restored" in str(error)
                assert "Injected partial population failure" in str(error)
            else:
                assert outcome == {'CANCELLED'}
        assert populated_rows == [second.name], (suffix, populated_rows)
        assert_surrogate_import_preserves_state("injected population failure " + str(suffix))
    finally:
        addon.populate_rules = original_populate
        if path is not None:
            path.unlink()
print("PASS: injected TypeError after one new rule is populated rejects direct load and JSON/literal-Python imports; transaction restores raw nonexportable incomplete/legacy rules, pointers, all indexes/flags/status/results, groups, weights and Mirror flags")

safe_values = {key: ["Weight 🙂"] for key in addon.engine.PATTERN_KEYS}
safe_values["assign_all_vertices"] = ["Weight 🙂", {"group": "Pair 🙂", "side": "L", "mirror": True}]
safe_rules = {second.name: safe_values}
assert addon.presets.validate_rules(safe_rules) == safe_rules
addon.load_rules(bpy.context.scene, safe_rules)
safe_export = addon.export_rules(bpy.context.scene)
assert addon.active_rule(bpy.context.scene).target == second
assert (snapshot(obj), snapshot(second)) == preserved_meshes
for suffix in (".json", ".py"):
    path = ARTIFACTS / ("surrogate_import_valid_emoji" + suffix)
    source = (json.dumps(safe_rules, ensure_ascii=True) if suffix == ".json"
              else "OBJECT_RULES = " + repr(safe_rules) + "\nraise RuntimeError('MUST NOT EXECUTE')\n")
    if suffix == ".json":
        assert r"\ud83d\ude42" in source
    path.write_text(source, encoding="utf-8")
    try:
        assert bpy.ops.vgr.import_rules(filepath=str(path)) == {'FINISHED'}
        assert addon.export_rules(bpy.context.scene) == safe_export
        assert addon.active_rule(bpy.context.scene).target == second
        assert (snapshot(obj), snapshot(second)) == preserved_meshes
    finally:
        path.unlink()
print("PASS: valid non-BMP emoji, including JSON escaped surrogate pairs, remains intact in object keys, all ten filters and string/mirrored assignments through direct load and both import formats")

reset()
reference = bpy.data.objects.new("MirrorReference", None)
bpy.context.collection.objects.link(reference)
reference.location.x = 1
obj = mesh_object("Offset Part", x=-3, mirror=True)
obj.location.x = 5
obj.modifiers["Mirror"].mirror_object = reference
bpy.context.view_layer.update()
assert addon.engine.detect_group_side(obj, "Anything") == "L"
print("PASS: external Mirror reference and translated mesh")

reset()
rig = bpy.data.objects.new("TestRig", bpy.data.armatures.new("TestRig"))
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name, x in (("DEF-hand.L", -2.0), ("DEF-hand.R", 2.0)):
    bone = rig.data.edit_bones.new(name)
    bone.head, bone.tail = (x, 0, 0), (x, 0, 1)
bpy.ops.object.mode_set(mode='OBJECT')
rig.matrix_world = Matrix.Translation((3, 4, 5)) @ Matrix.Rotation(1.2, 4, 'Z')
obj = mesh_object("Glove", mirror=True)
obj.matrix_world = rig.matrix_world.copy()
obj.modifiers.new("Armature", 'ARMATURE').object = rig
bpy.context.view_layer.update()
assert addon.engine.detect_group_side(obj, "DEF-hand") == "R"
print("PASS: arbitrary matching bone names on a transformed rig")

reset()
obj = mesh_object("Ambiguous", x=0, mirror=True)
add_group(obj, "Shell")
addon.load_rules(bpy.context.scene, {obj.name: {
    "delete_exact": ["Shell"],
    "assign_all_vertices": [{"group": "Pair", "side": "AUTO", "mirror": True}],
}})
before = snapshot(obj)
bpy.ops.vgr.apply(scope='ALL')
assert snapshot(obj) == before
assert "ambiguous" in bpy.context.scene.vgr_settings.log[0].message
rule = addon.active_rule(bpy.context.scene)
rule.assignments[0].side = "R"
bpy.ops.vgr.apply(scope='ALL')
assert_full(obj, "Pair.R")
assert obj.vertex_groups.get("Shell") is None
print("PASS: invalid assignment is reported before cleanup; explicit side override works")

reset()
obj = mesh_object("Edit Target")
add_group(obj, "Shell")
addon.load_rules(bpy.context.scene, {obj.name: {"delete_exact": ["Shell"]}})
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.vgr.apply(scope='ALL')
assert obj.vertex_groups.get("Shell") is not None
assert "Object Mode" in bpy.context.scene.vgr_settings.log[0].message
bpy.ops.object.mode_set(mode='OBJECT')
print("PASS: Edit Mode guard")

reset()
obj = mesh_object("Disabled")
add_group(obj, "Shell")
addon.load_rules(bpy.context.scene, {obj.name: {"delete_exact": ["Shell"]}, "Missing": {}})
bpy.context.scene.vgr_settings.rules[0].enabled = False
bpy.ops.vgr.apply(scope='ALL')
assert obj.vertex_groups.get("Shell") is not None
assert "Object was not found" in bpy.context.scene.vgr_settings.log[0].message
bpy.context.scene.vgr_settings.rule_index = 0
bpy.ops.vgr.apply(scope='ACTIVE')
assert obj.vertex_groups.get("Shell") is None
print("PASS: disabled rules excluded from All, active rule executes explicitly, missing targets logged")

for rename_before_delete in (False, True):
    reset()
    original = mesh_object("Original Bound Target A", mirror=True)
    replacement = mesh_object("Replacement Bound Target B", mirror=True)
    for target in (original, replacement):
        add_group(target, "Existing", 0.35, indices=[0, 2]).lock_weight = True
    addon.load_rules(bpy.context.scene, {original.name: {
        "delete_exact": ["Existing"],
        "assign_all_vertices": ["Retarget Weight", {"group": "Retarget Pair", "side": "L", "mirror": True}],
    }})
    settings = bpy.context.scene.vgr_settings
    rule = addon.active_rule(bpy.context.scene)
    assert rule.target == original and rule.target_was_set
    rule.target = replacement
    assert rule.object_name == replacement.name and rule.target_was_set
    original_before, replacement_before = snapshot(original), snapshot(replacement)
    if rename_before_delete:
        replacement.name = "Renamed Replacement Target B"
        assert addon.target_object(rule) == replacement
        assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
        assert rule.object_name == replacement.name and rule.target_was_set
        assert snapshot(original) == original_before and snapshot(replacement) == replacement_before
    last_bound_name = rule.object_name
    bpy.data.objects.remove(replacement, do_unlink=True)
    assert rule.target is None and rule.target_was_set
    assert addon.target_object(rule) is None
    for scope in ('ACTIVE', 'ALL'):
        for operation in (bpy.ops.vgr.preview, bpy.ops.vgr.apply):
            assert operation(scope=scope) == {'FINISHED'}
            assert snapshot(original) == original_before
            assert rule.target is None and rule.target_was_set and rule.object_name == last_bound_name
            assert len(settings.log) == 1 and settings.log[0].kind == "WARNING"
            assert "Object was not found" in settings.log[0].message
            assert last_bound_name in settings.log[0].message
    recreated = mesh_object(last_bound_name, mirror=True)
    add_group(recreated, "Existing", 0.6, indices=[1])
    recreated_before = snapshot(recreated)
    assert addon.target_object(rule) is None
    assert bpy.ops.vgr.apply(scope='ALL') == {'FINISHED'}
    assert snapshot(original) == original_before and snapshot(recreated) == recreated_before
    assert "Object was not found" in settings.log[0].message
    rule.target = recreated
    assert rule.target_was_set and rule.object_name == recreated.name
    assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
    assert snapshot(original) == original_before
    assert recreated.vertex_groups.get("Existing") is None
    assert_full(recreated, "Retarget Weight")
    assert_full(recreated, "Retarget Pair.L")
    assert recreated.modifiers["Mirror"].use_mirror_vertex_groups
print("PASS: retarget A to B then delete B, including a renamed B, warns in Active/All without touching A; a recreated same-name B is ignored until explicitly reselected")

reset()
original = mesh_object("Explicitly Cleared Target", mirror=True)
add_group(original, "Existing", 0.35, indices=[0, 2]).lock_weight = True
addon.load_rules(bpy.context.scene, {original.name: {"assign_all_vertices": ["Cleared Weight"]}})
settings = bpy.context.scene.vgr_settings
rule = addon.active_rule(bpy.context.scene)
before = snapshot(original)
rule.target = None
assert rule.target_was_set and rule.object_name == original.name
assert addon.target_object(rule) is None
for operation in (bpy.ops.vgr.preview, bpy.ops.vgr.apply):
    assert operation(scope='ACTIVE') == {'FINISHED'}
    assert snapshot(original) == before
    assert len(settings.log) == 1 and "Object was not found" in settings.log[0].message
rule.object_name = original.name
assert not rule.target_was_set and rule.target is None
assert addon.target_object(rule) == original
assert rule.target is None and not rule.target_was_set  # Read-only lookup does not bind.
assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
assert rule.target == original and rule.target_was_set and snapshot(original) == before
print("PASS: clearing a bound pointer does not silently rebind its stored name; explicitly editing the fallback name opts back into resolution, and Preview binds without changing mesh data")

reset()
lazy_name = "Unresolved Imported Target"
addon.load_rules(bpy.context.scene, {lazy_name: {"assign_all_vertices": ["Lazy Weight"]}})
settings = bpy.context.scene.vgr_settings
rule = addon.active_rule(bpy.context.scene)
assert rule.target is None and not rule.target_was_set and addon.target_object(rule) is None
late_target = mesh_object(lazy_name)
assert addon.target_object(rule) == late_target
assert rule.target is None and not rule.target_was_set
assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
assert rule.target == late_target and rule.target_was_set and not late_target.vertex_groups
assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
assert_full(late_target, "Lazy Weight")
bpy.data.objects.remove(late_target, do_unlink=True)
same_name_target = mesh_object(lazy_name)
assert addon.target_object(rule) is None
assert bpy.ops.vgr.apply(scope='ALL') == {'FINISHED'}
assert not same_name_target.vertex_groups
assert len(settings.log) == 1 and "Object was not found" in settings.log[0].message
print("PASS: an unresolved imported name resolves when a mesh is created later, binds on Preview, and requires reselection if that bound object is subsequently deleted")

reset()
original = mesh_object("Persisted Cleared Target", mirror=True)
live = mesh_object("Persisted Live Target", mirror=True)
for target in (original, live):
    add_group(target, "Existing", 0.35, indices=[0, 2]).lock_weight = True
future_name = "Persisted Unresolved Target"
addon.load_rules(bpy.context.scene, {
    original.name: {"assign_all_vertices": ["Must Stay Unassigned"]},
    future_name: {"assign_all_vertices": ["Future Weight"]},
    live.name: {"assign_all_vertices": ["Live Weight"]},
})
settings = bpy.context.scene.vgr_settings
settings.rules[0].target = None
live.name = "Renamed Persisted Live Target"
assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
assert settings.rules[0].target_was_set and settings.rules[0].target is None
assert not settings.rules[1].target_was_set and settings.rules[1].target is None
assert settings.rules[2].target == live and settings.rules[2].object_name == live.name
original_name, live_name = original.name, live.name
original_before, live_before = snapshot(original), snapshot(live)
binding_states = [(rule.object_name, rule.target_was_set, rule.target.name if rule.target else None)
                  for rule in settings.rules]
saved_targets = ARTIFACTS / "target_binding_persistence.blend"
assert bpy.ops.wm.save_as_mainfile(filepath=str(saved_targets), check_existing=False) == {'FINISHED'}
assert bpy.ops.wm.open_mainfile(filepath=str(saved_targets)) == {'FINISHED'}
settings = bpy.context.scene.vgr_settings
original, live = bpy.data.objects[original_name], bpy.data.objects[live_name]
assert [(rule.object_name, rule.target_was_set, rule.target.name if rule.target else None)
        for rule in settings.rules] == binding_states
assert snapshot(original) == original_before and snapshot(live) == live_before
future = mesh_object(future_name)
assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
assert settings.rules[0].target is None and settings.rules[0].target_was_set
assert settings.rules[1].target == future and settings.rules[1].target_was_set
assert settings.rules[2].target == live and settings.rules[2].target_was_set
assert len([line for line in settings.log if line.kind == "WARNING"]) == 1
assert bpy.ops.vgr.apply(scope='ALL') == {'FINISHED'}
assert snapshot(original) == original_before
assert_full(future, "Future Weight")
assert_full(live, "Live Weight")
print("PASS: bound-pointer history, explicit clears, unresolved import names and renamed live pointers persist through .blend reload; missing bound targets remain blocked while newly resolved and live targets run")

reset()
earlier = mesh_object("Earlier Distinct Target", mirror=True)
duplicate = mesh_object("Duplicate Target", mirror=True)
for target in (earlier, duplicate):
    add_group(target, "Existing", 0.35, indices=[0, 2]).lock_weight = True
addon.load_rules(bpy.context.scene, {
    earlier.name: {
        "delete_exact": ["Existing"],
        "assign_all_vertices": [{"group": "Earlier Pair", "side": "L", "mirror": True}],
    },
    duplicate.name: {
        "assign_all_vertices": ["New Group", {"group": "Duplicate Pair", "side": "L", "mirror": True}],
    },
    "Duplicate Rule": {"delete_exact": ["New Group"]},
})
settings = bpy.context.scene.vgr_settings
settings.rules[2].target = duplicate


def assert_duplicate_batch_cancelled(objects, duplicate_names):
    before = [snapshot(target) for target in objects]
    for operation in (bpy.ops.vgr.preview, bpy.ops.vgr.apply):
        settings.show_log = False
        settings.log_index = 5
        stale = settings.log.add()
        stale.kind, stale.message = "ASSIGN", "Stale result"
        assert operation(scope='ALL') == {'CANCELLED'}
        assert [snapshot(target) for target in objects] == before
        assert settings.show_log and settings.log_index == 0
        assert "No rules ran" in settings.status
        assert len(settings.log) == len(duplicate_names)
        assert all(line.kind == "WARNING" for line in settings.log)
        for name in duplicate_names:
            messages = [line.message for line in settings.log if line.message.startswith(f"{name}:")]
            assert len(messages) == 1
            assert "enabled rules" in messages[0] and "Combine" in messages[0]
            assert "disable" in messages[0]


assert_duplicate_batch_cancelled((earlier, duplicate), (duplicate.name,))
print("PASS: duplicate assign/delete targets cancel Preview All and Apply All before any groups, weights, locks or Mirror settings change, including an earlier distinct target")

old_name = duplicate.name
duplicate.name = "Renamed Duplicate Target"
assert settings.rules[1].object_name == old_name
settings.rules[2].target = None
settings.rules[2].object_name = duplicate.name
assert addon.target_object(settings.rules[1]) == addon.target_object(settings.rules[2]) == duplicate
assert_duplicate_batch_cancelled((earlier, duplicate), (duplicate.name,))
third = settings.rules.add()
third.target = duplicate
third.object_name = "Another stale target label"
assert_duplicate_batch_cancelled((earlier, duplicate), (duplicate.name,))
second_duplicate = mesh_object("Second Duplicate Target", mirror=True)
add_group(second_duplicate, "Existing", 0.6)
for _ in range(2):
    rule = settings.rules.add()
    rule.target = second_duplicate
assert_duplicate_batch_cancelled((earlier, duplicate, second_duplicate),
                                 (duplicate.name, second_duplicate.name))
print("PASS: duplicate detection uses resolved identity across stale names, renames and fallback targets; reports each duplicated object once, including multiple duplicate sets")

settings.rule_index = 1
before = snapshot(duplicate)
assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
assert snapshot(duplicate) == before
assert any(line.kind == "ASSIGN" for line in settings.log)
earlier_before = snapshot(earlier)
assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
assert_full(duplicate, "New Group")
assert_full(duplicate, "Duplicate Pair.L")
assert duplicate.modifiers["Mirror"].use_mirror_vertex_groups
assert duplicate.vertex_groups["Existing"].lock_weight
assert abs(duplicate.vertex_groups["Existing"].weight(0) - 0.35) < 1e-6
assert snapshot(earlier) == earlier_before
settings.rule_index = 2
before = snapshot(duplicate)
assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
assert snapshot(duplicate) == before
assert any(line.kind == "DELETE" and "New Group" in line.message for line in settings.log)
assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
assert duplicate.vertex_groups.get("New Group") is None
assert duplicate.vertex_groups.get("Existing") is not None
print("PASS: explicit Active Preview/Apply still executes the selected assignment or cleanup rule when enabled duplicate targets exist")

reset()
first = mesh_object("First Valid Target", mirror=True)
second = mesh_object("Second Valid Target")
add_group(first, "Existing", 0.2)
addon.load_rules(bpy.context.scene, {
    first.name: {"assign_all_vertices": ["New Group", {"group": "Pair", "side": "L", "mirror": True}]},
    "Disabled Duplicate": {"delete_exact": ["New Group"]},
    second.name: {"assign_all_vertices": ["Second Weight"]},
    "Missing One": {}, "Missing Two": {},
})
settings = bpy.context.scene.vgr_settings
settings.rules[1].target, settings.rules[1].enabled = first, False
settings.rules[3].object_name = settings.rules[4].object_name = "Same Missing Target"
before = (snapshot(first), snapshot(second))
assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
assert (snapshot(first), snapshot(second)) == before
assert len([line for line in settings.log if line.kind == "WARNING"]) == 2
assert all("Object was not found" in line.message for line in settings.log if line.kind == "WARNING")
assert bpy.ops.vgr.apply(scope='ALL') == {'FINISHED'}
assert_full(first, "New Group")
assert_full(first, "Pair.L")
assert_full(second, "Second Weight")
assert abs(first.vertex_groups["Existing"].weight(0) - 0.2) < 1e-6
assert first.modifiers["Mirror"].use_mirror_vertex_groups
assert len([line for line in settings.log if line.kind == "WARNING"]) == 2
settings.rule_index = 1
assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
assert first.vertex_groups.get("New Group") is None
print("PASS: disabled duplicates do not block distinct enabled targets; repeated missing targets remain ordinary warnings; a disabled rule still runs explicitly through Active")

reset()
earlier = mesh_object("Earlier Single User", mirror=True)
shared = mesh_object("Shared Rule Target", mirror=True)
for target in (earlier, shared):
    add_group(target, "Existing", 0.35, indices=[0, 2]).lock_weight = True
hidden_owner = linked_copy(shared, "Hidden Disabled Owner")
hidden_owner.hide_set(True)
hidden_owner.hide_render = True
other_scene = bpy.data.scenes.new("Shared Owner Other Scene")
outside_owner = linked_copy(shared, "Outside Scene Owner", other_scene.collection)
unlinked_owner = shared.copy()
unlinked_owner.name = "Unlinked Mesh Owner"
shared.data.use_fake_user = True
addon.load_rules(bpy.context.scene, {
    earlier.name: {"delete_exact": ["Existing"], "assign_all_vertices": ["Earlier New Weight"]},
    shared.name: {"delete_exact": ["Existing"], "assign_all_vertices": [
        "Shared New Weight", {"group": "Shared Pair", "side": "L", "mirror": True},
    ]},
    hidden_owner.name: {"assign_all_vertices": ["Disabled Assignment"], "enabled": False},
})
settings = bpy.context.scene.vgr_settings
owners = (shared, hidden_owner, outside_owner, unlinked_owner)
targets = (earlier, *owners)
before = [snapshot(target) for target in targets]
assert bpy.ops.vgr.apply.get_rna_type().properties["allow_shared_data"].default is False


def shared_warnings():
    return [line.message for line in settings.log
            if line.kind == "WARNING" and "shared mesh" in line.message.lower()]


def assert_shared_owners(named_owners):
    messages = shared_warnings()
    assert len(messages) == 1, messages
    assert all(owner.name in messages[0] for owner in named_owners), messages
    assert shared.data.name in messages[0], messages


assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
assert [snapshot(target) for target in targets] == before
assert_shared_owners(owners)
assert any(line.kind == "DELETE" and earlier.name in line.message for line in settings.log)
assert any(line.kind == "ASSIGN" and shared.name in line.message for line in settings.log)
for scope in ('ALL', 'ACTIVE'):
    settings.rule_index = 1
    assert bpy.ops.vgr.apply(scope=scope) == {'CANCELLED'}
    assert [snapshot(target) for target in targets] == before
    assert_shared_owners(owners)
    assert "confirm" in settings.status.lower(), settings.status
    assert settings.show_log and settings.log_index == 0
print("PASS: shared mesh Preview names target and hidden, disabled, other-scene and unlinked owners; unconfirmed Active/All cancel without any changes, including an earlier single-user target")

stale_name = shared.name
shared.name = "Renamed Shared Rule Target"
hidden_owner.name = "Renamed Hidden Disabled Owner"
assert settings.rules[1].object_name == stale_name
assert bpy.ops.vgr.apply(scope='ALL') == {'CANCELLED'}
assert_shared_owners(owners)
settings.rules[1].target = None
settings.rules[1].object_name = shared.name
assert addon.target_object(settings.rules[1]) == shared
assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
assert_shared_owners(owners)
assert [snapshot(target) for target in targets] == before

assert bpy.ops.vgr.apply(scope='ALL', allow_shared_data=True) == {'FINISHED'}
assert earlier.vertex_groups.get("Existing") is None
assert_full(earlier, "Earlier New Weight")
assert shared.vertex_groups.get("Existing") is None
assert_full(shared, "Shared New Weight")
assert_full(shared, "Shared Pair.L")
assert shared.vertex_groups.get("Shared Pair.R") is not None
opposite_index = shared.vertex_groups["Shared Pair.R"].index
assert all(all(item.group != opposite_index for item in vertex.groups) for vertex in shared.data.vertices)
assert shared.modifiers["Mirror"].use_mirror_vertex_groups
assert all(not owner.modifiers["Mirror"].use_mirror_vertex_groups for owner in owners[1:])
assert all(owner.data == shared.data for owner in owners)
assert all(snapshot(owner)[1] == snapshot(shared)[1] for owner in owners)
assert all(snapshot(owner)[1] != before[index + 2][1] for index, owner in enumerate(owners[1:]))
assert_shared_owners(owners)
after_continue = [snapshot(target) for target in targets]
assert bpy.ops.vgr.apply(scope='ALL') == {'CANCELLED'}
assert [snapshot(target) for target in targets] == after_continue
assert_shared_owners(owners)
assert bpy.ops.vgr.apply(scope='ACTIVE', allow_shared_data=True) == {'FINISHED'}
assert [snapshot(target) for target in targets] == after_continue
print("PASS: current owner names survive target rename/fallback; explicit continuation performs cleanup, weights and Mirror settings while retaining sharing, and permission resets on the next Apply")

# Distinct enabled targets sharing a mesh are unsafe as one batch, even with opt-in.
settings.rules[2].enabled = True
for operation, arguments in ((bpy.ops.vgr.preview, {}), (bpy.ops.vgr.apply, {}),
                             (bpy.ops.vgr.apply, {"allow_shared_data": True})):
    assert operation(scope='ALL', **arguments) == {'CANCELLED'}
    assert [snapshot(target) for target in targets] == after_continue
    assert len(settings.log) == 1 and settings.log[0].kind == "WARNING"
    assert all(name in settings.log[0].message for name in
               (shared.data.name, shared.name, hidden_owner.name))
    assert "No rules ran" in settings.status
extra = settings.rules.add()
extra.target, extra.object_name, extra.pattern_lists_split = shared, shared.name, True
for operation, opt_in in ((bpy.ops.vgr.preview, False), (bpy.ops.vgr.apply, True)):
    arguments = {"scope": 'ALL'}
    if opt_in:
        arguments["allow_shared_data"] = True
    assert operation(**arguments) == {'CANCELLED'}
    assert [snapshot(target) for target in targets] == after_continue
    assert not shared_warnings()
    assert any("enabled rules" in line.message for line in settings.log)
print("PASS: distinct enabled targets sharing one mesh block both batch operators and opt-in; duplicate object guard takes precedence")

reset()
earlier = mesh_object("Earlier Linked Batch Guard", mirror=True)
first = mesh_object("Linked Assignment Target", mirror=True)
second = linked_copy(first, "Linked Cleanup Target")
no_op = mesh_object("Linked No-op Target")
invalid = linked_copy(no_op, "Linked Invalid Target")
disabled_owner = linked_copy(first, "Disabled Linked Batch Target")
for obj in (earlier, first, no_op):
    add_group(obj, "Original", 0.35, indices=[0, 2]).lock_weight = True
addon.load_rules(bpy.context.scene, {
    earlier.name: {"delete_exact": ["Original"], "assign_all_vertices": ["Earlier New Weight"]},
    first.name: {"assign_all_vertices": ["Dependency Weight", {"group": "Linked Pair", "side": "L", "mirror": True}]},
    second.name: {"delete_exact": ["Dependency Weight"]},
    no_op.name: {}, invalid.name: {"keep_exact": ["Original"]},
    disabled_owner.name: {"assign_all_vertices": ["Disabled Weight"], "enabled": False},
    "Missing Linked Batch Target": {},
})
settings = bpy.context.scene.vgr_settings
first.name = "Renamed Linked Assignment Target"
settings.rules[2].target = None
settings.rules[2].object_name = second.name
assert addon.target_object(settings.rules[2]) == second
missing_bound = linked_copy(first, "Deleted Linked Batch Target")
missing_rule = settings.rules.add()
missing_rule.pattern_lists_split = True
missing_rule.target = missing_bound
missing_rule.object_name = first.name
bpy.data.objects.remove(missing_bound, do_unlink=True)
assert missing_rule.target is None and missing_rule.target_was_set
assert addon.target_object(missing_rule) is None
batch_objects = (earlier, first, second, no_op, invalid, disabled_owner)
batch_before = [snapshot(obj) for obj in batch_objects]

def assert_linked_batch_blocked():
    for operation, arguments in ((bpy.ops.vgr.preview, {}), (bpy.ops.vgr.apply, {}),
                                 (bpy.ops.vgr.apply, {"allow_shared_data": True})):
        assert operation(scope='ALL', **arguments) == {'CANCELLED'}
        assert [snapshot(obj) for obj in batch_objects] == batch_before
        assert "No rules ran" in settings.status
        assert settings.show_log and settings.log_index == 0
        assert len(settings.log) == 2 and all(line.kind == "WARNING" for line in settings.log)
        for a, b in ((first, second), (no_op, invalid)):
            messages = [line.message for line in settings.log if a.data.name in line.message]
            assert len(messages) == 1, [line.message for line in settings.log]
            assert a.name in messages[0] and b.name in messages[0]
            assert disabled_owner.name not in messages[0]
            assert "Missing Linked Batch Target" not in messages[0]
        assert not any("Object was not found" in line.message for line in settings.log)

assert_linked_batch_blocked()
invalid_entry = settings.rules[4].delete_patterns.add()
invalid_entry.kind, invalid_entry.value = "delete_regex", "["
assert_linked_batch_blocked()
print("PASS: multiple shared-target batches block assign-then-delete dependencies before an earlier mesh changes; no-op and invalid enabled rules count, aliases/renames resolve, and disabled/missing targets are excluded")

settings.rules[2].enabled = settings.rules[4].enabled = False
assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
assert [snapshot(obj) for obj in batch_objects] == batch_before
assert len([line for line in settings.log if "Object was not found" in line.message]) == 2
assert bpy.ops.vgr.apply(scope='ALL') == {'CANCELLED'}
assert [snapshot(obj) for obj in batch_objects] == batch_before
assert "confirm" in settings.status.lower()
settings.rules[2].enabled = settings.rules[4].enabled = True
settings.rule_index = 1
assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
assert [snapshot(obj) for obj in batch_objects] == batch_before
assert bpy.ops.vgr.apply(scope='ACTIVE') == {'CANCELLED'}
assert [snapshot(obj) for obj in batch_objects] == batch_before
assert bpy.ops.vgr.apply(scope='ACTIVE', allow_shared_data=True) == {'FINISHED'}
assert_full(first, "Dependency Weight")
assert_full(first, "Linked Pair.L")
assert first.modifiers["Mirror"].use_mirror_vertex_groups
assert snapshot(earlier) == batch_before[0]
assert (snapshot(no_op), snapshot(invalid)) == (batch_before[3], batch_before[4])
print("PASS: disabling competing shared targets restores ordinary Preview and shared-data confirmation; Active can continue explicitly while the batch remains blocked")

reset()
shared_targets = []
shared_sets = []
for number in (1, 2):
    target = mesh_object(f"Shared Batch Target {number}")
    add_group(target, "Original", 0.3)
    owner = linked_copy(target, f"Shared Batch Owner {number}")
    shared_targets.append(target)
    shared_sets.append((target, owner))
addon.load_rules(bpy.context.scene, {
    target.name: {"delete_exact": ["Original"], "assign_all_vertices": ["Batch Weight"]}
    for target in shared_targets
})
settings = bpy.context.scene.vgr_settings
before = [[snapshot(obj) for obj in objects] for objects in shared_sets]
for operation, expected in ((bpy.ops.vgr.preview, {'FINISHED'}), (bpy.ops.vgr.apply, {'CANCELLED'})):
    assert operation(scope='ALL') == expected
    assert [[snapshot(obj) for obj in objects] for objects in shared_sets] == before
    messages = shared_warnings()
    assert len(messages) == 2, messages
    for target, owner in shared_sets:
        matching = [message for message in messages if target.data.name in message]
        assert len(matching) == 1 and target.name in matching[0] and owner.name in matching[0]
print("PASS: multiple distinct shared meshes produce one warning per mesh and require confirmation before any target changes")

reset()
single = mesh_object("Single Owner With Fake User")
single.data.use_fake_user = True
assert single.data.users > 1
same_name_mesh = mesh_object("Different Mesh Owner")
same_name_mesh.data.name = single.data.name
addon.load_rules(bpy.context.scene, {single.name: {"assign_all_vertices": ["Single Weight"]}})
settings = bpy.context.scene.vgr_settings
assert bpy.ops.vgr.apply(scope='ALL') == {'FINISHED'}
assert_full(single, "Single Weight")
assert not shared_warnings()
assert not same_name_mesh.vertex_groups
print("PASS: object data identity detects sharing; mesh fake users and separate similarly named meshes do not require confirmation")

reset()
shared = mesh_object("No-op Shared Target", mirror=True)
add_group(shared, "Preserved", 0.4, indices=[0])
owner = linked_copy(shared, "No-op Linked Owner")
settings = bpy.context.scene.vgr_settings
for values in ({}, {"keep_exact": ["Preserved"]}, {"delete_exact": ["Missing Group"]},
               {"keep_exact": ["Preserved"], "delete_exact": ["Preserved"]}):
    addon.load_rules(bpy.context.scene, {shared.name: values})
    before = (snapshot(shared), snapshot(owner))
    for operation in (bpy.ops.vgr.preview, bpy.ops.vgr.apply):
        assert operation(scope='ALL') == {'FINISHED'}
        assert (snapshot(shared), snapshot(owner)) == before
        assert not shared_warnings()
addon.load_rules(bpy.context.scene, {shared.name: {"assign_all_vertices": ["Disabled Weight"], "enabled": False}})
before = (snapshot(shared), snapshot(owner))
assert bpy.ops.vgr.apply(scope='ALL') == {'CANCELLED'}
assert (snapshot(shared), snapshot(owner)) == before
assert not shared_warnings()
assert bpy.ops.vgr.apply(scope='ACTIVE') == {'CANCELLED'}
assert len(shared_warnings()) == 1
assert (snapshot(shared), snapshot(owner)) == before
print("PASS: Keep-only, empty and unmatched cleanup rules do not warn about shared data; disabled rules are excluded from All while explicitly selected Active rules require confirmation")

addon.load_rules(bpy.context.scene, {shared.name: {
    "delete_exact": ["Preserved"], "assign_all_vertices": ["Valid Early Assignment", "Placeholder"],
}})
addon.active_rule(bpy.context.scene).assignments[1].group_name = "é" * 32
before = (snapshot(shared), snapshot(owner))
for opt_in in (False, True):
    assert bpy.ops.vgr.apply(scope='ALL', allow_shared_data=opt_in) == {'FINISHED'}
    assert (snapshot(shared), snapshot(owner)) == before
    assert not shared_warnings()
    assert len(settings.log) == 1 and "Blender allows 63" in settings.log[0].message
rule = addon.active_rule(bpy.context.scene)
rule.assignments[1].group_name = "Now Valid"
entry = rule.delete_patterns.add()
entry.kind, entry.value = "delete_regex", "["
assert bpy.ops.vgr.apply(scope='ACTIVE', allow_shared_data=True) == {'FINISHED'}
assert (snapshot(shared), snapshot(owner)) == before
assert not shared_warnings()
assert len(settings.log) == 1 and "Invalid Delete Regex" in settings.log[0].message
empty_mesh = bpy.data.meshes.new("Empty Shared Mesh")
empty = bpy.data.objects.new("Empty Shared Target", empty_mesh)
bpy.context.collection.objects.link(empty)
empty_owner = linked_copy(empty, "Empty Linked Owner")
addon.load_rules(bpy.context.scene, {empty.name: {}})
assert bpy.ops.vgr.apply(scope='ALL') == {'FINISHED'}
assert not empty.vertex_groups and not empty_owner.vertex_groups and not shared_warnings()
print("PASS: invalid UTF8 names and regex still skip shared rules before cleanup even after opt-in; an empty shared mesh with no actions remains a harmless no-op")

reset()
edit_target = mesh_object("Object Mode Shared Target", mirror=True)
add_group(edit_target, "Original Editable Weight", 0.35, indices=[0, 2]).lock_weight = True
add_group(edit_target, "Retained Editable Weight", 0.6, indices=[1])
edit_sibling = linked_copy(edit_target, "Edit Mode Shared Sibling")
addon.load_rules(bpy.context.scene, {edit_target.name: {
    "delete_exact": ["Original Editable Weight"],
    "assign_all_vertices": ["New Editable Weight", {"group": "Editable Pair", "side": "L", "mirror": True}],
}})
settings = bpy.context.scene.vgr_settings
before_edit = (snapshot(edit_target), snapshot(edit_sibling))
for selected in list(bpy.context.selected_objects):
    selected.select_set(False)
edit_sibling.select_set(True)
bpy.context.view_layer.objects.active = edit_sibling
assert bpy.ops.object.mode_set(mode='EDIT') == {'FINISHED'}
assert edit_target.mode == 'OBJECT' and edit_sibling.mode == 'EDIT'
assert edit_target.data.is_editmode
for scope in ('ACTIVE', 'ALL'):
    for operation, arguments in (
        (bpy.ops.vgr.preview, {}),
        (bpy.ops.vgr.apply, {}),
        (bpy.ops.vgr.apply, {"allow_shared_data": True}),
    ):
        assert operation(scope=scope, **arguments) == {'FINISHED'}
        assert (snapshot(edit_target), snapshot(edit_sibling)) == before_edit
        assert len(settings.log) == 1 and settings.log[0].kind == "WARNING"
        assert edit_target.name in settings.log[0].message
        assert "Object Mode" in settings.log[0].message
        assert not shared_warnings()
        assert edit_target.mode == 'OBJECT' and edit_sibling.mode == 'EDIT'
assert bpy.ops.object.mode_set(mode='OBJECT') == {'FINISHED'}
assert not edit_target.data.is_editmode
assert (snapshot(edit_target), snapshot(edit_sibling)) == before_edit
print("PASS: a linked sibling in Edit Mode blocks Preview, default Apply and shared-data opt-in before cleanup, weights or Mirror changes; groups and weights remain intact after leaving Edit Mode")

reset()
placeholder = mesh_object("Choose an object", mirror=True)
add_group(placeholder, "Existing Weight", 0.35, indices=[0, 2]).lock_weight = True
addon.load_rules(bpy.context.scene, {placeholder.name: {
    "delete_exact": ["Existing Weight"], "assign_all_vertices": ["Exported Weight"],
}})
settings = bpy.context.scene.vgr_settings
before_export_mesh = snapshot(placeholder)
placeholder_preset = ARTIFACTS / "placeholder_export_roundtrip.json"
try:
    expected_placeholder = addon.export_rules(bpy.context.scene)
    assert set(expected_placeholder) == {"Choose an object"}
    assert bpy.ops.vgr.export_rules(filepath=str(placeholder_preset)) == {'FINISHED'}
    assert json.loads(placeholder_preset.read_text(encoding="utf-8")) == expected_placeholder
    addon.load_rules(bpy.context.scene, {})
    assert bpy.ops.vgr.import_rules(filepath=str(placeholder_preset)) == {'FINISHED'}
    assert addon.active_rule(bpy.context.scene).target == placeholder
    assert addon.export_rules(bpy.context.scene) == expected_placeholder
    assert snapshot(placeholder) == before_export_mesh

    placeholder.name = "Renamed Placeholder Mesh"
    assert bpy.ops.vgr.export_rules(filepath=str(placeholder_preset)) == {'FINISHED'}
    expected_renamed = json.loads(placeholder_preset.read_text(encoding="utf-8"))
    assert set(expected_renamed) == {placeholder.name}
    assert expected_renamed[placeholder.name] == expected_placeholder["Choose an object"]
    assert snapshot(placeholder) == before_export_mesh

    preserved_file = b'{"existing": "preserve this destination"}\n'
    def assert_export_rejected(message):
        placeholder_preset.write_bytes(preserved_file)
        before_settings = raw_settings_snapshot(settings)
        try:
            addon.export_rules(bpy.context.scene)
        except ValueError as error:
            assert message in str(error), str(error)
        else:
            raise AssertionError("Invalid export was accepted")
        try:
            result = bpy.ops.vgr.export_rules(filepath=str(placeholder_preset))
        except RuntimeError as error:
            assert message in str(error), str(error)
        else:
            assert result == {'CANCELLED'}, result
        assert placeholder_preset.read_bytes() == preserved_file
        assert raw_settings_snapshot(settings) == before_settings
        assert snapshot(placeholder) == before_export_mesh

    blank_rule = settings.rules.add()
    blank_rule.pattern_lists_split = True
    assert_export_rejected("Choose an object or enter a name")
    settings.rules.remove(1)
    duplicate_rule = settings.rules.add()
    duplicate_rule.pattern_lists_split = True
    duplicate_rule.target = placeholder
    for enabled in (True, False):
        duplicate_rule.enabled = enabled
        assert_export_rejected("Two rules target")

    reset()
    unrelated = mesh_object("Unrelated Export Guard", mirror=True)
    add_group(unrelated, "Preserved Weight", 0.45, indices=[1]).lock_weight = True
    unrelated_before = snapshot(unrelated)
    addon.load_rules(bpy.context.scene, expected_placeholder)
    fallback_rule = addon.active_rule(bpy.context.scene)
    assert fallback_rule.target is None and not fallback_rule.target_was_set
    assert addon.target_object(fallback_rule) is None
    assert bpy.ops.vgr.export_rules(filepath=str(placeholder_preset)) == {'FINISHED'}
    assert json.loads(placeholder_preset.read_text(encoding="utf-8")) == expected_placeholder
    addon.load_rules(bpy.context.scene, {})
    assert bpy.ops.vgr.import_rules(filepath=str(placeholder_preset)) == {'FINISHED'}
    assert addon.active_rule(bpy.context.scene).target is None
    assert addon.export_rules(bpy.context.scene) == expected_placeholder
    assert snapshot(unrelated) == unrelated_before
finally:
    placeholder_preset.unlink(missing_ok=True)
print("PASS: actual Export accepts resolved and unresolved 'Choose an object' names, follows resolved renames and roundtrips JSON without mesh changes; blank and enabled/disabled duplicate rules preserve existing export files and raw settings")

reset()
obj = mesh_object("Added from Selection")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.vgr.add_rule(selected=True)
bpy.ops.vgr.add_rule(selected=True)
assert len(bpy.context.scene.vgr_settings.rules) == 1
bpy.ops.vgr.edit_list(list_name='DELETE', action='ADD')
rule = addon.active_rule(bpy.context.scene)
rule.delete_patterns[0].kind, rule.delete_patterns[0].value = "delete_contains", "jaw"
for kind, value in (("keep_only_prefixes", "DEF-"), ("keep_exact", "Shell"), ("keep_contains", "eye"),
                    ("keep_suffixes", ".L"), ("keep_regex", r"^DEF-eye[.]L$")):
    bpy.ops.vgr.edit_list(list_name='KEEP', action='ADD')
    entry = rule.keep_patterns[rule.keep_pattern_index]
    entry.kind, entry.value = kind, value
for kind, value in (("delete_suffixes", ".R"), ("delete_regex", r"^jaw\d+$")):
    bpy.ops.vgr.edit_list(list_name='DELETE', action='ADD')
    entry = rule.delete_patterns[rule.delete_pattern_index]
    entry.kind, entry.value = kind, value
rule.keep_case_sensitive = True
assert not rule.delete_case_sensitive
bpy.ops.vgr.edit_list(list_name='ASSIGNMENT', action='ADD')
rule.assignments[0].group_name = "Custom Weight"
rule.enabled = False
obj.name = "Renamed Mesh"
second = mesh_object("Opposite Case Settings")
second.select_set(True)
obj.select_set(False)
bpy.context.view_layer.objects.active = second
bpy.ops.vgr.add_rule(selected=True)
second_rule = addon.active_rule(bpy.context.scene)
second_rule.delete_case_sensitive = True
assert not second_rule.keep_case_sensitive
entry = second_rule.delete_patterns.add()
entry.kind, entry.value = "delete_regex", r"^Case[.]L$"
expected = addon.export_rules(bpy.context.scene)
assert "Renamed Mesh" in expected
preset = ARTIFACTS / "roundtrip_rules.json"
assert bpy.ops.vgr.export_rules(filepath=str(preset)) == {'FINISHED'}
addon.load_rules(bpy.context.scene, {})
assert bpy.ops.vgr.import_rules(filepath=str(preset)) == {'FINISHED'}
assert addon.export_rules(bpy.context.scene) == expected
assert not addon.active_rule(bpy.context.scene).enabled
assert addon.active_rule(bpy.context.scene).keep_case_sensitive
assert not addon.active_rule(bpy.context.scene).delete_case_sensitive
assert not bpy.context.scene.vgr_settings.rules[1].keep_case_sensitive
assert bpy.context.scene.vgr_settings.rules[1].delete_case_sensitive
print("PASS: GUI add/edit operators, selection deduplication, object rename tracking, JSON import/export")

settings = bpy.context.scene.vgr_settings
settings.rules[0].enabled = False
saved = ARTIFACTS / "rule_persistence.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(saved), check_existing=False)
bpy.ops.wm.open_mainfile(filepath=str(saved))
assert addon.export_rules(bpy.context.scene) == expected
assert not bpy.context.scene.vgr_settings.rules[0].enabled
assert addon.target_object(bpy.context.scene.vgr_settings.rules[0]).name == "Renamed Mesh"
assert bpy.context.scene.vgr_settings.rules[0].keep_case_sensitive
assert not bpy.context.scene.vgr_settings.rules[0].delete_case_sensitive
assert not bpy.context.scene.vgr_settings.rules[1].keep_case_sensitive
assert bpy.context.scene.vgr_settings.rules[1].delete_case_sensitive
print("PASS: object pointers, all new filter types, independent case flags and enable flags survive JSON and .blend roundtrips")

unsafe = ARTIFACTS / "literal_import.py"
unsafe.write_text("OBJECT_RULES = {'Imported': {'assign_all_vertices': ['Anything']}}\nraise RuntimeError('MUST NOT EXECUTE')\n", encoding="utf-8")
assert bpy.ops.vgr.import_rules(filepath=str(unsafe)) == {'FINISHED'}
assert len(bpy.context.scene.vgr_settings.rules) == 1
assert addon.active_rule(bpy.context.scene).object_name == "Imported"
assert addon.export_rules(bpy.context.scene)["Imported"]["assign_all_vertices"] == ["Anything"]
print("PASS: Python import reads user-supplied literal rules without executing code")

addon.unregister()
assert not hasattr(bpy.types.Scene, "vgr_settings")
assert addon.initialize_loaded_scenes not in bpy.app.handlers.load_post
addon.register()
addon.unregister()
print("PASS: unregister and re-register cleanly")
print("ALL ADD-ON INTEGRATION CHECKS PASSED")
