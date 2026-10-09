# VG Rules compliance report

Version: **0.1.2**. Submission-ready: **YES**.
Generated UTC: 2026-10-09T01:14:28.907284+00:00

Extension SHA-256: `c8bc7418e4e7b625e6bd251ff494736a1efe9ab60b1ac71a198f0bb6924d6b2e`
Gumroad SHA-256: `7a7776f093f4bc224cc80d73c84ec5ad61a4600800b6b2713aa331e9659c76cc`

[Hosted verification run](https://github.com/cheinu-mike/vg-rules/actions/runs/37868570738)

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
- Legacy migration uses generated saved mixed-list rules and JSON, not personal projects
- Platform upload and moderation are subsequent release steps
