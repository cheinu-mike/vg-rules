# VG Rules compliance report

Version: **0.1.4**. Submission-ready: **YES**.
Generated UTC: 2026-11-20T03:21:05.783155+00:00

Extension SHA-256: `6f80769a0cb9ddd31304034f5befc7be89b68041ec7707cee8dd1669b402f481`
Gumroad SHA-256: `ef4eb88f5538c611992bbd4bf878c2041016ce6aee5dae2b6e41f8071a44e871`

[Hosted verification run](https://github.com/cheinu-mike/vg-rules/actions/runs/44666038856)

| Platform | Blender | Actual result |
| --- | --- | --- |
| linux-x64 | 4.2.1 | PASS |
| linux-x64 | 4.2.23 | PASS |
| linux-x64 | 5.2.0 | PASS |
| macos-arm64 | 4.2.1 | PASS |
| macos-arm64 | 4.2.23 | PASS |
| macos-arm64 | 5.2.0 | PASS |
| macos-x64 | 4.2.1 | PASS |
| macos-x64 | 4.2.23 | PASS |
| windows-x64 | 4.2.1 | PASS |
| windows-x64 | 4.2.23 | PASS |
| windows-x64 | 5.2.0 | PASS |
| macos-x64 | 5.2.0 | Unsupported; no official build |

Local native GUI checks:

- Windows / 4.2.1: PASS
- Windows / 4.2.23: PASS
- Windows / 5.2.0: PASS

Package and submission materials:

- PASS: exact source parity, matching metadata/credits, GPL notices, files-only permission; 9 text files in extension, 7 in legacy installer; no bundled artwork/fonts/binaries
- PASS: final-archive synthetic Preview/Apply captures, unchanged cube thumbnail, public guides and listing present

Verification scope:

- Headless checks on every required hosted platform; local GUI checks on Windows only
- Update uses a synthetic previous-version package with a marker, followed by a real process restart
- Runtime tests are offline and block Python socket/URL entry points; not an OS firewall trace
- Installer-switch checks use generated saved separate Keep/Delete rules and JSON, not personal projects
- Platform upload and moderation are subsequent release steps
