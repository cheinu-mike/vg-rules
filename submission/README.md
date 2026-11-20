# VG Rules submission materials

Prepared for version **0.1.4**, an unpublished development build. The published
release remains **0.1.2**. Upload the verified extension ZIP under
`dist/blender_extensions/` with these separate listing materials. The package
has not yet been submitted for platform review.

The resubmission candidate requires Blender **4.2.1 or later**. Both ZIPs came
from the [hosted verification run](https://github.com/cheinu-mike/vg-rules/actions/runs/44666038856).
All eleven hosted checks, three Windows GUI runs and the local release gate
passed for those exact installer hashes. See the [compliance report](COMPLIANCE.md).

The listing and bundled quick start link to the guides on the canonical `main`
branch.

| Material | Use |
| --- | --- |
| [LISTING.md](LISTING.md) | Public description, included features, limitations, installation and support links |
| [images/thumbnail.png](images/thumbnail.png) | Existing cube icon, reused unchanged; 1920 × 1920 PNG |
| [images/preview.png](images/preview.png) | Preview Rule from the installed final extension |
| [images/apply.png](images/apply.png) | Apply Rule from the same installed extension |
| [capture.json](capture.json) | Extension hash, synthetic scene results and screenshot hashes |
| [COMPLIANCE.md](COMPLIANCE.md) | Passing platform/GUI report with both final installer hashes |
| [compliance.json](compliance.json) | Machine-readable release-gate result |
| [verification-results.json](verification-results.json) | Eleven hosted stage records |
| [gui-results.json](gui-results.json) | Three Windows GUI records with checkpoint screenshot hashes |
| [QUICK_START.txt](QUICK_START.txt) | Rendered quick start extracted from the final extension ZIP |

Read the compliance report before submitting. All eleven supported hosted
platform/version pairs and the local GUI checks must pass against the final ZIP.
Blender 5.2.0 on Intel macOS is unsupported; both pinned 4.2 versions cover Intel.
Upload and moderation follow preparation and verification.
Historical 0.1.2 reports, results, listing materials and screenshots are preserved
under [history/0.1.2](history/0.1.2/ARCHIVE.md); they certify that older release only.

## Screenshot captions

**Preview:** A synthetic eight-vertex Demo Shell with an X Mirror modifier.
Keep protects `DEF-` groups and `cloth_pin`. Delete matches `MCH-` and `_backup`.
Preview reports two deletions, one full-weight assignment and zero warnings;
all original groups and 0.25 weights remain unchanged.

**Apply:** The same rule removes `MCH-temp` and `weights_backup`, assigns
`DEF-Demo.L` weight 1.0 on all eight source vertices, empties `DEF-Demo.R` and
enables Mirror vertex-group mirroring. `cloth_pin` retains its original weights.
The active group's weight colors show the actual before/after data.

The native 3D Viewport capture excludes Blender's global top bar and logo.
The geometry, rules and results are real; no external model or rendered mock UI
is used. Images show only functionality included in the packaged extension.

## Reproduce

Build the final extension first, then run with Python 3.11 or newer:

```sh
python build_extension.py --blender /path/to/blender
python submission/capture.py --blender /path/to/blender
```

The capture script starts its own offline Blender GUI session with a disposable
profile. It installs that ZIP into an extension namespace and checks installed
bytes against the archive. It checks Preview does not mutate the scene, verifies
Apply's weights and deletions, captures the editor directly, and quits that
session. Temporary profiles and logs stay in ignored `tests/.artifacts/`.
No scene binaries are committed. See the public [guides](../docs/installation.md).

## Copyright, credits and packaging

The five bundled Python files carry `Copyright (C) 2026 Blank Glyph` and
`SPDX-License-Identifier: GPL-3.0-or-later`. The manifest credits `2026 Blank Glyph`
and the same GPL license; its maintainer agrees with `bl_info`'s author.
`NOTICE.txt` supplies the copyright and warranty notice; `COPYING.txt` contains
the complete GPL text. No third-party runtime modules or bundled media are used.

The current source packages contain nine text files in the extension and seven
in the classic add-on. `regex_worker.py` is a required runtime script launched
directly by Blender's Python with `bpy.app.python_args`; normal add-on imports
do not execute it. It uses only the standard library and communicates with JSON.

The thumbnail is the existing project-supplied cube icon, reused unchanged for
the listing. No new CC0 grant is asserted for that supplied image. The screenshots
use only generated geometry and the application's own interface. These separate
submission images are excluded from both installers; no fonts or binary assets
are bundled. The extension ZIP contains only five Python files, the manifest,
quick start and two license/notice text files.

Any future assets included inside an extension must have documented CC0 rights
and appropriate credits before packaging, as required by the
[platform terms](https://extensions.blender.org/terms-of-service/). Keep the name
VG Rules, avoid the Blender logo in submission images, and keep advertising out
of the application. Support goes to
[GitHub Issues](https://github.com/cheinu-mike/vg-rules/issues).
