# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph
#
# This file is part of VG Rules.
#
# VG Rules is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# VG Rules is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with VG Rules. If not, see https://www.gnu.org/licenses/.

bl_info = {
    "name": "VG Rules",
    "author": "Blank Glyph",
    "version": (0, 1, 1),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > VG Rules",
    "description": "Edit object cleanup rules and assign all mesh vertices full group weights",
    "category": "Rigging",
}

import json
import textwrap

import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup, UIList
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import engine, presets


KEEP_ITEMS = (
    ("keep_only_prefixes", "Keep Prefix", "Protect groups beginning with this text from every Delete rule"),
    ("keep_exact", "Keep Exact", "Protect groups whose names match exactly from every Delete rule"),
    ("keep_contains", "Keep Contains", "Protect groups containing this text anywhere from every Delete rule"),
    ("keep_suffixes", "Keep Suffix", "Protect groups ending with this text from every Delete rule"),
    ("keep_regex", "Keep Regex", "Protect groups matching a Python regex search; use ^/$ to anchor. Regex matching has a one-second worker deadline per rule"),
)

DELETE_ITEMS = (
    ("delete_exact", "Delete Exact", "Delete groups whose names match exactly unless a Keep rule matches"),
    ("delete_prefixes", "Delete Prefix", "Delete groups beginning with this text unless a Keep rule matches"),
    ("delete_contains", "Delete Contains", "Delete groups containing this text anywhere unless a Keep rule matches"),
    ("delete_suffixes", "Delete Suffix", "Delete groups ending with this text unless a Keep rule matches"),
    ("delete_regex", "Delete Regex", "Delete groups matching a Python regex search unless a Keep rule matches; use ^/$ to anchor. Regex matching has a one-second worker deadline per rule"),
)

# Preserve the original enum values when reading old saved .blend data.
LEGACY_PATTERN_ITEMS = (
    ("keep_only_prefixes", "Keep Prefix", "", 0),
    ("delete_exact", "Delete Exact", "", 1),
    ("delete_prefixes", "Delete Prefix", "", 2),
    ("delete_contains", "Delete Contains", "", 3),
)

SIDE_ITEMS = (
    ("EXACT", "Exact Name", "Use the group name exactly as entered"),
    ("AUTO", "Auto Side", "Choose .L/.R from matching rest-pose bones or the X Mirror plane"),
    ("L", "Left (.L)", "Assign the .L group"),
    ("R", "Right (.R)", "Assign the .R group"),
)


class VGR_Pattern(PropertyGroup):
    """Legacy mixed list, retained only to migrate saved rules."""
    kind: EnumProperty(name="Match", items=LEGACY_PATTERN_ITEMS)
    value: StringProperty(name="Text")


class VGR_KeepPattern(PropertyGroup):
    kind: EnumProperty(name="Match", items=KEEP_ITEMS)
    value: StringProperty(name="Text", description="Vertex group protection text or regular expression")


class VGR_DeletePattern(PropertyGroup):
    kind: EnumProperty(name="Match", items=DELETE_ITEMS)
    value: StringProperty(name="Text", description="Vertex group match text or regular expression")


class VGR_Assignment(PropertyGroup):
    group_name: StringProperty(name="Group", description="Exact vertex group name, or a base name when choosing a side")
    side: EnumProperty(name="Side", items=SIDE_ITEMS, default="EXACT")
    mirror: BoolProperty(name="Mirror Weights", description="Create and empty the opposite .L/.R group and enable Mirror vertex groups")


def mesh_poll(self, obj):
    return obj.type == 'MESH' and object_in_scene(obj, self.id_data)


def update_rule_target(rule, context):
    if rule.target is not None:
        rule.object_name = rule.target.name
        rule.target_was_set = True
    # A cleared/deleted pointer retains its binding history and needs reselection.


def update_fallback_name(rule, context):
    if rule.target is None:
        # Editing the fallback explicitly opts back into name-based resolution.
        rule.target_was_set = False


