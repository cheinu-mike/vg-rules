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

"""Run regular-expression searches in a disposable, time-limited process."""

from functools import lru_cache
import json
import os
from pathlib import Path
import re
import subprocess
import sys


MATCH_TIMEOUT_SECONDS = 1.0
MAX_PATTERN_CHARACTERS = 4096
MAX_PATTERNS_PER_SECTION = 64
_MAX_CACHED_GROUPS = 4096
_MAX_CACHED_CHARACTERS = 65536


def compile_patterns(expressions, case_sensitive, section):
    expressions = tuple(expressions)
    prefix = f"Invalid {section.title()} Regex"
    if len(expressions) > MAX_PATTERNS_PER_SECTION:
        raise ValueError(f"{prefix}: At most {MAX_PATTERNS_PER_SECTION} patterns are allowed; shorten the list.")
    compiled = []
    for expression in expressions:
        if len(expression) > MAX_PATTERN_CHARACTERS:
            raise ValueError(f"{prefix}: Patterns allow at most {MAX_PATTERN_CHARACTERS} characters; shorten the expression.")
        try:
            compiled.append(re.compile(expression, 0 if case_sensitive else re.IGNORECASE))
        except (re.error, OverflowError, RecursionError) as error:
            if isinstance(error, OverflowError):
                reason = "Repetition count is too large; reduce its bound."
            elif isinstance(error, RecursionError):
                reason = "Pattern nesting is too deep; simplify the expression."
            else:
                reason = str(error)
            pattern_text = repr(expression)
            if len(pattern_text) > 160:
                pattern_text = pattern_text[:157] + "..."
            raise ValueError(f"{prefix}: {reason} Pattern: {pattern_text}") from None
    return compiled


def _label(keep, delete):
    section = "Keep/Delete" if keep and delete else "Keep" if keep else "Delete"
    return f"{section} Regex"


def _failure(label, reason):
    return ValueError(f"{label}: {reason}; simplify the expression or use literal filters.")


def _bundled_interpreter(label):
    # This is only called inside Blender, never by the standalone worker.
    import bpy

    executable = sys.executable
    if not isinstance(executable, str) or not executable:
        raise _failure(label, "Safe matching needs Blender's Python interpreter")
    try:
        interpreter = Path(executable).resolve()
        resource = Path(bpy.utils.resource_path('LOCAL')).resolve()
        python = (resource / "python").resolve()
        available = interpreter.is_file()
    except (OSError, ValueError, RuntimeError):
        raise _failure(label, "Safe matching could not locate Blender's Python interpreter") from None
    if (not available or not python.is_relative_to(resource) or not interpreter.is_relative_to(python)
            or re.fullmatch(r"python(?:\d+(?:\.\d+)*)?(?:t|w)?(?:\.exe)?", interpreter.name, re.IGNORECASE) is None):
        raise _failure(label, "Safe matching needs Blender's Python interpreter")
    return interpreter


def _run_matches(keep, delete, names, literals):
    label = _label(keep, delete)
    interpreter = _bundled_interpreter(label)
    payload = json.dumps({"keep": keep, "delete": delete, "names": names, "literals": literals})
    options = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace",
               "timeout": MATCH_TIMEOUT_SECONDS}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        # run() kills and waits for the child on timeout. No regex search runs here.
        result = subprocess.run([str(interpreter), "-I", "-B", str(_worker_path(label))],
                                input=payload, **options)
    except subprocess.TimeoutExpired:
        raise _failure(label, f"Matching exceeded the {MATCH_TIMEOUT_SECONDS:g}-second time limit") from None
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise _failure(label, "Safe matching worker could not run") from None
    if result.returncode != 0:
        raise _failure(label, "Safe matching worker failed")
    if not isinstance(result.stdout, str) or len(result.stdout) > 8 * len(names) + 64:
        raise _failure(label, "Safe matching worker returned invalid results")
    try:
        decisions = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise _failure(label, "Safe matching worker returned invalid results") from None
    if not isinstance(decisions, list) or len(decisions) != len(names) or any(type(value) is not bool for value in decisions):
        raise _failure(label, "Safe matching worker returned invalid results")
    return tuple(decisions)


@lru_cache(maxsize=128)
def _cached_matches(keep, delete, names, literals):
    return _run_matches(keep, delete, names, literals)


def _worker_path(label):
    try:
        path = Path(__file__).resolve()
        if path.is_file():
            return path
    except (OSError, ValueError, RuntimeError):
        pass
    raise _failure(label, "Safe matching worker is unavailable")


def match_groups(keep_patterns, delete_patterns, names, literal_matches):
    keep = tuple((pattern.pattern, int(pattern.flags)) for pattern in keep_patterns)
    delete = tuple((pattern.pattern, int(pattern.flags)) for pattern in delete_patterns)
    names = tuple(names)
    literals = tuple(tuple(pair) for pair in literal_matches)
    label = _label(keep, delete)
    if len(names) != len(literals) or any(not isinstance(name, str) for name in names):
        raise _failure(label, "Invalid group matching input")
    if any(len(pair) != 2 or any(type(value) is not bool for value in pair) for pair in literals):
        raise _failure(label, "Invalid literal matching input")
    if not keep and not delete:
        return tuple(not protected and selected for protected, selected in literals)
    # A regex rule must not mutate data with unavailable worker resources,
    # even if its matches would be cached or all names are literal-protected.
    _bundled_interpreter(label)
    _worker_path(label)
    if not names or all(protected for protected, _ in literals):
        return (False,) * len(names)
    character_count = sum(len(name) for name in names) + sum(len(pattern) for pattern, _ in (*keep, *delete))
    if len(names) > _MAX_CACHED_GROUPS or character_count > _MAX_CACHED_CHARACTERS:
        return _run_matches(keep, delete, names, literals)
    return _cached_matches(keep, delete, names, literals)


def _worker():
    request = json.load(sys.stdin)
    keep = [re.compile(expression, flags) for expression, flags in request["keep"]]
    delete = [re.compile(expression, flags) for expression, flags in request["delete"]]
    decisions = []
    for name, (protected, selected) in zip(request["names"], request["literals"]):
        protected = protected or any(pattern.search(name) is not None for pattern in keep)
        decisions.append(not protected and (selected or any(pattern.search(name) is not None for pattern in delete)))
    print(json.dumps(decisions, separators=(",", ":")))


if __name__ == "__main__":
    _worker()
