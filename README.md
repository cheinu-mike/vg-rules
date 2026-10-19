# VG Rules

Clean up vertex groups and assign full weights with reusable rules in Blender.
This is the canonical development repository for VG Rules.

- Protect and delete groups by exact name, prefix, suffix, contained text or regex.
- Preview a rule or all enabled rules before applying changes.
- Assign all vertices to groups at weight 1.0, with optional side and Mirror settings.
- Save rules in the `.blend` file and exchange JSON presets.

Development build **0.1.3**. Requires Blender **4.2 or later**. This build is for
testing and has not been published or submitted for Blender platform review.
The final 0.1.3 installers passed all eleven hosted platform/version combinations,
local Windows GUI checks and the submission-readiness gate. See
[CHANGELOG](CHANGELOG.md) and the hash-bound
[compliance report](submission/COMPLIANCE.md) for results and verification limits.
The published release remains 0.1.2; its submission evidence is preserved in
[history](submission/history/0.1.2/COMPLIANCE.md).
Blender 5.2.0 on macOS Intel remains unsupported because no official Intel build exists.

Public guides: [Installation](docs/installation.md), [Usage](docs/usage.md),
[Updates and switching installers](docs/migration.md), and [Troubleshooting](docs/troubleshooting.md).
Support is through [GitHub Issues](https://github.com/cheinu-mike/vg-rules/issues).

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

Imported names and executable targets resolve in the current scene. The picker
shows its meshes. If a saved target is outside that scene, its pointer remains
saved and the rule is skipped with a warning. Link it into this scene or choose
a local object to run the rule.

Full Weights replaces the assigned group's weights on every vertex, including
hidden and unselected vertices and kept or locked groups. Mirror Weights creates
and empties the opposite `.L`/`.R` group and enables vertex-group mirroring on
existing Mirror modifiers. It does not apply those modifiers.

Preview lists planned changes. Apply asks for confirmation when mesh data is
shared or one target object belongs to multiple scenes. The warning lists every
affected object and its scenes; Cancel leaves the batch untouched. All stops
when enabled rules target the same object or different objects sharing one mesh.
Invalid rules are skipped
with warnings, while other valid rules may run. Review Results and use Undo or
your saved copy to recover.

Regex uses Python syntax and a one-second worker deadline per rule, with up to
64 patterns per section and 4096 characters per pattern. Slow or invalid regex
skips the affected rule before changes. The worker uses Blender's bundled Python;
a missing interpreter or failed worker also skips the affected rule. Vertex
group names allow at most 63 UTF-8 bytes, including a `.L`/`.R` suffix.

Import replaces the rule list after validation and accepts JSON or a Python file
containing a literal `OBJECT_RULES` dictionary. Python files are read without
executing their code. Export a backup before importing.
Export writes atomically, preserving existing presets on failure, and refuses
destinations inside installed VG Rules directories, including disabled copies.
Runtime operation requires no write access to those directories. Disable and
remove the previous VG Rules installation before enabling its replacement.

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

- `dist/vg_rules-0.1.3.zip`: the Gumroad add-on, including `bl_info`.
- `dist/blender_extensions/vg_rules-0.1.3.zip`: the extension, including
  `blender_manifest.toml` and an extension-specific `QUICK_START.txt`, and
  omitting `bl_info`.

Both packages use the same runtime code. Filenames derive from `bl_info`, and
the extension build rejects inconsistent manifest metadata. Both builders verify
their ZIP contents before replacing output. The extension also requires Blender's
official validation to succeed; missing Blender, validation failures or timeouts
leave any previous ZIP intact. Generated packages are not committed.
The installers contain only editable Python, metadata, documentation and license
text. Submission images are kept separately in [submission/](submission/README.md).

## Checks

```sh
python -m unittest discover -s tests -p "test_*.py"
python tests/run_blender.py --blender /path/to/blender
```

Build both installers first. The runner uses temporary offline profiles and
generated meshes, presets and scenes. It runs the full source and installed ZIP
suites with enforced read-only permissions, then separate processes for installer switches,
update, restart and uninstall. GitHub Actions tests eleven required platform/version
pairs using one candidate archive. See [Verification](docs/verification.md), the
[archive-bound compliance report](submission/COMPLIANCE.md) and [CHANGELOG](CHANGELOG.md).
Missing, failed or stale results block submission readiness.

## Support and license

Report problems through [GitHub Issues](https://github.com/cheinu-mike/vg-rules/issues).
Include OS, Blender and VG Rules versions, which package you installed, Results
text, and steps describing expected and actual behavior.

Copyright (C) 2026 Blank Glyph. Licensed under **GPL-3.0-or-later**. Editable
Python source, the copyright notice and complete GPL text are included in both
installers. See [LICENSE](LICENSE) and [NOTICE](vg_rules/NOTICE.txt).

The prepared [listing text](submission/LISTING.md) and
[thumbnail and screenshots](submission/README.md) describe included functionality.
The screenshots are captured from the installed extension ZIP in a synthetic scene.