class VGR_ObjectRule(PropertyGroup):
    enabled: BoolProperty(name="Enabled", default=True, description="Include this rule when running all rules")
    target: PointerProperty(name="Object", type=bpy.types.Object, poll=mesh_poll, update=update_rule_target)
    object_name: StringProperty(name="Object Name", description="Edit to explicitly resolve an unselected target by name", update=update_fallback_name)
    # Keep this after target/name so raw rollback restores history after callbacks.
    target_was_set: BoolProperty(default=False, options={'HIDDEN'})
    patterns: CollectionProperty(type=VGR_Pattern)
    pattern_index: IntProperty(default=0)
    pattern_lists_split: BoolProperty(default=False)
    keep_patterns: CollectionProperty(type=VGR_KeepPattern)
    keep_pattern_index: IntProperty(default=0)
    keep_case_sensitive: BoolProperty(name="Case Sensitive", default=False, description="Match letter case for all Keep filters; unchecked ignores case")
    delete_patterns: CollectionProperty(type=VGR_DeletePattern)
    delete_pattern_index: IntProperty(default=0)
    delete_case_sensitive: BoolProperty(name="Case Sensitive", default=False, description="Match letter case for all Delete filters; unchecked ignores case")
    assignments: CollectionProperty(type=VGR_Assignment)
    assignment_index: IntProperty(default=0)


class VGR_LogLine(PropertyGroup):
    kind: StringProperty()
    message: StringProperty()


class VGR_Settings(PropertyGroup):
    initialized: BoolProperty(default=False)
    rules: CollectionProperty(type=VGR_ObjectRule)
    rule_index: IntProperty(default=0)
    log: CollectionProperty(type=VGR_LogLine)
    log_index: IntProperty(default=0)
    status: StringProperty(default="Add selected meshes or create a new rule to get started.")
    show_log: BoolProperty(name="Results", default=True)


def active_rule(scene):
    settings = scene.vgr_settings
    if 0 <= settings.rule_index < len(settings.rules):
        return settings.rules[settings.rule_index]
    return None


def object_in_scene(obj, scene):
    return obj is not None and scene.objects.get(obj.name) == obj


def target_object(rule, scene=None):
    scene = scene if scene is not None else rule.id_data
    if rule.target is not None:
        return rule.target if object_in_scene(rule.target, scene) else None
    if rule.target_was_set:
        return None
    return scene.objects.get(rule.object_name)


def rule_name(rule, scene=None):
    obj = rule.target if rule.target is not None else target_object(rule, scene)
    return obj.name if obj is not None else rule.object_name or "Choose an object"


def split_legacy_patterns(rule):
    if rule.pattern_lists_split:
        return
    for index, old in enumerate(rule.patterns):
        is_keep = old.kind in engine.KEEP_KEYS
        collection = rule.keep_patterns if is_keep else rule.delete_patterns
        entry = collection.add()
        entry.kind, entry.value = old.kind, old.value
        if index == rule.pattern_index:
            if is_keep:
                rule.keep_pattern_index = len(collection) - 1
            else:
                rule.delete_pattern_index = len(collection) - 1
    rule.patterns.clear()
    rule.pattern_lists_split = True


def rule_dictionary(rule):
    split_legacy_patterns(rule)
    result = {key: [] for key in engine.PATTERN_KEYS}
    for pattern in (*rule.keep_patterns, *rule.delete_patterns):
        if not pattern.value.strip():
            raise ValueError("Enter text for every match rule, or remove the blank row.")
        result[pattern.kind].append(pattern.value)
    # Keep older JSON/script presets unchanged when the new types are unused.
    for key in ("keep_exact", "keep_contains", "keep_suffixes", "keep_regex", "delete_suffixes", "delete_regex"):
        if not result[key]:
            del result[key]
    for key in engine.CASE_KEYS:
        if getattr(rule, key):
            result[key] = True
    assignments = []
    for entry in rule.assignments:
        if entry.side == "EXACT" and not entry.mirror:
            assignments.append(entry.group_name)
        else:
            settings = {"group": entry.group_name}
            if entry.side != "EXACT":
                settings["side"] = entry.side
            if entry.mirror:
                settings["mirror"] = True
            assignments.append(settings)
    if assignments:
        result["assign_all_vertices"] = assignments
    return result


def snapshot_property_group(group):
    """Keep raw RNA data, including unfinished rows and legacy UI state."""
    values = {}
    for prop in group.bl_rna.properties:
        if prop.type == 'COLLECTION':
            values[prop.identifier] = [snapshot_property_group(item) for item in getattr(group, prop.identifier)]
        elif not prop.is_readonly:
            values[prop.identifier] = getattr(group, prop.identifier)
    return values


def restore_property_group(group, values):
    for name, value in values.items():
        if group.bl_rna.properties[name].type == 'COLLECTION':
            collection = getattr(group, name)
            collection.clear()
            for item in value:
                restore_property_group(collection.add(), item)
        else:
            setattr(group, name, value)


