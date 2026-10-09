# Release policy

The current release is **0.1.2**; preserve historical **0.1.0** and **0.1.1** artifacts.
Derive installer filenames from `vg_rules/__init__.py`'s `bl_info` version and
require matching `blender_manifest.toml` metadata.
Record release changes and verification limits in `CHANGELOG.md`.

Require all eleven supported hosted platform/version combinations and local
Windows GUI checks to pass against the final archive hash before marking it
submission-ready. Blender 5.2.0 on macOS Intel is unsupported; verify Intel on
4.2.0 and 4.2.23. Missing, failed or stale evidence is a release blocker.
Keep generated fixtures in disposable temporary directories. Preserve portable
results and screenshots separately from the installers.

# Packaging

Use one shared add-on implementation and two separate builders. Only the
extension package omits `bl_info`. The extension builder must run Blender's
official validator before replacing an existing ZIP.

Keep the repository limited to source, builders, synthetic tests, documentation,
licenses and separately stored submission materials. Generated packages and test
output remain ignored. Do not build a seller kit unless the user explicitly
requests one.

Include the extension-specific quick start in the extension ZIP, with its version
rendered from `bl_info`. Keep images, fonts and binaries out of both installers.
Any future bundled assets must have documented CC0 rights and appropriate credits.
Keep copyright notices and manifest credits consistent.

# Submission materials

Keep the name VG Rules. Describe only included functionality. Use the existing
cube thumbnail and genuine Preview/Apply captures from the final packaged
extension in a synthetic scene. Do not include the Blender logo in those images
or advertisements inside the application. Support goes to GitHub Issues in the
canonical repository: https://github.com/cheinu-mike/vg-rules.
