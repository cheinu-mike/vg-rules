# Changelog

## 0.1.4 (2026-10-29, development build)

- Package the reviewer fixes under a new version so the installers are distinct
  from the previously verified 0.1.3 build and Blender can recognize the update.
- Set matching add-on and extension metadata to 0.1.4; keep Blender 4.2.1 as the
  minimum. Update the active installation guides, listing and release policy.
  The extension quick start renders the version from bl_info during packaging.
- Include the explicit regex-worker launcher, forwarded bpy.app.python_args and
  removal of packaged direct-execution guards. Preserve the one-second worker
  deadline and failure handling. Keep the eleven-pair hosted test matrix on
  Blender 4.2.1, 4.2.23 and 5.2.0, excluding unsupported macOS Intel on 5.2.0.
- Preserve the 0.1.0, 0.1.1, 0.1.2 and original 0.1.3 installers and historical
  submission evidence. The published release remains 0.1.2.

Build verification (2026-10-29): all 23 packaging/release-gate unit tests passed,
including real validator rejection. Both installers were built with matching
0.1.4 metadata. The extension passed Blender's official validator on 4.2.23;
its quick start renders 0.1.4 and requires Blender 4.2.1. Exact source parity,
licenses and text-only package contents passed; only the extension omits bl_info.
All eleven local headless stages passed on Windows with Blender 4.2.23 and 5.2.0
against these final hashes, including installed read-only/offline operation and
installer-switch/restart checks. All eight pre-existing installers are unchanged.
Portable results and logs remain separate from the installers.

- Extension SHA-256: `6afa3908556f52b63c309f798eb13dc5bdb8daa4cf45a7af0e8db9b615a218b5`
- Classic add-on SHA-256: `983edb1f9f7c0940a1946b3dc30c8bd7e4832b8f91bd4e83ee55826d22ac3729`

Verification limits: local checks above are Windows headless only. Blender 4.2.1
passed the earlier 0.1.3 candidate, not these final 0.1.4 hashes. The release gate
correctly reports that 0.1.4 is not submission-ready: all eleven hosted
platform/version combinations, local Windows GUI checks and final-archive
Preview/Apply captures remain required. Earlier 0.1.3 evidence is historical and
does not certify these installers. The published release remains 0.1.2.

## 0.1.3 (2026-10-12, development build)

Review corrections (2026-10-28; verification pending):

- Raise the minimum supported Blender version to 4.2.1 in both package formats.
- Forward bpy.app.python_args immediately after the bundled Python executable.
- Replace the regex worker's direct-execution guard with an explicit child-process
  launcher that loads the existing module by absolute path and calls its worker.
- Remove the optional direct-execution registration guard from the add-on.
- Replace 4.2.0 with 4.2.1 in the required test matrix; retain eleven hosted pairs
  and Windows GUI checks on 4.2.1, 4.2.23 and 5.2.0.

Local verification (2026-10-28): all 23 packaging/release-gate unit tests passed,
including real validator rejection. Candidate installers were built in disposable
staging, with official extension validation on Blender 4.2.23. All eleven local
headless stages passed on Windows with Blender 4.2.1, 4.2.23 and 5.2.0 against the
same candidate hashes, including source and installed-extension suites, enforced
read-only/offline operation, and installer-switch/restart lifecycle checks.
Portable results and logs are stored separately from installers; existing release
installers and submission evidence were preserved.

Verification limits: these are local Windows headless checks. All archive results
below apply only to the previously verified hashes. Revised installers remain
blocked pending all eleven required hosted platform/version combinations, local
Windows GUI checks and refreshed submission captures against the final archive
hashes. Preserve previous release artifacts and evidence; the published release
remains 0.1.2.

- Bump add-on and manifest metadata together to 0.1.3. Build separate 0.1.3
  installers for testing; preserve the published 0.1.2 packages and prior artifacts.

- Simplify registration and unregistration to direct class and Scene-property
  operations. Remove duplicate-installation checks, ownership tracking and
  partial-registration rollback.
- Read saved Scene rules directly and use property defaults for fresh scenes.
  Remove load handlers, initialization timers, the sidebar readiness gate,
  initialization flags and unused mixed-pattern migration. Released 0.1.0 already
  stored separate Keep/Delete collections and object-binding history.
- Keep target callbacks and metadata refresh when Preview/Apply uses a rule;
  display live names without changing saved properties during drawing or loading.
  Retain preset validation, operation checks and bounded regex execution.
- Replace unpublished mixed-list fixtures with ordinary saved-rule persistence
  checks across installer switches. Verify saved indexes, results and binding
  metadata load unchanged, without running validation or target callbacks.

Implementation verification before the version bump: 22 packaging/release-gate
tests, all eleven hosted platform/version combinations and Windows native GUI
checks on Blender 4.2.0, 4.2.23 and 5.2.0 passed. Checks include Cancel/Continue,
Ctrl-Z Undo, fresh and unfinished saved rules, disable/re-enable, real published
0.1.2 replacement with full restart, read-only/offline operation and 0.1.0 saved
files. These results apply to the earlier candidate ZIP, not the new 0.1.3 hashes.

0.1.3 archive verification: all 22 packaging/release-gate tests passed, including
real validator rejection. The extension passed Blender's official validator on
4.2.23. Actual published 0.1.2-to-0.1.3 install/replacement and full-restart checks
passed on Windows with Blender 4.2.0, 4.2.23 and 5.2.0, including saved rules,
Preview/Apply and disable/re-enable. The classic add-on installed and passed
Preview/Apply and disable cleanup on Blender 4.2.23. Both ZIPs have matching 0.1.3
metadata, and the extension quick start renders 0.1.3 without placeholders.

Final archive verification (2026-10-19): all eleven supported hosted combinations
passed against the CI-produced 0.1.3 installers. Native Windows GUI checks passed
on Blender 4.2.0, 4.2.23 and 5.2.0 against that exact extension ZIP, including
visually reviewed shared-data warnings, actual Cancel/Continue, Ctrl-Z Undo and
saved .blend/JSON transfer between installers. Fresh synthetic Preview/Apply
captures passed on Blender 4.2.23 with installed-byte parity and verified weights;
the existing cube thumbnail is unchanged. The release gate reports zero blockers.
See the hash-bound [compliance report](submission/COMPLIANCE.md) and portable
hosted/GUI records. Historical 0.1.2 submission evidence is preserved under
`submission/history/0.1.2/`; all historical installers remain preserved.

Verification limits: GUI behavior is verified on Windows only. Hosted update
checks use a synthetic previous-version package followed by a fresh-process
restart; offline checks are application-level, not an OS network trace. Blender
5.2.0 on macOS Intel remains unsupported; both pinned 4.2 versions passed there.
0.1.3 is submission-ready for preparation purposes, but remains an unpublished
development build. The published release remains 0.1.2; platform upload and
moderation are separate subsequent steps.

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
