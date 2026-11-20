# Blender 5.3 local verification

The rebuilt **VG Rules 0.1.4** archives passed the checks below on **Windows
x64 with the installed Blender 5.3.0** on **2026-11-16**. This report covers the
earlier 0.1.4 installer hashes listed below.

Blender reported release branch `blender-v5.3-release`, build hash
`02f0899d78e3`, built 2026-11-10. The executable was
`C:\Program Files\Blender Foundation\Blender 5.3\blender.exe`.
Testing used the 2026-11-15 Delete Prefix rebuilds:

| Package | SHA-256 |
| --- | --- |
| Extension, `dist/blender_extensions/vg_rules-0.1.4.zip` | `543593e6f6aba5e6ecb70d20bab2add80d0d35a25129af96b264733ce4d62f42` |
| Classic add-on, `dist/vg_rules-0.1.4.zip` | `6dd30eb3215446e0d2c0d38691d45b27e0c1fadea6c6d6481f575b6a71b1eead` |

The tested installers are preserved under
`dist/history/0.1.4/2026-11-19-before-resubmission/`.

## Results

| Check | Result and scope |
| --- | --- |
| Packaging/release-gate unit tests | 25 passed, no skips; includes real Blender 5.3 validator rejection without replacing an existing ZIP |
| Version and architecture probe | Exact 5.3.0, AMD64, offline |
| Official extension validator | Passed against the existing extension archive |
| Source add-on integration suite | Passed: all Keep/Delete match types and precedence, case sensitivity, full weights, sides, Mirror, shared data, invalid rules and preset handling |
| Source runtime suite | Passed: registration, saved rules, scene scope, shared-data planning, worker startup/failures/timeouts, read-only/export protections |
| Installed extension | Passed both full suites in an arbitrary extension repository namespace; installed bytes matched the ZIP; enforced write denial and blocked Python network entry points |
| Classic add-on and installer lifecycle | All six phases passed: classic install/save, migration, restart into a synthetic previous extension, update, updated restart/uninstall, uninstalled restart |
| Delete defaults and saved enum numbers | Passed in source and installed extension: new operator-created rows default to Prefix; menu order preserves enum numbers Exact=0, Prefix=1, Contains=2, Suffix=3, Regex=4 |
| GUI shared-data workflow | Seven checkpoints passed: saved `.blend` migration, JSON transfer, Cancel preserving data, warning layout review, Continue applying changes, native Ctrl-Z restoring data and unchanged migration backups |
| GUI list workflow | Seven checkpoints passed: Keep text selection, edit/commit, move selected row, remove selected row, Delete selection/edit cancellation, assignment selection/edit and Delete Prefix default/menu order |

The headless runner recorded **11 passing stages**. The final GUI run recorded
**14 passing checkpoints** with screenshots. Apply/Undo assertions covered both
shared mesh users, every vertex-group weight, group locks and Mirror settings.
Long object and scene names in the shared-data warning were visually reviewed.

## Evidence and reproduction

Portable results, logs and screenshots are stored separately from installers in
the ignored `tests/.artifacts/blender-5.3-2026-11-16/` directory:

- `unit-tests.txt`: all 25 packaging/release-gate results.
- `headless-final/result.json` and stage logs: final complete headless pass,
  including the new default/menu regression assertions.
- `gui-final/result.json`, `undo-state.json` and PNGs: final GUI pass, including
  native input and all seven list checkpoints.
- `release-gate/`: package/source parity and the remaining submission blockers.
- `final-checks.json`: 60 resolved local documentation links/anchors, Python
  syntax checks, exact package/source parity and all preserved installer hashes.
- `blender-version.txt`: installed Blender build identity.
- Earlier attempts remain alongside the final runs for diagnostics.

Use the commands in [README](../README.md#checks) and follow the checkpoint
protocol in [Verification](verification.md). `--expect-version 5.3.0` enforces
the exact version. `--list-checks` includes native Undo and list tests; it does
not assign a pass until the resulting Blender properties satisfy each assertion.
Every generated scene, saved preset, installation and profile is disposable.
The tests do not open personal projects or alter the normal Blender profile.

## Harness findings and limits

The initial sandboxed installed-extension check could not enforce its write-denial
probe. Complete reruns outside the sandbox passed with real read-only ACLs on
only the temporary installation; original permissions were restored on exit.

The original simulated Ctrl-Z check did not restore the fixture. An initial
attempt at native input was also inconclusive because event-simulation mode
still ignored OS input. The harness now offers `--native-undo` and `--list-checks`,
which disable event simulation after Continue, then wait for native Ctrl-Z.
Native input passed twice, including the final combined GUI run. Failed attempts
are retained; they are not counted as passes. The default simulated shortcut
path remains unverified on 5.3; use the native-input options for reproduction.

These results cover this Windows x64 build and these archive hashes. They do
not verify Blender 5.3 on Linux or macOS, every future 5.3 patch, or personal
production scenes. The classic installer has lifecycle coverage; the full
installed regression suites and GUI checks use the extension, whose shared
runtime is verified against the source.

See the [compliance report](../submission/COMPLIANCE.md) for the later
resubmission candidate and its exact archive hashes.