def populate_rules(collection, rules, scene):
    for object_name, values in rules.items():
        rule = collection.add()
        rule.pattern_lists_split = True
        rule.enabled = values.get("enabled", True)
        for key in engine.CASE_KEYS:
            setattr(rule, key, values.get(key, False))
        rule.object_name = object_name
        obj = scene.objects.get(object_name)
        if obj is not None and obj.type == 'MESH':
            rule.target = obj
        for kind in engine.PATTERN_KEYS:
            for value in values.get(kind, []):
                patterns = rule.keep_patterns if kind in engine.KEEP_KEYS else rule.delete_patterns
                pattern = patterns.add()
                pattern.kind = kind
                pattern.value = value
        for entry in values.get("assign_all_vertices", []):
            entry = {"group": entry} if isinstance(entry, str) else entry
            assignment = rule.assignments.add()
            assignment.group_name = entry["group"]
            assignment.side = entry.get("side") or "EXACT"
            assignment.mirror = entry.get("mirror", False)


def load_rules(scene, rules):
    # Complete validation before clearing any RNA rows or storing text in Blender.
    presets.validate_rules(rules)
    settings = scene.vgr_settings
    previous = snapshot_property_group(settings)
    try:
        settings.rules.clear()
        populate_rules(settings.rules, rules, scene)
        settings.initialized = True
        settings.rule_index = 0
        settings.log.clear()
        settings.status = (f"Loaded {len(settings.rules)} object rules. Preview before applying."
                           if settings.rules else "Add selected meshes or create a new rule to get started.")
    except Exception as error:
        restore_property_group(settings, previous)
        raise ValueError(f"Could not load rules; previous configuration restored: {error!r}") from error


def export_rules(scene):
    initialize_scene(scene)
    result = {}
    for rule in scene.vgr_settings.rules:
        obj = rule.target if rule.target is not None else target_object(rule, scene)
        name = obj.name if obj is not None else rule.object_name
        if not name:
            raise ValueError("Choose an object or enter a name for every rule before exporting.")
        if name in result:
            raise ValueError(f'Two rules target "{name}". Combine them before exporting.')
        result[name] = rule_dictionary(rule)
        if not rule.enabled:
            result[name]["enabled"] = False
    return presets.validate_rules(result)


def log_line(settings, kind, message):
    line = settings.log.add()
    line.kind = kind
    line.message = message


class VGR_OT_add_rule(Operator):
    bl_idname = "vgr.add_rule"
    bl_label = "Add Object Rule"
    bl_options = {'REGISTER', 'UNDO'}
    selected: BoolProperty(default=False)

    def execute(self, context):
        settings = context.scene.vgr_settings
        settings.initialized = True
        objects = [obj for obj in context.selected_objects
                   if obj.type == 'MESH' and object_in_scene(obj, context.scene)] if self.selected else [None]
        added = 0
        for obj in objects:
            existing = next((index for index, rule in enumerate(settings.rules)
                             if obj is not None and target_object(rule, context.scene) == obj), None)
            if existing is not None:
                settings.rule_index = existing
                continue
            rule = settings.rules.add()
            rule.pattern_lists_split = True
            if obj is not None:
                rule.target = obj
                rule.object_name = obj.name
            settings.rule_index = len(settings.rules) - 1
            added += 1
        self.report({'INFO'}, f"Added {added} rule(s).")
        return {'FINISHED'}


class VGR_OT_edit_list(Operator):
    bl_idname = "vgr.edit_list"
    bl_label = "Edit Rules"
    bl_options = {'REGISTER', 'UNDO'}
    list_name: EnumProperty(items=(('RULE', "Object", ""), ('KEEP', "Keep Rule", ""), ('DELETE', "Delete Rule", ""), ('ASSIGNMENT', "Assignment", "")))
    action: EnumProperty(items=(('ADD', "Add", ""), ('REMOVE', "Remove", ""), ('UP', "Up", ""), ('DOWN', "Down", "")))

    def execute(self, context):
        settings = context.scene.vgr_settings
        if self.list_name == 'RULE':
            owner, name, index_name = settings, "rules", "rule_index"
        else:
            owner = active_rule(context.scene)
            if owner is None:
                return {'CANCELLED'}
            split_legacy_patterns(owner)
            name, index_name = {
                'KEEP': ("keep_patterns", "keep_pattern_index"),
                'DELETE': ("delete_patterns", "delete_pattern_index"),
                'ASSIGNMENT': ("assignments", "assignment_index"),
            }[self.list_name]
        collection = getattr(owner, name)
        index = getattr(owner, index_name)
        if self.action == 'ADD':
            entry = collection.add()
            if self.list_name == 'RULE':
                entry.pattern_lists_split = True
            setattr(owner, index_name, len(collection) - 1)
        elif 0 <= index < len(collection):
            if self.action == 'REMOVE':
                collection.remove(index)
                setattr(owner, index_name, max(0, min(index, len(collection) - 1)))
            else:
                destination = index + (-1 if self.action == 'UP' else 1)
                if 0 <= destination < len(collection):
                    collection.move(index, destination)
                    setattr(owner, index_name, destination)
        return {'FINISHED'}


