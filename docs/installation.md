# Install VG Rules

Requires Blender **4.2.1 or later**. Version **0.1.4** is a development build for
testing. The revised candidate requires new submission-readiness checks against
its final installer hashes; see [CHANGELOG](../CHANGELOG.md). The existing
[verification report](../submission/COMPLIANCE.md) covers earlier archives. The published
release remains 0.1.2. Blender 5.2.0 on macOS Intel remains unsupported; no official
build exists.

The rebuilt 0.1.4 packages were tested locally on **Windows x64 with Blender
5.3.0** on 2026-11-16. Headless source/installed-extension suites, installer
lifecycle and native GUI checks passed. See the [5.3 report](blender-5.3.md).
This does not establish 5.3 compatibility on Linux or macOS.

The local 0.1.4 ZIPs rebuilt on 2026-11-15 include the standalone worker and
list-row selection fixes, plus Delete Prefix as the first and default Delete
match type. Earlier 0.1.4 ZIPs are preserved under `dist/history/0.1.4/`.
Compare the hashes in
[CHANGELOG](../CHANGELOG.md); the version number alone does not distinguish
these source revisions.

## Extension package

1. [Build the extension ZIP](../README.md#build) from the current source, or use a
   ZIP verified against that source. Keep `vg_rules-0.1.4.zip` compressed.
   The extension builder writes `dist/blender_extensions/`; its output is separate
   from the Gumroad installer.
2. Open **Preferences > Get Extensions > top-right menu > Install from Disk**.
3. Select the ZIP and enable **VG Rules**.
4. In the 3D Viewport, press **N** and open **VG Rules**.

The installed folder contains `QUICK_START.txt`. The public [usage guide](usage.md)
covers the same workflow. This development build has not been submitted for platform review.
Keep all installed files together, including `regex_worker.py`. If the worker is
missing, reinstall the complete ZIP.

## Gumroad add-on package

The separate customer ZIP is under `dist/`. Install it through **Preferences >
Add-ons > menu > Install from Disk**, then enable VG Rules. Its source keeps
`bl_info`; the extension uses `blender_manifest.toml`. Both have the same runtime.
Use one installation at a time.

## Updates

Follow [updates and switching installers](migration.md), including a **full Blender restart**.
Save a `.blend` copy and export a JSON backup before changing installations.
Disable and remove the previous VG Rules installation before enabling its replacement.

## Permissions and support

The only extension permission is file access for importing/exporting presets.
The runtime needs no network connection, external dependency, registration or key.
Read-only installation directories are supported; export to a writable user folder.

For installation problems, follow [troubleshooting](troubleshooting.md), then
report through [GitHub Issues](https://github.com/cheinu-mike/vg-rules/issues).
