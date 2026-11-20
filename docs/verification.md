# Verification and release gate

The current branch combines the standalone regex worker, rule-row selection
fixes and Delete Prefix default/menu order update. Both local 0.1.4 installers
were rebuilt on 2026-11-15 with those changes. Earlier 0.1.4 ZIPs are preserved
under `dist/history/0.1.4/`.
The [changelog](../CHANGELOG.md) records these separate verification scopes:

| Check | Latest recorded result | Scope |
| --- | --- | --- |
| Packaging/release-gate unit tests | 25 passed on 2026-11-16, including real Blender 5.3 validator rejection | Current builders and release gate; temporary packaging fixtures |
| Source add-on integration suite | Passed on Windows with Blender 4.2.23 on 2026-11-15 | Latest source including the Delete Prefix default change |
| Packaged Delete match checks | Passed on Windows with Blender 4.2.23 | Both latest archives: default, menu order, operator-created rows, saved explicit enum values and JSON presets |
| Blender 5.3.0 local headless checks | All eleven stages passed on Windows x64 on 2026-11-16 | Latest rebuilt archives; source and installed-extension suites, enforced read-only/offline operation and all restart/lifecycle stages; includes Delete Prefix/default and stable saved enum numbers |
| Blender 5.3.0 local GUI checks | All 14 checkpoints passed on 2026-11-16 | Latest packaged extension: native Cancel/Continue, Ctrl-Z, saved-rule transfer, text selection/editing/cancellation, Move/Remove and Delete Prefix default/menu; see the [5.3 report](blender-5.3.md) |
| Full headless source, installed-extension and restart suites | All eleven stages passed on Windows with Blender 4.2.23 and 5.2.0 on 2026-11-15 | Earlier rebuild before the Delete Prefix default change; historical hashes in CHANGELOG |
| Rule-row selection GUI checks | Passed on Windows with Blender 4.2.23 | Source UI session; no rebuilt final archive |
| Final combined candidate | Rebuilt locally on 2026-11-15; submission verification pending | All eleven hosted pairs, three Windows GUI runs and refreshed Preview/Apply captures must match the rebuilt archive hashes |

GitHub Actions tests the same candidate ZIP on Windows x64, Linux x64, macOS
Intel and macOS Apple Silicon using pinned official Blender 4.2.1, 4.2.23 and
5.2.0 distributions with SHA-256 checks. macOS Intel runs both 4.2 versions;
Blender 5.2.0 has no official Intel build and is unsupported there. This is an
explicitly accepted exception, giving eleven required platform/version pairs.

Blender **5.3.0** is additional local Windows coverage. It is accepted by
`tests/run_blender.py --expect-version 5.3.0`, but has not been added to the
hosted downloader, matrix or release gate. No Linux/macOS 5.3 pass is implied.
See the [local report](blender-5.3.md) for the installed build identity and exact
candidate hashes. The minimum remains 4.2.1 and the published version remains 0.1.2.

The workflow builds once, then every job downloads those exact installers.
It runs Blender's official extension validator, the full source regression and
runtime suites, and both suites from the installed extension under an arbitrary
repository namespace. Installation permissions deny writes during operations.
Offline sessions also block Python socket/URL entry points during installed tests.
This verifies application behavior; it is not an operating-system network trace.

Checks cover foreign-scene pointers, unlinking targets, shared objects and meshes
across scenes, rejected batches, cancelled shared-data operations, groups, locks,
weights and Mirror settings. They exercise bounded Python regex, actual regex
timeouts, worker failures, saved rules across enable/disable, immediate sidebar
drawing without data changes, atomic preset exports and uninstall. Separate Blender
processes exercise traditional add-on ZIP installation, saved separate Keep/Delete
rules, loading without validation or metadata rewrites, JSON backups, installer
switches, update and restart. The previous extension in the update test is a synthetic
lower-version package with a marker; the restarted process must load final bytes.