def scoped_rules(scene, scope):
    initialize_scene(scene)
    settings = scene.vgr_settings
    if scope == 'ALL':
        rules = [rule for rule in settings.rules if rule.enabled]
    else:
        rule = active_rule(scene)
        rules = [rule] if rule is not None else []
    # Capture the identity of newly resolved imported names before running them.
    # target_object itself stays read-only because the sidebar also calls it.
    for rule in rules:
        obj = target_object(rule, scene)
        if obj is not None and obj.type == 'MESH':
            if rule.target is None:
                rule.target = obj
            else:
                update_rule_target(rule, None)
    return rules


def duplicate_rule_targets(rules, scene):
    seen_targets = set()
    duplicates = {}
    for rule in rules:
        obj = target_object(rule, scene)
        if obj is None:
            continue
        identity = obj.as_pointer()
        if identity in seen_targets:
            duplicates[identity] = obj
        seen_targets.add(identity)
    return list(duplicates.values())


def conflicting_mesh_targets(rules, scene):
    groups = {}
    for rule in rules:
        if not rule.enabled:
            continue
        obj = target_object(rule, scene)
        if obj is None or obj.type != 'MESH':
            continue
        # Count targets before planning: a currently empty match can become
        # active after an earlier rule assigns a group on the same mesh.
        group = groups.setdefault(obj.data.as_pointer(), {"mesh": obj.data, "targets": {}})
        group["targets"][obj.as_pointer()] = obj
    return [group for group in groups.values() if len(group["targets"]) > 1]


def mesh_conflict_message(group):
    mesh_name = json.dumps(group["mesh"].name, ensure_ascii=False)
    return (f'All blocked: multiple enabled rules use mesh {mesh_name} and can affect each other\'s results. '
            f'Objects: {object_names(group["targets"].values())}. '
            'Disable extra rules or use Preview Rule and Apply Rule one at a time.')


def shared_mesh_groups(rules, scene):
    owners = {}
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            owners.setdefault(obj.data.as_pointer(), []).append(obj)
    groups = {}
    for rule in rules:
        obj = target_object(rule, scene)
        if obj is None or obj.type != 'MESH':
            continue
        identity = obj.data.as_pointer()
        objects = owners.get(identity, [])
        # One object can affect several scenes without another mesh user.
        scenes = {owner.as_pointer(): tuple(owner.users_scene) for owner in objects}
        if len(objects) < 2 and len(scenes.get(obj.as_pointer(), ())) < 2:
            continue
        try:
            plan = engine.make_plan(obj, rule_dictionary(rule))
        except (ValueError, RuntimeError, KeyError, TypeError):
            # Invalid rules are reported by run_rules and cannot change a mesh.
            continue
        if not plan.delete_names and not plan.assignments:
            continue
        group = groups.setdefault(identity, {"mesh": obj.data, "targets": {},
                                             "objects": objects, "scenes": scenes})
        group["targets"][obj.as_pointer()] = obj
    return list(groups.values())


def object_names(objects):
    return ", ".join(json.dumps(obj.name, ensure_ascii=False)
                     for obj in sorted(objects, key=lambda obj: obj.name.casefold()))


def shared_mesh_message(group):
    return (f'Shared mesh {group["mesh"].name!r}: rule targets {object_names(group["targets"].values())}. '
            f'Objects sharing this mesh: {object_names(group["objects"])}. '
            f'Affected objects and scenes: {affected_scenes(group)}. '
            'Vertex groups and weights can change on all listed objects and in their scenes.')


