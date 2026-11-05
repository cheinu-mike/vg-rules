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

"""Standalone regex worker: execute as a child script, never import into Blender."""

import json
import re
import sys


def main():
    request = json.load(sys.stdin)
    keep = [re.compile(expression, flags) for expression, flags in request["keep"]]
    delete = [re.compile(expression, flags) for expression, flags in request["delete"]]
    decisions = []
    for name, (protected, selected) in zip(request["names"], request["literals"]):
        protected = protected or any(pattern.search(name) is not None for pattern in keep)
        decisions.append(not protected and (selected or any(pattern.search(name) is not None for pattern in delete)))
    print(json.dumps(decisions, separators=(",", ":")))


main()
