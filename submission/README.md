# VG Rules submission materials

Prepared for version **0.1.2**. Upload the extension ZIP built under
`dist/blender_extensions/` with these separate listing materials. The package
has not yet been submitted for platform review.

| Material | Use |
| --- | --- |
| [LISTING.md](LISTING.md) | Public description, included features, limitations, installation and support links |
| [images/thumbnail.png](images/thumbnail.png) | Existing cube icon, reused unchanged; 1920 × 1920 PNG |
| [images/preview.png](images/preview.png) | Genuine Preview Rule capture from the installed extension |
| [images/apply.png](images/apply.png) | Genuine Apply Rule result from the same synthetic scene |
| [capture.json](capture.json) | Packaged-extension SHA-256, Blender version, preset, before/after weights and image hashes |
| [COMPLIANCE.md](COMPLIANCE.md) | Actual platform and GUI results, release scope and final archive hashes |
| [gui-results.json](gui-results.json) | Native warning, Cancel/Continue, Undo and migration evidence on three Windows versions |

Read the compliance report before submitting. All eleven supported hosted
platform/version pairs and the local GUI checks must pass against the final ZIP.
Blender 5.2.0 on Intel macOS is unsupported; both pinned 4.2 versions cover Intel.
Upload and moderation follow preparation and verification.

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

The four runtime Python modules carry `Copyright (C) 2026 Blank Glyph` and
`SPDX-License-Identifier: GPL-3.0-or-later`. The manifest credits `2026 Blank Glyph`
and the same GPL license; its maintainer agrees with `bl_info`'s author.
`NOTICE.txt` supplies the copyright and warranty notice; `COPYING.txt` contains
the complete GPL text. No third-party runtime modules or bundled media are used.

The thumbnail is the existing project-supplied cube icon, reused unchanged for
the listing. No new CC0 grant is asserted for that supplied image. The screenshots
use only generated geometry and the application's own interface. These separate
submission images are excluded from both installers; no fonts or binary assets
are bundled. The extension ZIP contains only four Python modules, the manifest,
quick start and two license/notice text files.

Any future assets included inside an extension must have documented CC0 rights
and appropriate credits before packaging, as required by the
[platform terms](https://extensions.blender.org/terms-of-service/). Keep the name
VG Rules, avoid the Blender logo in submission images, and keep advertising out
of the application. Support goes to
[GitHub Issues](https://github.com/cheinu-mike/vg-rules/issues).