Packaging regressions execute `regex_worker.py` directly from both installer
layouts and reject a missing worker without replacing existing ZIPs. Runtime
checks cover forwarded Blender Python arguments, the worker timeout, missing or
failed workers, invalid results and cached decisions. The worker is a bundled
runtime script using only the standard library; normal add-on imports do not run it.

All generated scenes, profiles, intermediate ZIPs and presets use disposable
temporary directories. Hosted runs use RUNNER_TEMP; local runs use temporary
subdirectories of ignored tests/.artifacts to support restricted Windows hosts.
Only portable results, logs and screenshots remain in the selected evidence folder.
No personal models or projects are fixtures.

To reproduce a pinned run after building both installers:

```sh
python -B -m unittest discover -s tests -p 'test_*.py'
python -B tests/run_blender.py --blender /path/to/blender --expect-version 4.2.1
```

Set VGR_TEST_BLENDER to an official Blender executable for the packaging test
that proves its validator rejects an invalid candidate without replacing a ZIP.
Without that environment variable, that one test is explicitly skipped.

Local GUI verification runs the final installed ZIP in disposable Windows
sessions on all three pinned versions. It inspects the actual warning layout,
clicks native Cancel and Continue, and uses Ctrl-Z to verify Undo restores all
shared groups, weights and Mirror modifiers. Saved .blend and JSON transfer between
installers are checked in the GUI session too. Screenshot hashes and results are recorded
in submission/gui-results.json. GUI behavior on macOS/Linux has not been tested.

```sh
python -B tests/gui_checks.py --blender /path/to/blender --output-dir tests/.artifacts/gui-check
```

This pauses for visual inspection of warning.png and confirmation.png. Provide
command.json as documented in the script only after inspecting the native dialog.
It must not receive an automatic PASS for an unreviewed warning.

For Blender 5.3, use `--native-undo` to disable event-simulation mode after
Continue and wait for a native Ctrl-Z in the viewport. Inspect `waiting.json`,
focus the viewport, press Ctrl-Z, then write
`{"action": "undo", "visual_review": true}` to `command.json`. The harness
asserts restored groups, weights, locks and Mirror settings and records an
`undo-state.json` diagnostic. The original simulated Ctrl-Z did not restore
the fixture on this build; native input passed. Event-simulation mode ignores
OS input until disabled. Blender's
[event-simulation testing workflow](https://developer.blender.org/docs/handbook/tooling/git_bisect_with_event_simulation/)
also documents leaving a test open for inspection. This harness hands control
to native input with `bpy.app.use_event_simulate = False`.

Use `--list-checks` for native Undo plus the pattern/assignment regression checks:

```sh
python -B tests/gui_checks.py --blender /path/to/blender --list-checks --output-dir tests/.artifacts/gui-lists
```

After Undo, `waiting.json` describes each native list action: text selection,
editing/commit, edit cancellation, Move/Remove and the new Delete Prefix row/menu.
Perform the action, then provide `{"action": "lists", "visual_review": true}`
in `command.json`. Each checkpoint asserts the resulting Blender properties
and saves a screenshot. Use a fresh evidence directory per run. These checks
operate only on generated fixtures in a temporary profile.

The release gate requires all eleven hosted results, all three local GUI results,
exact installer hashes, package/source parity, licenses, public guides, listing
and final-archive product captures. Missing, failed or stale evidence blocks release.
Include the pattern/assignment text-selection and editing checks in final GUI
verification so the combined package is checked for the row-selection fix too.
The existing [compliance report](../submission/COMPLIANCE.md) and linked Actions
run record earlier archive hashes. Verification of the revised candidate is
pending; previous passes do not certify its final installers. Workflow artifacts
retain detailed diagnostics for 30 days.

```sh
python -B tests/compliance.py --evidence /path/to/downloaded/actions/results --output submission --require-ready
```

Submission-ready means these preparation checks passed. Uploading the extension
and responding to Blender platform moderation are subsequent release steps.
