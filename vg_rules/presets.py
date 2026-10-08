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

"""Read literal OBJECT_RULES from scripts without executing them."""

import ast
import json
from pathlib import Path

from .engine import CASE_KEYS, PATTERN_KEYS, RuleMatcher, validate_assignment_name


def validate_utf8_strings(value, location="Rules"):
    """Reject text Blender cannot store, including text in unsupported fields."""
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError(f"{location} contains text that cannot be encoded as UTF-8 (unpaired Unicode surrogate).") from None
    elif isinstance(value, dict):
        for key, item in value.items():
            validate_utf8_strings(key, f"{location} key")
            validate_utf8_strings(item, f"{location}[{key!r}]")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            validate_utf8_strings(item, f"{location}[{index}]")


def validate_rules(rules):
    if not isinstance(rules, dict):
        raise ValueError("Rules must be a dictionary keyed by object name.")
    validate_utf8_strings(rules)
    for object_name, settings in rules.items():
        if not isinstance(object_name, str) or not object_name.strip():
            raise ValueError("Every rule needs a nonempty object name.")
        if "\0" in object_name:
            raise ValueError("Object names cannot contain a null character.")
        if not isinstance(settings, dict):
            raise ValueError(f'Rules for "{object_name}" must be a dictionary.')
        unknown = set(settings) - set(PATTERN_KEYS) - set(CASE_KEYS) - {"assign_all_vertices", "enabled"}
        if unknown:
            raise ValueError(f'Unsupported rule for "{object_name}": {", ".join(sorted(unknown))}')
        if "enabled" in settings and not isinstance(settings["enabled"], bool):
            raise ValueError(f'Enabled for "{object_name}" must be true or false.')
        for key in CASE_KEYS:
            if key in settings and not isinstance(settings[key], bool):
                raise ValueError(f'"{key}" for "{object_name}" must be true or false.')
        for key in PATTERN_KEYS:
            values = settings.get(key, [])
            if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f'"{key}" for "{object_name}" must be a list of nonempty strings.')
            if any("\0" in value for value in values):
                raise ValueError(f'"{key}" for "{object_name}" cannot contain a null character.')
        try:
            RuleMatcher(settings)
        except ValueError as error:
            raise ValueError(f'{object_name}: {error}') from None
        assignments = settings.get("assign_all_vertices", [])
        if not isinstance(assignments, list):
            raise ValueError(f'Assignments for "{object_name}" must be a list.')
        for entry in assignments:
            entry = {"group": entry} if isinstance(entry, str) else entry
            if not isinstance(entry, dict) or set(entry) - {"group", "side", "mirror"}:
                raise ValueError(f'Invalid assignment for "{object_name}".')
            if not isinstance(entry.get("group"), str) or not entry["group"].strip():
                raise ValueError(f'An assignment for "{object_name}" needs a group name.')
            if entry.get("side") is not None and entry["side"] not in {"AUTO", "L", "R"}:
                raise ValueError(f'Invalid assignment side for "{object_name}".')
            if "mirror" in entry and not isinstance(entry["mirror"], bool):
                raise ValueError(f'Mirror for "{object_name}" must be true or false.')
            try:
                validate_assignment_name(entry["group"], entry.get("side"))
            except ValueError as error:
                raise ValueError(f'{object_name}: {error}') from None
    return rules


def read_rules(filepath):
    filepath = Path(filepath)
    source = filepath.read_text(encoding="utf-8-sig")
    if filepath.suffix.lower() == ".py":
        tree = ast.parse(source, filename=str(filepath))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "OBJECT_RULES" for target in node.targets):
                try:
                    rules = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    raise ValueError("OBJECT_RULES must be a literal dictionary.") from None
                return validate_rules(rules)
        raise ValueError("The script has no literal OBJECT_RULES dictionary.")
    return validate_rules(json.loads(source))
