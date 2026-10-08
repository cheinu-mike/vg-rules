# VG Rules

Clean up vertex groups and assign full weights with reusable rules in Blender.
This is the canonical development repository for VG Rules.

- Protect and delete groups by exact name, prefix, suffix, contained text or regex.
- Preview a rule or all enabled rules before applying changes.
- Assign all vertices to groups at weight 1.0, with optional side and Mirror settings.
- Save rules in the `.blend` file and exchange JSON presets.

Version **0.1.0**. Requires Blender **4.2 or later**. Tested on Windows with
Blender **4.2.23 LTS** and **5.2.0 LTS**; macOS and Linux verification is pending.
The extension package has not yet been submitted for Blender platform review.

## Installation

Install the extension ZIP from Preferences > Get Extensions > menu > Install
from Disk. Keep it compressed, enable VG Rules, then press **N** in the 3D
Viewport and open **VG Rules**.

The separate Gumroad add-on ZIP installs through Preferences > Add-ons > menu >
Install from Disk. Use one VG Rules installation at a time. Before replacing an
installation, save your `.blend`, export a JSON backup, disable/remove the old
installation, install the replacement, and fully restart Blender.

## First rule

1. In a new General scene, select the Cube in Object Mode and click **Add Selected**.
2. Leave Keep and Delete empty. Under **Full Weights - All Vertices**, add an
   assignment, choose **Exact Name**, and enter `DemoWeight`.
3. **Preview Rule** should report zero deletions and one assignment without
   changing the mesh. **Apply Rule** creates the group with weight 1.0 on all vertices.

Save a separate `.blend` copy before cleanup or weight changes. Keep matches
override every Delete match; Keep alone deletes nothing. Matching is case
insensitive unless the corresponding section's **Case Sensitive** checkbox is set.

Full Weights replaces the assigned group's weights on every vertex, including
hidden and unselected vertices and kept or locked groups. Mirror Weights creates
and empties the opposite `.L`/`.R` group and enables vertex-group mirroring on
existing Mirror modifiers. It does not apply those modifiers.

Preview lists planned changes. Apply asks for confirmation when mesh data is
shared; Cancel leaves the batch untouched. All stops when enabled rules target
the same object or different objects sharing one mesh. Invalid rules are skipped
with warnings, while other valid rules may run. Review Results and use Undo or
your saved copy to recover.

Regex uses Python syntax and a one-second worker deadline per rule, with up to
64 patterns per section and 4096 characters per pattern. Slow or invalid regex
skips the affected rule before changes. Vertex group names allow at most 63 UTF-8
bytes, including a `.L`/`.R` suffix.

Import replaces the rule list after validation and accepts JSON or a Python file
containing a literal `OBJECT_RULES` dictionary. Python files are read without
executing their code. Export a backup before importing.

## Build

Use Python **3.11 or newer**. The add-on requires no additional Python packages.

```sh
python build_addon.py
python build_extension.py --blender /path/to/blender
```

On Windows, quote the full executable path, for example:

```powershell
python build_extension.py --blender "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
```

The builders produce:

- `dist/vg_rules-0.1.0.zip`: the Gumroad add-on, including `bl_info`.
- `dist/blender_extensions/vg_rules-0.1.0.zip`: the extension, including
  `blender_manifest.toml` and omitting `bl_info`.

Both packages use the same runtime code. Filenames derive from `bl_info`, and
the extension build rejects inconsistent manifest metadata. Both builders verify
their ZIP contents before replacing output. The extension also requires Blender's
official validation to succeed; missing Blender, validation failures or timeouts
leave any previous ZIP intact. Generated packages are not committed.

## Checks

```sh
python -m unittest discover -s tests -p "test_*.py"
python tests/run_blender.py --blender /path/to/blender
```

Build the extension first. The Blender runner uses fresh offline profiles and
generated meshes, presets and scenes. Output stays in ignored `tests/.artifacts/`.

## Support and license

Report problems through [GitHub Issues](https://github.com/cheinu-mike/vg-rules/issues).
Include OS, Blender and VG Rules versions, which package you installed, Results
text, and steps describing expected and actual behavior.

Copyright (C) 2026 Blank Glyph. Licensed under **GPL-3.0-or-later**. Editable
Python source, the copyright notice and complete GPL text are included in both
installers. See [LICENSE](LICENSE) and [NOTICE](vg_rules/NOTICE.txt).
