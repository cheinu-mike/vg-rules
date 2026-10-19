# Install VG Rules

Requires Blender **4.2 or later**. Version **0.1.3** is a development build for
testing. The final installers passed the submission-readiness checks; see
[CHANGELOG](../CHANGELOG.md) and the
[verification report](../submission/COMPLIANCE.md) for their scope. The published
release remains 0.1.2. Blender 5.2.0 on macOS Intel remains unsupported; no official
build exists.

## Extension package

1. Use the extension ZIP `vg_rules-0.1.3.zip` supplied with the development build, or
   [build it](../README.md#build). Keep it compressed. The extension builder writes
   `dist/blender_extensions/`; its output is separate from the Gumroad installer.
2. Open **Preferences > Get Extensions > top-right menu > Install from Disk**.
3. Select the ZIP and enable **VG Rules**.
4. In the 3D Viewport, press **N** and open **VG Rules**.

The installed folder contains `QUICK_START.txt`. The public [usage guide](usage.md)
covers the same workflow. This development build has not been submitted for platform review.

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