def affected_scenes(group):
    return "; ".join(
        f'{json.dumps(obj.name, ensure_ascii=False)} in '
        f'{object_names(group["scenes"][obj.as_pointer()]) or "no scene (unlinked)"}'
        for obj in sorted(group["objects"], key=lambda obj: obj.name.casefold()))


def log_shared_meshes(settings, groups, status):
    settings.log.clear()
    settings.log_index = 0
    for group in groups:
        log_line(settings, "WARNING", shared_mesh_message(group))
    settings.status = status
    settings.show_log = True


def run_rules(operator, context, scope, apply, allow_shared_data=False):
    settings = context.scene.vgr_settings
    rules = scoped_rules(context.scene, scope)
    if not rules:
        operator.report({'WARNING'}, "No rules to run.")
        return {'CANCELLED'}
    settings.log.clear()
    settings.log_index = 0
    if scope == 'ALL':
        duplicate_targets = duplicate_rule_targets(rules, context.scene)
        if duplicate_targets:
            for obj in duplicate_targets:
                log_line(settings, "WARNING", f'{obj.name}: Multiple enabled rules target this object. Combine them or disable duplicates before running All.')
            settings.status = "No rules ran: duplicate enabled targets. Combine or disable the duplicate rules."
            settings.show_log = True
            operator.report({'WARNING'}, settings.status)
            return {'CANCELLED'}
        mesh_conflicts = conflicting_mesh_targets(rules, context.scene)
        if mesh_conflicts:
            settings.status = ("No rules ran: multiple enabled rules share mesh data. "
                               "Disable extra rules or use Preview Rule and Apply Rule one at a time.")
            settings.show_log = True
            for group in mesh_conflicts:
                message = mesh_conflict_message(group)
                log_line(settings, "WARNING", message)
                operator.report({'WARNING'}, message)
            return {'CANCELLED'}
    shared_groups = shared_mesh_groups(rules, context.scene)
    if shared_groups:
        log_shared_meshes(settings, shared_groups, "No rules ran: shared mesh data needs confirmation.")
        if apply and not allow_shared_data:
            operator.report({'WARNING'}, settings.status)
            return {'CANCELLED'}
    completed = deleted = assigned = 0
    warnings = len(shared_groups)
    for rule in rules:
        try:
            if rule.target is not None and not object_in_scene(rule.target, context.scene):
                raise ValueError(f'Target is outside executing scene {context.scene.name!r}; rule skipped. '
                                 'Link the object into this scene or choose a target here.')
            obj = target_object(rule, context.scene)
            if obj is None:
                raise ValueError(f'Object was not found in scene {context.scene.name!r}. Choose an object for this rule.')
            values = rule_dictionary(rule)
            plan = engine.make_plan(obj, values)
            descriptions = engine.describe_plan(plan)
            if apply:
                engine.apply_plan(plan)
            for kind, message in descriptions:
                log_line(settings, kind, message)
            completed += 1
            deleted += len(plan.delete_names)
            assigned += len(plan.assignments)
        except (ValueError, RuntimeError, KeyError, TypeError) as error:
            log_line(settings, "WARNING", f"{rule_name(rule, context.scene)}: {error}")
            warnings += 1
    verb = "Applied" if apply else "Previewed"
    settings.status = f"{verb} {completed} rule(s): {deleted} deletion(s), {assigned} assignment(s), {warnings} warning(s)."
    settings.show_log = True
    operator.report({'WARNING'} if warnings else {'INFO'}, settings.status)
    return {'FINISHED'}


class VGR_OT_preview(Operator):
    bl_idname = "vgr.preview"
    bl_label = "Preview Changes"
    bl_description = "Show deletions and assignments without modifying vertex groups"
    scope: EnumProperty(items=(('ACTIVE', "Active Rule", ""), ('ALL', "All Enabled Rules", "")))

    def execute(self, context):
        return run_rules(self, context, self.scope, False)


