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

"""Plan and apply VG Rules without changing Blender's selection."""

from dataclasses import dataclass

from mathutils import Vector

from . import regex_guard


KEEP_KEYS = ("keep_only_prefixes", "keep_exact", "keep_contains", "keep_suffixes", "keep_regex")
DELETE_KEYS = ("delete_exact", "delete_prefixes", "delete_contains", "delete_suffixes", "delete_regex")
PATTERN_KEYS = KEEP_KEYS + DELETE_KEYS
CASE_KEYS = ("keep_case_sensitive", "delete_case_sensitive")
# Blender's vertex-group name buffer includes one byte for the terminator.
GROUP_NAME_MAX_BYTES = 63


@dataclass
class Assignment:
    group_name: str
    opposite_name: str | None = None


@dataclass
class Plan:
    obj: object
    delete_names: list
    assignments: list
    vertex_count: int


class GroupFilters:
    def __init__(self, rules, section):
        self.section = section
        self.case_sensitive = rules.get(f"{section}_case_sensitive", False)
        prefix_key = "keep_only_prefixes" if section == "keep" else "delete_prefixes"
        self.literals = {}
        for match_type, key in (
            ("exact", f"{section}_exact"), ("prefix", prefix_key),
            ("contains", f"{section}_contains"), ("suffix", f"{section}_suffixes"),
        ):
            self.literals[match_type] = tuple(
                value if self.case_sensitive else value.lower() for value in rules.get(key, [])
            )
        self.regex = regex_guard.compile_patterns(rules.get(f"{section}_regex", []),
                                                  self.case_sensitive, section)

    def literal_matches(self, name):
        literal_name = name if self.case_sensitive else name.lower()
        return (
            literal_name in self.literals["exact"]
            or literal_name.startswith(self.literals["prefix"])
            or any(value in literal_name for value in self.literals["contains"])
            or literal_name.endswith(self.literals["suffix"])
        )

    def matches(self, name):
        if self.literal_matches(name):
            return True
        if self.section == "keep":
            return not regex_guard.match_groups(self.regex, [], (name,), ((False, True),))[0]
        return regex_guard.match_groups([], self.regex, (name,), ((False, False),))[0]


class RuleMatcher:
    def __init__(self, rules):
        # Validate every expression before matching, even if a Keep filter wins.
        self.keep = GroupFilters(rules, "keep")
        self.delete = GroupFilters(rules, "delete")

    def should_delete(self, name):
        return self.deletion_matches((name,))[0]

    def deletion_matches(self, names):
        # Match the whole rule under one worker deadline before any mesh mutation.
        names = tuple(names)
        literals = tuple((self.keep.literal_matches(name), self.delete.literal_matches(name))
                         for name in names)
        return regex_guard.match_groups(self.keep.regex, self.delete.regex, names, literals)


def should_delete_group(name, rules):
    return RuleMatcher(rules).should_delete(name)


def validate_assignment_name(group_name, side=None):
    if not group_name.strip():
        raise ValueError("Enter a vertex group name for every assignment.")
    if "\0" in group_name:
        raise ValueError("Vertex group names cannot contain a null character.")
    final_name = group_name
    if side is not None:
        base_name = group_name[:-2] if group_name.endswith((".L", ".R")) else group_name
        # Both resolved sides, and the opposite mirror name, use two bytes.
        final_name = f"{base_name}.L"
    byte_count = len(final_name.encode("utf-8"))
    if byte_count > GROUP_NAME_MAX_BYTES:
        suffix_note = " including the .L/.R suffix" if side is not None else ""
        raise ValueError(f'Vertex group name {group_name!r} needs {byte_count} UTF-8 bytes{suffix_note}; Blender allows {GROUP_NAME_MAX_BYTES}. Shorten the name.')


