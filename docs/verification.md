# Verification and release gate

GitHub Actions tests the same candidate ZIP on Windows x64, Linux x64, macOS
Intel and macOS Apple Silicon using pinned official Blender 4.2.0, 4.2.23 and
5.2.0 distributions with SHA-256 checks. macOS Intel runs both 4.2 versions;
Blender 5.2.0 has no official Intel build and is unsupported there. This is an
explicitly accepted exception, giving eleven required platform/version pairs.

The workflow builds once, then every job downloads those exact installers.
It runs Blender's official extension validator, the full source regression and
runtime suites, and both suites from the installed extension under an arbitrary
repository namespace. Installation permissions deny writes during operations.
Offline sessions also block Python socket/URL entry points during installed tests.
This verifies application behavior; it is not an operating-system network trace.

Checks cover foreign-scene pointers, unlinking targets, shared objects and meshes
across scenes, rejected batches, cancelled shared-data operations, groups, locks,
weights and Mirror settings. They exercise bounded Python regex, actual regex
timeouts, worker failures, registration conflicts and rollback, atomic preset
exports, disable/re-enable and uninstall. Separate Blender processes exercise
legacy ZIP installation, generated saved mixed-list rules, JSON backup migration,
update and restart. The previous extension in the update test is a synthetic
lower-version package with a marker; the restarted process must load final bytes.

All generated scenes, profiles, intermediate ZIPs and presets use disposable
temporary directories. Hosted runs use RUNNER_TEMP; local runs use temporary
subdirectories of ignored tests/.artifacts to support restricted Windows hosts.
Only portable results, logs and screenshots remain in the selected evidence folder.
No personal models or projects are fixtures.

To reproduce a pinned run after building both installers:

```sh
python -B -m unittest discover -s tests -p 'test_*.py'
python -B tests/run_blender.py --blender /path/to/blender --expect-version 4.2.0
```

Set VGR_TEST_BLENDER to an official Blender executable for the packaging test
that proves its validator rejects an invalid candidate without replacing a ZIP.
Without that environment variable, that one test is explicitly skipped.

Local GUI verification runs the final installed ZIP in disposable Windows
sessions on all three pinned versions. It inspects the actual warning layout,
clicks native Cancel and Continue, and uses Ctrl-Z to verify Undo restores all
shared groups, weights and Mirror modifiers. Legacy .blend and JSON migration
are checked in the GUI session too. Screenshot hashes and results are recorded
in submission/gui-results.json. GUI behavior on macOS/Linux has not been tested.

```sh
python -B tests/gui_checks.py --blender /path/to/blender --output-dir tests/.artifacts/gui-check
```

This pauses for visual inspection of warning.png and confirmation.png. Provide
command.json as documented in the script only after inspecting the native dialog.
It must not receive an automatic PASS for an unreviewed warning.

The release gate requires all eleven hosted results, all three local GUI results,
exact installer hashes, package/source parity, licenses, public guides, listing
and final-archive product captures. Missing, failed or stale evidence blocks release.
The authoritative actual results are in [the compliance report](../submission/COMPLIANCE.md)
and the linked public Actions run. Workflow artifacts retain detailed diagnostics
for 30 days; the committed report preserves the compact release evidence.

```sh
python -B tests/compliance.py --evidence /path/to/downloaded/actions/results --output submission --require-ready
```

Submission-ready means these preparation checks passed. Uploading the extension
and responding to Blender platform moderation are subsequent release steps.
