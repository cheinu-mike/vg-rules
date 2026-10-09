# VG Rules

Clean up vertex groups and assign full weights with rules.

VG Rules adds a 3D Viewport sidebar for reusable, object-specific vertex-group
cleanup and full-weight assignments. Start with your own meshes and rules;
Preview lists the intended changes before Apply.

## Included features

- Separate Keep and Delete lists with Exact, Prefix, Suffix, Contains and Python Regex.
  Matching ignores case unless you enable a section's Case Sensitive checkbox.
  Keep protects against all Delete filters; Keep alone deletes nothing.
- Preview Rule / Preview All without changing groups or weights, and Apply Rule /
  Apply All with Results counts and warnings. Rules can be enabled individually.
- Full Weights assigns 1.0 to every vertex, creates missing groups and replaces
  existing assigned-group weights, including kept/locked groups and hidden vertices.
- Exact, Left, Right and Auto Side assignments. Mirror Weights requires an existing
  Mirror modifier, empties the opposite source group and enables modifier vertex-group
  mirroring. It does not apply modifiers or build a complete rig.
- Rules saved in the `.blend`, plus JSON import/export and nonexecuting import of
  literal `OBJECT_RULES` dictionaries from Python files. Import replaces the list.
- Targets resolved within the executing scene. Saved outside-scene pointers are
  retained and their rules skipped with a warning.
- Confirmation for shared mesh users and objects linked into multiple scenes.
  The warning names affected objects and scenes; Cancel leaves the batch intact.

## Before Apply

Save a separate `.blend` copy. Full Weights overwrites existing weights on all vertices;
Keep does not protect against assignments. Mirror Weights empties the opposite source
group even when it is kept or locked. Review shared-data effects in every listed scene.
All blocks duplicate enabled targets and different enabled targets sharing a mesh;
invalid rules may be skipped while valid rules run. Leave Edit Mode on all shared users.

Regex limits: 4096 characters per pattern, 64 patterns per Keep/Delete section and
a one-second matching worker deadline per rule. Blender's bundled Python is required;
invalid, slow, missing or failed workers skip the affected rule before mutation.
Final group names allow 63 UTF-8 bytes including `.L`/`.R`.

## Installation and help

Requires Blender 4.2 or later. Install from Preferences > Get Extensions > menu >
Install from Disk, enable VG Rules, then open its 3D Viewport sidebar tab with N.
Use one installation at a time. Export JSON and save a `.blend` copy before updating
or migrating. **Fully quit and restart Blender after replacing an installation.**

[Installation](https://github.com/cheinu-mike/vg-rules/blob/main/docs/installation.md) ·
[Usage](https://github.com/cheinu-mike/vg-rules/blob/main/docs/usage.md) ·
[Migration](https://github.com/cheinu-mike/vg-rules/blob/main/docs/migration.md) ·
[Troubleshooting](https://github.com/cheinu-mike/vg-rules/blob/main/docs/troubleshooting.md) ·
[Support: GitHub Issues](https://github.com/cheinu-mike/vg-rules/issues)

Version 0.1.2 is verified on Windows with Blender 4.2.23 and 5.2.0. macOS/Linux
verification remains pending. The runtime needs only file permission for presets;
it has no external dependencies, network calls, registration requirement or custom updater.

Copyright (C) 2026 Blank Glyph. GPL-3.0-or-later; editable Python source is included.
