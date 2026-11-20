# Changelog

## 0.1.4 (2026-10-29, development build)

Resubmission candidate (2026-11-19):

- Point the extension quick start and listing to the guides on `main`. Build
  both installers in [GitHub Actions](https://github.com/cheinu-mike/vg-rules/actions/runs/44666038856).
  Validate the hosted extension again with Blender 4.2.23 on Windows and keep
  those exact archive bytes in `dist`.
- Pass all eleven supported hosted platform/version combinations and Windows
  GUI checks on Blender 4.2.1, 4.2.23 and 5.2.0. All three GUI runs verified the
  shared-data warning, Cancel, Continue, native Ctrl-Z and saved `.blend`/JSON
  transfer across installers. Blender 4.2.23 also passed all seven list checks,
  covering text selection, editing, edit cancellation, Move/Remove and Delete
  Prefix default/menu order.
- Refresh Preview and Apply from the final installed extension in the synthetic
  Demo Shell scene on Blender 4.2.23. Reuse the existing cube thumbnail. The
  [compliance report](submission/COMPLIANCE.md) records the passing gate.

- Extension SHA-256: `6f80769a0cb9ddd31304034f5befc7be89b68041ec7707cee8dd1669b402f481`
- Classic add-on SHA-256: `ef4eb88f5538c611992bbd4bf878c2041016ce6aee5dae2b6e41f8071a44e871`

Verification limits: native GUI checks ran on Windows x64. Blender 5.2.0 on
Intel macOS is unsupported. Blender 5.3.0 coverage below applies to the earlier
archive hashes. The first sandboxed Blender 4.2.1 GUI launch crashed before the
dialog. An out-of-sandbox retry with a disposable profile passed all seven
checks. Portable records and screenshots are in `submission/`; detailed logs
are in `tests/.artifacts/resubmission-0.1.4/`. The earlier 0.1.4 ZIPs are retained
under `dist/history/0.1.4/2026-11-19-before-resubmission/`. The published release
remains 0.1.2.

Blender 5.3 local verification and documentation (2026-11-16):

- Verify the 2026-11-15 rebuilt archives with the installed Windows x64 Blender
  5.3.0, build `02f0899d78e3`. All 25 packaging/release-gate tests passed,
  including real validator rejection. All eleven headless stages passed:
  official validation, source and installed-extension integration/runtime,
  enforced read-only/offline operation, installer switches, update, restart
  and uninstall.
- Pass all 14 packaged-extension GUI checkpoints: saved `.blend`/JSON transfer,
  shared-data warning review, Cancel/Continue, native Ctrl-Z restoration,
  Keep/Delete/assignment text selection and editing, edit cancellation,
  Move/Remove and Delete Prefix default/menu order.
- Extend the runner's exact-version option to 5.3.0. Add persistent regressions
  for Delete Prefix and saved enum numbers. Add native Undo and list-check
  modes to the GUI harness, with data assertions and portable screenshots.
- Refresh README, public guides and submission indexes with the local 5.3
  scope, reproduction commands and [detailed report](docs/blender-5.3.md).
  No add-on runtime, packaged quick start or installer changes were required.

Documentation/static checks: 60 local Markdown links and anchors resolved;
Python syntax and exact source parity of both existing archives passed.

Verified archive hashes remain:

- Extension SHA-256: `543593e6f6aba5e6ecb70d20bab2add80d0d35a25129af96b264733ce4d62f42`
- Classic add-on SHA-256: `6dd30eb3215446e0d2c0d38691d45b27e0c1fadea6c6d6481f575b6a71b1eead`

Portable evidence is stored separately under ignored
`tests/.artifacts/blender-5.3-2026-11-16/`. The initial sandboxed write-denial
probe failed; complete runs outside the sandbox passed. Simulated Ctrl-Z failed
to restore the fixture; after disabling event-simulation mode, native Ctrl-Z
passed twice. These harness attempts are preserved with the successful results.

Verification limits: Windows x64 Blender 5.3.0 only; no Linux/macOS 5.3 claim.
The hosted matrix and release policy remain unchanged. All eleven required
hosted combinations, three pinned Windows GUI runs and refreshed final-ZIP
submission captures still require current-hash evidence. Submission readiness
remains blocked and the published release remains 0.1.2. Historical installers
and submission materials remain preserved.

Delete rule default update (2026-11-15):

- Make Delete Prefix the default for new Delete rows and place it above Delete
  Exact, matching the Keep menu order.
- Preserve the original stored enum values so existing saved Delete rules keep
  their match types. Existing rows without an explicitly stored match use the
  new Delete Prefix default.
- Rebuild both 0.1.4 installer formats and preserve the previous local rebuild
  under `dist/history/0.1.4/2026-11-15-before-delete-prefix/`.

Verification: all 25 packaging/release-gate unit tests passed, including real
validator rejection. The rebuilt extension passed Blender 4.2.23's official
validator before replacing its ZIP. The full source add-on integration suite
passed on Windows with Blender 4.2.23. Checks using both final archives verified
the default, menu order, operator-created rows and JSON presets, plus loading
all five explicit Delete match types from a .blend saved by the previous
archive. An unstored old default correctly adopts Delete Prefix. All historical
archives retain their original hashes. Fixtures used disposable directories.

- Extension SHA-256: `543593e6f6aba5e6ecb70d20bab2add80d0d35a25129af96b264733ce4d62f42`
- Classic add-on SHA-256: `6dd30eb3215446e0d2c0d38691d45b27e0c1fadea6c6d6481f575b6a71b1eead`

Portable results and logs are stored separately under the ignored
`tests/.artifacts/delete-prefix-default-0.1.4-2026-11-15/` directory.

Verification limits: these are Windows headless checks on Blender 4.2.23.
The full installed-extension/runtime/restart suites were not rerun for this
update. All eleven supported hosted combinations, local Windows GUI checks and
final-ZIP captures must match these rebuilt hashes before submission readiness.
The published release remains 0.1.2; earlier archive evidence does not certify
this development build.

Local installer rebuild (2026-11-15):

- Rebuild both 0.1.4 installers from `blender-review-fixes` commit `418c41f`,
  including the standalone regex worker and rule-row selection fix.
- Preserve the earlier 0.1.4 installers under
  `dist/history/0.1.4/2026-10-29/`. All eight 0.1.0 through 0.1.3 installers
  retain their original hashes.

Build verification: all 25 packaging/release-gate unit tests passed, including
real validator rejection. The rebuilt extension passed Blender 4.2.23's official
validator before replacing its ZIP. Exact source parity, selectable pattern and
assignment text, the bundled worker, matching 0.1.4/Blender 4.2.1 metadata,
rendered quick start, licenses and text-only package contents were checked.

All eleven local headless stages passed on Windows with Blender 4.2.23 and
5.2.0 against these rebuilt hashes, including installed read-only/offline
operation and all installer-switch/restart lifecycle checks. Initial sandboxed
runs could not enforce the read-only permission probe; complete reruns outside
the sandbox passed using disposable profiles. The failed attempts are preserved
with the successful rerun evidence.

- Extension SHA-256: `76a36a2602dd9d768d3eb6b5c5e5f571d0219e2ceed0c71b3c114793aa7a29b4`
- Classic add-on SHA-256: `7d642c0159c1f1befa931d0971eedf3bba2f3d194ee136d35a698162a3b6ec1f`

Portable build results and logs are stored separately under the ignored
`tests/.artifacts/rebuild-0.1.4-2026-11-15-418c41f/` directory.

Verification limits: this is a development rebuild. All eleven supported hosted
platform/version combinations, local Windows GUI checks and refreshed final-ZIP
Preview/Apply captures must match these hashes before submission readiness.
Earlier evidence is not assumed to certify them. The published release remains
0.1.2; submission readiness remains blocked pending final-archive evidence.

Documentation refresh (2026-11-05):

- Update the README, installation guide and submission index to distinguish the
  combined source fixes from the older 0.1.4 ZIPs built on 2026-10-29.
- Document text-click row selection, double-click editing, worker installation
  requirements and the per-request scope of the regex timeout in the guides and
  packaged quick-start template.
- Record the separate unit, worker-candidate and source-UI verification scopes.
  Label preserved submission reports, captures and rendered quick start as
  historical 0.1.3 evidence. Development documentation links point to this branch.

Documentation checks: 42 local Markdown links/anchors resolved. The quick-start
template rendered 0.1.4 and the Blender 4.2.1 minimum from the package metadata
with no unresolved version placeholders.

Verification limits: this is a documentation-only update. Implementation and
historical evidence are unchanged; no final installers were rebuilt. The updated
quick-start template will be included in a future build, whose new hashes require
the full release verification described below.

Worker simplification (2026-11-05):

- Move regex matching into a bundled, standard-library-only regex_worker.py
  script. Launch it directly with Blender's Python and bpy.app.python_args;
  remove the inline bootstrap, manual module loading and sys.modules assignment.
- Keep the worker out of Blender's add-on imports. Preserve the JSON protocol,
  one-second timeout, Keep/Delete precedence, cache and failure handling.
- Include the same worker source in both installers. Update packaging checks and
  runtime regressions for the additional file and direct script invocation.

Local verification: all 25 packaging/release-gate unit tests passed, including
standalone worker execution from both ZIP layouts, missing-worker rejection and
real validator rejection. Temporary candidate packages passed official extension
validation on Blender 4.2.23. All eleven local headless stages passed on Windows
with Blender 4.2.23 and 5.2.0 against those candidate hashes, including source and
installed suites, read-only/offline operation and installer-switch/restart checks.
The candidates contain nine text files in the extension and seven in the classic
add-on. Portable results are stored separately; temporary fixtures were removed.

Verification limits: the 2026-10-29 installer hashes and results below describe
the earlier bootstrap-based build. Existing installers and evidence remain
preserved; the new worker is currently a source change. Rebuilt final installers
still require all eleven hosted combinations, Windows GUI checks and refreshed
submission captures against their final hashes before being submission-ready.

Rule selection fix (2026-11-05):

- Use Blender's native selectable list text for Keep/Delete patterns and
  assignment names. Clicking the text selects its row; double-clicking edits
  the text with that row selected, so Move/Remove targets the intended entry.
- Verified source UI behavior in a disposable Windows Blender 4.2.23 scene:
  text-click selection, editing and committing a Keep pattern, selecting a
  Delete pattern by double-clicking, cancelling its edit, moving/removing the
  selected pattern, and selecting an assignment through its name all passed.
  All 23 existing packaging/release-gate unit tests passed, including real
  validator rejection. Portable results and a screenshot are stored separately
  under the ignored tests/.artifacts/rule-row-selection directory.

Verification limits for this fix: no installers were rebuilt. These source UI
checks do not certify a final archive or replace the eleven hosted combinations
and local Windows GUI release checks. The earlier archive hashes below predate
this fix; submission readiness remains blocked pending final-archive evidence.

Combined branch verification (2026-11-05): all 25 packaging/release-gate unit
tests passed after integrating both fixes, including real validator rejection.
The combined source has not been rebuilt into final release installers.

Original 0.1.4 package (2026-10-29):

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