def detect_group_side(obj, base_name):
    if not obj.data.vertices:
        raise ValueError(f'Cannot detect the side of "{base_name}" on an empty mesh.')
    center = sum((vertex.co for vertex in obj.data.vertices), Vector()) / len(obj.data.vertices)
    armature = obj.find_armature()
    left = armature.data.bones.get(f"{base_name}.L") if armature else None
    right = armature.data.bones.get(f"{base_name}.R") if armature else None
    if left is not None and right is not None:
        try:
            center = armature.matrix_world.inverted() @ obj.matrix_world @ center
        except ValueError:
            raise ValueError("The armature has a zero-scale transform; choose Left or Right.") from None
        difference = (center - left.head_local).length_squared - (center - right.head_local).length_squared
        if abs(difference) > 1e-12:
            return "L" if difference < 0 else "R"
    else:
        mirror = next((modifier for modifier in obj.modifiers
                       if modifier.type == 'MIRROR' and modifier.use_axis[0]), None)
        if mirror is None:
            raise ValueError(f'Auto side for "{base_name}" needs matching bones or an X Mirror. Choose Left or Right.')
        reference = mirror.mirror_object if mirror.mirror_object is not None else obj
        try:
            center_x = (reference.matrix_world.inverted() @ obj.matrix_world @ center).x
        except ValueError:
            raise ValueError("The mirror reference has a zero-scale transform; choose Left or Right.") from None
        if abs(center_x) > 1e-6:
            return "L" if center_x > 0 else "R"
    raise ValueError(f'The side of "{base_name}" is ambiguous. Choose Left or Right.')


def make_plan(obj, rules):
    if obj is None:
        raise ValueError("Object was not found. Choose an object for this rule.")
    if obj.type != 'MESH':
        raise ValueError("The target must be a mesh object.")
    if obj.mode == 'EDIT' or obj.data.is_editmode:
        raise ValueError("Switch the target and any objects sharing its mesh to Object Mode first.")
    if not obj.is_editable or not obj.data.is_editable:
        raise ValueError("The target or its mesh is read-only.")

    matcher = RuleMatcher(rules)
    assignments = []
    for entry in rules.get("assign_all_vertices", []):
        settings = {"group": entry} if isinstance(entry, str) else entry
        group_name = settings["group"]
        side = settings.get("side")
        validate_assignment_name(group_name, side)
        if side is not None:
            base_name = group_name[:-2] if group_name.endswith((".L", ".R")) else group_name
            side = side.upper()
            if side == "AUTO":
                side = detect_group_side(obj, base_name)
            if side not in {"L", "R"}:
                raise ValueError('Side must be "AUTO", "L", or "R".')
            group_name = f"{base_name}.{side}"
        opposite_name = None
        if settings.get("mirror", False):
            if not group_name.endswith((".L", ".R")):
                raise ValueError(f'Mirror assignment for "{group_name}" needs a .L/.R suffix or a side setting.')
            if not any(modifier.type == 'MIRROR' for modifier in obj.modifiers):
                raise ValueError("The target needs a Mirror modifier for mirrored assignments.")
            opposite_name = f'{group_name[:-2]}.{"R" if group_name.endswith(".L") else "L"}'
        assignments.append(Assignment(group_name, opposite_name))

    targets = {assignment.group_name for assignment in assignments}
    for assignment in assignments:
        if assignment.opposite_name in targets:
            raise ValueError(f'"{assignment.opposite_name}" cannot be both assigned and emptied for mirroring in this rule.')
    names = tuple(group.name for group in obj.vertex_groups)
    delete_names = [name for name, delete in zip(names, matcher.deletion_matches(names)) if delete]
    return Plan(obj, delete_names, assignments, len(obj.data.vertices))


def describe_plan(plan):
    lines = [("INFO", f"{plan.obj.name}: {len(plan.delete_names)} group(s) to delete; {len(plan.assignments)} full-weight assignment(s).")]
    lines.extend(("DELETE", f"{plan.obj.name}: delete {name}") for name in plan.delete_names)
    for assignment in plan.assignments:
        lines.append(("ASSIGN", f"{plan.obj.name}: {assignment.group_name} = 1.0 on all {plan.vertex_count} vertices (create if missing)."))
        if assignment.opposite_name is not None:
            lines.append(("INFO", f"{plan.obj.name}: empty {assignment.opposite_name} and enable Mirror vertex groups."))
    return lines


def apply_plan(plan):
    obj = plan.obj
    for name in plan.delete_names:
        group = obj.vertex_groups.get(name)
        if group is not None:
            obj.vertex_groups.remove(group)
    indices = [vertex.index for vertex in obj.data.vertices]
    for assignment in plan.assignments:
        group = obj.vertex_groups.get(assignment.group_name)
        if group is None:
            group = obj.vertex_groups.new(name=assignment.group_name)
        if assignment.opposite_name is not None:
            opposite = obj.vertex_groups.get(assignment.opposite_name)
            if opposite is None:
                opposite = obj.vertex_groups.new(name=assignment.opposite_name)
            if indices:
                opposite.remove(indices)
            for modifier in obj.modifiers:
                if modifier.type == 'MIRROR':
                    modifier.use_mirror_vertex_groups = True
        if indices:
            group.add(indices, 1.0, 'REPLACE')
        obj.vertex_groups.active_index = group.index
