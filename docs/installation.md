# Install VG Rules

Requires Blender **4.2 or later**. Version 0.1.2 is verified on Windows x64,
Linux x64 and macOS Apple Silicon with Blender 4.2.0, 4.2.23 and 5.2.0. macOS
Intel is verified on 4.2.0 and 4.2.23; 5.2.0 has no official Intel build and is
unsupported there. See the [verification report](../submission/COMPLIANCE.md).

## Extension package

1. Use the extension ZIP `vg_rules-0.1.2.zip` supplied with the release, or
   [build it](../README.md#build). Keep it compressed. The extension builder writes
   `dist/blender_extensions/`; its output is separate from the Gumroad installer.
2. Open **Preferences > Get Extensions > top-right menu > Install from Disk**.
3. Select the ZIP and enable **VG Rules**.
4. In the 3D Viewport, press **N** and open **VG Rules**.

The installed folder contains `QUICK_START.txt`. The public [usage guide](usage.md)
covers the same workflow. The extension has not yet been submitted for platform review.

## Gumroad add-on package

The separate customer ZIP is under `dist/`. Install it through **Preferences >
Add-ons > menu > Install from Disk**, then enable VG Rules. Its source keeps
`bl_info`; the extension uses `blender_manifest.toml`. Both have the same runtime.
Use one installation at a time.

## Updates

Follow [migration and updates](migration.md), including a **full Blender restart**.
Save a `.blend` copy and export a JSON backup before changing installations.
Registration rejects conflicting installations before altering Blender resources.

## Permissions and support

The only extension permission is file access for importing/exporting presets.
The runtime needs no network connection, external dependency, registration or key.
Read-only installation directories are supported; export to a writable user folder.

For installation problems, follow [troubleshooting](troubleshooting.md), then
report through [GitHub Issues](https://github.com/cheinu-mike/vg-rules/issues).