class VGR_OT_apply(Operator):
    bl_idname = "vgr.apply"
    bl_label = "Apply VG Rules"
    bl_description = "Delete matching groups and set all vertices in the assignment groups to weight 1; supports Undo"
    bl_options = {'REGISTER', 'UNDO'}
    scope: EnumProperty(items=(('ACTIVE', "Active Rule", ""), ('ALL', "All Enabled Rules", "")))
    allow_shared_data: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'},
                                   description="Explicitly allow changes affecting shared objects or multiple scenes")

    def invoke(self, context, event):
        # Each click needs a fresh decision; a previous confirmation is not reused.
        self.allow_shared_data = False
        rules = scoped_rules(context.scene, self.scope)
        if self.scope == 'ALL' and (duplicate_rule_targets(rules, context.scene)
                                   or conflicting_mesh_targets(rules, context.scene)):
            return self.execute(context)
        self._shared_groups = shared_mesh_groups(rules, context.scene)
        if not self._shared_groups:
            return self.execute(context)
        log_shared_meshes(context.scene.vgr_settings, self._shared_groups,
                          "Shared mesh data: choose Continue or Cancel. No rules have run.")
        # The dialog only executes the operator when its Continue button is used.
        self.allow_shared_data = True
        return context.window_manager.invoke_props_dialog(self, width=600,
                                                         title="Shared Mesh Data", confirm_text="Continue")

    def draw(self, context):
        layout = self.layout
        layout.label(text="These changes affect shared objects or multiple scenes.", icon='ERROR')
        for group in getattr(self, "_shared_groups", []):
            box = layout.box()
            for text in (f'Rule targets: {object_names(group["targets"].values())}',
                         f'Objects sharing this mesh: {object_names(group["objects"])}',
                         f'Affected scenes: {affected_scenes(group)}'):
                # Leave room for wide glyphs at smaller window sizes.
                for line in textwrap.wrap(text, width=40):
                    box.label(text=line)
        layout.label(text="Vertex groups and weights can change in all listed scenes.")
        layout.label(text="Continue to apply, or Cancel to leave them unchanged.")

    def cancel(self, context):
        self.allow_shared_data = False
        context.scene.vgr_settings.status = "No rules ran: shared mesh data application cancelled."

    def execute(self, context):
        return run_rules(self, context, self.scope, True, self.allow_shared_data)


class VGR_OT_import(Operator, ImportHelper):
    bl_idname = "vgr.import_rules"
    bl_label = "Import VG Rules"
    bl_description = "Replace the rules with a JSON preset or a literal OBJECT_RULES dictionary from a Python script; scripts are not executed"
    bl_options = {'REGISTER', 'UNDO'}
    filter_glob: StringProperty(default="*.json;*.py", options={'HIDDEN'})

    def execute(self, context):
        try:
            load_rules(context.scene, presets.read_rules(self.filepath))
        except (OSError, ValueError, SyntaxError, TypeError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, context.scene.vgr_settings.status)
        return {'FINISHED'}


class VGR_OT_export(Operator, ExportHelper):
    bl_idname = "vgr.export_rules"
    bl_label = "Export VG Rules"
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def execute(self, context):
        try:
            rules = export_rules(context.scene)
            presets.write_rules(self.filepath, rules)
        except (OSError, ValueError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, "Rules exported.")
        return {'FINISHED'}


