# Changelog

## 0.1.1 (2026-10-08)

- Resolve imported names and executable rule targets in the executing scene.
  The picker shows that scene's meshes. Outside-scene pointers remain saved;
  their rules are skipped with a warning.
- Include affected objects and their scenes in shared-data confirmation,
  including one object linked into several scenes. Cancel keeps the batch intact.
- Reject registration conflicts before changing Blender resources, roll back
  partial registration, and remove only resources owned by this installation.
- Export presets atomically and reject destinations inside VG Rules installations,
  including disabled legacy and extension copies.
  Preserve an existing preset if writing or replacement fails.
- Require Blender's bundled Python for the bounded regex worker, including when
  reusing cached decisions. Keep Python regex syntax, timeout and failure behavior.
- Preserve operator IDs, preset format, saved rule properties, relative imports
  and the file-only manifest permission. Add no external dependencies or services.

Verification: 13 packaging checks, the full source integration suite, and runtime
regressions passed on Windows with Blender 4.2.23 and 5.2.0. Installed-extension
checks include enabling, running and disabling with write access denied and
restoring the original directory permissions. The extension ZIP passed Blender's
official validator. macOS and Linux verification remains pending.

## 0.1.0 (2026-10-08)

- Initial VG Rules source and separate Gumroad and Blender extension builders.
- Canonical public repository with synthetic tests, documentation and GPL license.
- Match manifest metadata to `bl_info` and omit it only from the extension ZIP.
- Require official Blender validation before atomically replacing extension output.
