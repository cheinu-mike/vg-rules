# Changelog

## 0.1.2 (2026-10-08)

- Fix the empty sidebar caused by writing Scene properties during panel drawing.
  Defer scene initialization, target-name refresh and saved-list migration to an
  owned timer; draw initialized rules without changing scene data.
- Add public installation, usage, migration and troubleshooting guides, with
  GitHub Issues for support. Include an extension-specific quick start in its ZIP.
- Prepare listing text, the existing cube thumbnail, and genuine Preview/Apply
  screenshots from the packaged extension using a generated scene. Keep all
  submission artwork outside the installers.
- Run the full source and installed-extension regressions on checksum-pinned
  Blender 4.2.0, 4.2.23 and 5.2.0 in GitHub Actions, including real installation,
  disable/re-enable, legacy migration, update, fresh-process restart and uninstall.
- Add cross-scene shared-mesh and cancelled/rejected batch checks, with snapshots
  of groups, locks, weights and per-object Mirror settings.
- Use temporary fixtures and profiles, and enforce read-only installation access.
  On Windows compare restored access rules and inheritance protection, allowing
  Windows to normalize SDDL metadata. Write denial remains mandatory.
- Make ZIP metadata reproducible and use LF text checkouts on every platform.
  Keep a release gate that rejects missing, failed or wrong-hash evidence.

Verification: 22 packaging/release-gate unit checks passed, with the real Blender
validator rejection test enabled. Full source, runtime, installed ZIP and lifecycle
checks passed on all eleven supported hosted combinations: Windows x64, Linux x64
and macOS Apple Silicon on all three pinned versions, plus macOS Intel on both
4.2 versions. Blender 5.2.0 has no official Intel build and is unsupported there.
Local Windows GUI checks passed on all three versions: warning layout, actual
Cancel/Continue, Ctrl-Z Undo, and saved legacy .blend/JSON migration. Product
captures and GUI evidence use the final archive. See the hash-bound
[compliance report](submission/COMPLIANCE.md) for actual results and scope.

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