class VGR_UL_objects(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        obj = target_object(item, context.scene)
        row.label(text=rule_name(item, context.scene), icon='MESH_DATA' if obj is not None else 'ERROR')
        row.label(text=f"{len(item.keep_patterns) + len(item.delete_patterns)} / {len(item.assignments)}")


class VGR_UL_patterns(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        split = row.split(factor=0.5)
        split.prop(item, "kind", text="")
        split.prop(item, "value", text="")


class VGR_UL_assignments(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "group_name", text="", icon='GROUP_VERTEX')
        row.label(text="1.0")


class VGR_UL_log(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        icons = {"WARNING": 'ERROR', "DELETE": 'X', "ASSIGN": 'GROUP_VERTEX'}
        layout.label(text=item.message, icon=icons.get(item.kind, 'INFO'))


def list_buttons(layout, list_name, include_add=True):
    column = layout.column(align=True)
    for action, icon in (("ADD", 'ADD'), ("REMOVE", 'REMOVE'), ("UP", 'TRIA_UP'), ("DOWN", 'TRIA_DOWN')):
        if action == "ADD" and not include_add:
            continue
        operator = column.operator("vgr.edit_list", text="", icon=icon)
        operator.list_name = list_name
        operator.action = action


def wrapped_labels(layout, text, region, icon=None, wide_text=False):
    if wide_text:
        # W and CJK object names need more room than ordinary prose. Results
        # keeps the full text; wrap conservatively so every name remains visible.
        character_width = 14 * bpy.context.preferences.system.ui_scale
        width = max(8, int((region.width - 45) / character_width)) if region else 40
    else:
        width = max(24, int((region.width - 45) / 7)) if region else 55
    column = layout.column(align=True)
    column.scale_y = 0.9
    for index, line in enumerate(textwrap.wrap(text, width=width)):
        if index == 0 and icon:
            column.label(text=line, icon=icon)
        else:
            column.label(text=line)


class VGR_PT_rules(Panel):
    bl_label = "VG Rules"
    bl_idname = "VGR_PT_rules"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "VG Rules"

    def draw(self, context):
        layout = self.layout
        initialize_scene(context.scene)
        settings = context.scene.vgr_settings
        layout.use_property_split = False
        row = layout.row(align=True)
        row.operator("vgr.import_rules", text="Import", icon='IMPORT')
        row.operator("vgr.export_rules", text="Export", icon='EXPORT')
        layout.separator()
        row = layout.row(align=True)
        row.operator("vgr.add_rule", text="Add Selected", icon='ADD').selected = True
        row.operator("vgr.add_rule", text="New Rule", icon='ADD').selected = False
        row = layout.row()
        row.template_list("VGR_UL_objects", "", settings, "rules", settings, "rule_index", rows=5)
        list_buttons(row, "RULE", include_add=False)

        rule = active_rule(context.scene)
        if rule is not None:
            layout.prop(rule, "target")
            if rule.target is None:
                layout.prop(rule, "object_name", text="Fallback Name")
            obj = target_object(rule, context.scene)
            if obj is None:
                if rule.target is not None:
                    message = f'Target is outside scene {context.scene.name!r}; this rule will be skipped. Link it here or choose a local mesh.'
                else:
                    message = ("The selected object is missing. Choose a mesh above or explicitly edit the fallback name."
                               if rule.target_was_set else "Object not found in this scene. Choose a mesh above.")
                wrapped_labels(layout, message, context.region, 'ERROR')
            elif obj.mode == 'EDIT' or obj.data.is_editmode:
                wrapped_labels(layout, "Switch the target and any objects sharing its mesh to Object Mode.", context.region, 'ERROR')

            box = layout.box()
            box.label(text="Keep Rules", icon='LOCKED')
            box.prop(rule, "keep_case_sensitive")
            row = box.row()
            row.template_list("VGR_UL_patterns", "keep", rule, "keep_patterns", rule, "keep_pattern_index", rows=3)
            list_buttons(row, "KEEP")
            wrapped_labels(box, "Any Keep match overrides all Delete rules.", context.region)

            box = layout.box()
            box.label(text="Delete Rules", icon='TRASH')
            box.prop(rule, "delete_case_sensitive")
            row = box.row()
            row.template_list("VGR_UL_patterns", "delete", rule, "delete_patterns", rule, "delete_pattern_index", rows=3)
            list_buttons(row, "DELETE")
            wrapped_labels(box, "Only explicit matches delete groups.", context.region)

            box = layout.box()
            box.label(text="Full Weights - All Vertices", icon='GROUP_VERTEX')
            row = box.row()
            row.template_list("VGR_UL_assignments", "", rule, "assignments", rule, "assignment_index", rows=2)
            list_buttons(row, "ASSIGNMENT")
            if 0 <= rule.assignment_index < len(rule.assignments):
                entry = rule.assignments[rule.assignment_index]
                if obj is not None:
                    box.prop_search(entry, "group_name", obj, "vertex_groups", text="Group", results_are_suggestions=True)
                else:
                    box.prop(entry, "group_name")
                box.prop(entry, "side")
                box.prop(entry, "mirror")
                if entry.mirror:
                    wrapped_labels(box, "Empties the opposite source group.", context.region)
            wrapped_labels(box, "Creates missing groups. All vertices = 1.0, after cleanup.", context.region)

            row = layout.row(align=True)
            row.operator("vgr.preview", text="Preview Rule", icon='VIEWZOOM').scope = 'ACTIVE'
            row.operator("vgr.apply", text="Apply Rule", icon='CHECKMARK').scope = 'ACTIVE'

        row = layout.row(align=True)
        row.enabled = bool(settings.rules)
        row.operator("vgr.preview", text="Preview All", icon='VIEWZOOM').scope = 'ALL'
        row.operator("vgr.apply", text="Apply All", icon='CHECKMARK').scope = 'ALL'
        wrapped_labels(layout, settings.status, context.region)
        layout.prop(settings, "show_log", text="Results", icon='TRIA_DOWN' if settings.show_log else 'TRIA_RIGHT', emboss=False)
        if settings.show_log and settings.log:
            layout.template_list("VGR_UL_log", "", settings, "log", settings, "log_index", rows=4)
            if 0 <= settings.log_index < len(settings.log):
                line = settings.log[settings.log_index]
                wrapped_labels(layout, line.message, context.region, wide_text=line.kind == "WARNING")


def initialize_scene(scene):
    if not scene.vgr_settings.initialized:
        if not scene.vgr_settings.rules:
            load_rules(scene, {})
        else:
            scene.vgr_settings.initialized = True
    for rule in scene.vgr_settings.rules:
        if rule.target is not None:
            update_rule_target(rule, None)
        split_legacy_patterns(rule)


@persistent
def initialize_loaded_scenes(_):
    # Other scenes initialize when their UI or operators are used.
    scene = getattr(bpy.context, "scene", None)
    if scene is not None:
        initialize_scene(scene)


def initialize_pending_scenes():
    # Blender restricts data access while an add-on's register() runs.
    # Initialize only once that enable step has finished.
    if owns_scene_property():
        initialize_loaded_scenes(None)
    return None


CLASSES = (
    VGR_Pattern, VGR_KeepPattern, VGR_DeletePattern, VGR_Assignment,
    VGR_ObjectRule, VGR_LogLine, VGR_Settings,
    VGR_OT_add_rule, VGR_OT_edit_list, VGR_OT_preview,
    VGR_OT_apply, VGR_OT_import, VGR_OT_export,
    VGR_UL_objects, VGR_UL_patterns, VGR_UL_assignments, VGR_UL_log, VGR_PT_rules,
)


_registered_classes = []
_scene_property = None
_owns_handler = False
_owns_timer = False


def registered_class(cls):
    base = next(base for base in (PropertyGroup, Operator, UIList, Panel) if issubclass(cls, base))
    identifier = getattr(cls, "bl_idname", cls.__name__)
    if issubclass(cls, Operator):
        prefix, name = identifier.split(".", 1)
        identifier = f"{prefix.upper()}_OT_{name}"
    return base.bl_rna_get_subclass_py(identifier, None)


def owns_scene_property():
    prop = bpy.types.Scene.bl_rna.properties.get("vgr_settings")
    return (_scene_property is not None and prop is not None and prop.type == 'POINTER'
            and prop.as_pointer() == _scene_property and registered_class(VGR_Settings) is VGR_Settings
            and prop.fixed_type == VGR_Settings.bl_rna)


def register():
    global _scene_property, _owns_handler, _owns_timer
    if (_registered_classes or hasattr(bpy.types.Scene, "vgr_settings")
            or any(registered_class(cls) is not None for cls in CLASSES)
            or initialize_loaded_scenes in bpy.app.handlers.load_post
            or bpy.app.timers.is_registered(initialize_pending_scenes)):
        raise RuntimeError("VG Rules installation conflicts with already registered resources. "
                           "Disable the other installation and restart Blender before enabling this one.")
    try:
        for cls in CLASSES:
            _registered_classes.append(cls)
            bpy.utils.register_class(cls)
        bpy.types.Scene.vgr_settings = PointerProperty(type=VGR_Settings)
        _scene_property = bpy.types.Scene.bl_rna.properties["vgr_settings"].as_pointer()
        _owns_handler = True
        bpy.app.handlers.load_post.append(initialize_loaded_scenes)
        _owns_timer = True
        # Defer data changes until Blender has finished enabling the add-on.
        bpy.app.timers.register(initialize_pending_scenes, first_interval=0.0)
    except Exception:
        unregister()
        raise


def unregister():
    global _scene_property, _owns_handler, _owns_timer
    errors = []
    try:
        if _owns_timer and bpy.app.timers.is_registered(initialize_pending_scenes):
            bpy.app.timers.unregister(initialize_pending_scenes)
        _owns_timer = False
    except Exception as error:
        errors.append(error)
    if _owns_handler:
        if initialize_loaded_scenes in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(initialize_loaded_scenes)
        _owns_handler = False
    try:
        if owns_scene_property():
            del bpy.types.Scene.vgr_settings
        _scene_property = None
    except Exception as error:
        errors.append(error)
    for cls in reversed(_registered_classes.copy()):
        try:
            if registered_class(cls) is cls:
                bpy.utils.unregister_class(cls)
            _registered_classes.remove(cls)
        except Exception as error:
            errors.append(error)
    if errors:
        raise RuntimeError(f"Could not unregister all owned VG Rules resources: {errors!r}")


if __name__ == "__main__":
    register()
