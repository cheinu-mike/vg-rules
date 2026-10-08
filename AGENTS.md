# Release policy

The current release is **0.1.1**; preserve historical **0.1.0** artifacts.
Derive installer filenames from `vg_rules/__init__.py`'s `bl_info` version and
require matching `blender_manifest.toml` metadata.
Record release changes and verification limits in `CHANGELOG.md`.

# Packaging

Use one shared add-on implementation and two separate builders. Only the
extension package omits `bl_info`. The extension builder must run Blender's
official validator before replacing an existing ZIP.

Keep the repository limited to source, builders, synthetic tests, documentation
and licenses. Generated packages and test output remain ignored. Do not build a
seller kit unless the user explicitly requests one.
