# VG Rules compliance report

Version: **0.1.3**. Submission-ready: **YES**.
Generated UTC: 2026-10-19T19:00:12.675478+00:00

Extension SHA-256: `a9d019ec4d52cf8bbd29afda6df79ecd636088e423b633535c92caac680a51af`
Gumroad SHA-256: `2cd19608f64be6248fa02fa7cc24ce07b40d89771b4f0ad3e8ab36b033a37dc6`

[Hosted verification run](https://github.com/cheinu-mike/vg-rules/actions/runs/39306833907)

| Platform | Blender | Actual result |
| --- | --- | --- |
| linux-x64 | 4.2.0 | PASS |
| linux-x64 | 4.2.23 | PASS |
| linux-x64 | 5.2.0 | PASS |
| macos-arm64 | 4.2.0 | PASS |
| macos-arm64 | 4.2.23 | PASS |
| macos-arm64 | 5.2.0 | PASS |
| macos-x64 | 4.2.0 | PASS |
| macos-x64 | 4.2.23 | PASS |
| windows-x64 | 4.2.0 | PASS |
| windows-x64 | 4.2.23 | PASS |
| windows-x64 | 5.2.0 | PASS |
| macos-x64 | 5.2.0 | Unsupported; no official build |

Local native GUI checks:

- Windows / 4.2.0: PASS
- Windows / 4.2.23: PASS
- Windows / 5.2.0: PASS

Package and submission materials:

- PASS: exact source parity, matching metadata/credits, GPL notices, files-only permission; eight text files in extension, six in legacy installer; no bundled artwork/fonts/binaries
- PASS: final-archive synthetic Preview/Apply captures, unchanged cube thumbnail, public guides and listing present

Verification scope:

- Headless checks on every required hosted platform; local GUI checks on Windows only
- Update uses a synthetic previous-version package with a marker, followed by a real process restart
- Runtime tests are offline and block Python socket/URL entry points; not an OS firewall trace
- Installer-switch checks use generated saved separate Keep/Delete rules and JSON, not personal projects
- Platform upload and moderation are subsequent release steps
