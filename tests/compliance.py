# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Collect actual evidence; missing, failed or stale verification blocks release."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_addon
import build_extension

VERSIONS = ('4.2.0', '4.2.23', '5.2.0')
PLATFORMS = ('windows-x64', 'linux-x64', 'macos-x64', 'macos-arm64')
REQUIRED = {(p, v) for p in PLATFORMS for v in VERSIONS if (p, v) != ('macos-x64', '5.2.0')}
STAGES = {'version', 'official_validation', 'verify_addon', 'verify_runtime', 'verify_extension',
          'lifecycle_legacy', 'lifecycle_migration', 'lifecycle_migration_restart_old',
          'lifecycle_update', 'lifecycle_updated_restart_uninstall', 'lifecycle_uninstalled_restart'}
GUI_STAGES = {'legacy_saved_blend_migration', 'legacy_json_backup_migration',
              'cancel_preserves_groups_weights_modifiers', 'warning_layout_reviewed',
              'continue_applies_confirmed_changes', 'undo_restores_groups_weights_modifiers',
              'migration_backups_unchanged'}
INSTALLED = {
    'extension install/enable and installed-byte parity',
    'full integration suite in installed extension namespace',
    'runtime compliance regressions in installed extension namespace',
    'offline flag remains false with Python network entry points blocked',
    'disable/re-enable/disable preserves installation ownership',
    'enable, operations, worker, export and disable with enforced read-only installation',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_errors(record, expected):
    checks = record.get('checks', [])
    names = [c.get('name') for c in checks]
    errors = []
    if record.get('status') != 'PASS':
        errors.append('overall status is not PASS')
    if len(names) != len(set(names)):
        errors.append('duplicate check names')
    if not expected <= set(names):
        errors.append('missing checks: ' + ', '.join(sorted(expected - set(names))))
    if any(c.get('status') != 'PASS' for c in checks):
        errors.append('a check did not pass')
    return errors


def evaluate(records, gui, archive_hash, legacy_hash, *, require_hosted=True):
    """Use explicit evidence, never infer a pass from absence or a platform label."""
    blockers, matrix, local = [], [], []
    for platform, version in sorted(REQUIRED):
        matches = [r for r in records if (r.get('platform'), r.get('blender')) == (platform, version)]
        reasons = []
        if len(matches) != 1:
            reasons.append(f'expected one result, found {len(matches)}')
        else:
            r = matches[0]
            reasons += stage_errors(r, STAGES)
            if r.get('expected_blender') != version:
                reasons.append('pinned version was not required')
            arch = 'arm64' if platform.endswith('arm64') else 'x64'
            if r.get('blender_architecture') not in ({'arm64', 'aarch64'} if arch == 'arm64' else {'AMD64', 'x86_64'}):
                reasons.append('architecture does not match')
            if r.get('archive_sha256') != archive_hash or r.get('legacy_sha256') != legacy_hash:
                reasons.append('installer hash differs from final archive')
            if not INSTALLED <= set(r.get('installed_checks', [])):
                reasons.append('installed read-only/offline/full-suite coverage missing')
            if require_hosted and not r.get('github_sha'):
                reasons.append('no hosted Actions source revision')
        matrix.append({'platform': platform, 'blender': version, 'status': 'FAIL' if reasons else 'PASS',
                       'reasons': reasons, 'source_revision': matches[0].get('github_sha') if len(matches) == 1 else None})
        blockers += [f'{platform} / {version}: {reason}' for reason in reasons]
    for version in VERSIONS:
        matches = [r for r in gui if r.get('platform') == 'windows-x64' and r.get('blender') == version]
        reasons = []
        if len(matches) != 1:
            reasons.append(f'expected one GUI result, found {len(matches)}')
        else:
            reasons += stage_errors(matches[0], GUI_STAGES)
            if matches[0].get('archive_sha256') != archive_hash:
                reasons.append('GUI checked another archive')
            if not {'warning', 'confirmation', 'cancelled', 'continued', 'undo'} <= set(matches[0].get('images', {})):
                reasons.append('GUI captures missing')
        local.append({'platform': 'windows-x64', 'blender': version, 'status': 'FAIL' if reasons else 'PASS',
                      'reasons': reasons})
        blockers += [f'GUI / {version}: {reason}' for reason in reasons]
    return matrix, local, blockers


def collect(root, evidence):
    source = root / 'vg_rules'
    metadata = build_addon.read_metadata((source / '__init__.py').read_bytes())
    version = '.'.join(map(str, metadata['version']))
    archive = root / f'dist/blender_extensions/vg_rules-{version}.zip'
    legacy = root / f'dist/vg_rules-{version}.zip'
    blockers = []
    archive_hash = digest(archive) if archive.is_file() else None
    legacy_hash = digest(legacy) if legacy.is_file() else None
    if archive_hash is None or legacy_hash is None:
        blockers.append('Final extension and Gumroad installers must both exist')
    static = []
    try:
        payload = {name: (source / name).read_bytes() for name in (*build_addon.FILES, *build_extension.EXTRA_FILES)}
        manifest = build_extension.read_manifest(payload[build_extension.MANIFEST], metadata)
        assert set(manifest['permissions']) == {'files'}, 'Only files permission is permitted'
        assert manifest['copyright'] == ['2026 Blank Glyph']
        assert manifest['website'] == 'https://github.com/cheinu-mike/vg-rules'
        payload['__init__.py'] = build_extension.extension_init(payload['__init__.py'])
        payload['QUICK_START.txt'] = payload['QUICK_START.txt'].replace(b'@VERSION@', version.encode())
        build_extension.verify_archive(archive, payload, metadata)
        build_addon.verify_archive(legacy, {f'vg_rules/{n}': (source / n).read_bytes() for n in build_addon.FILES}, metadata)
        assert (source / 'COPYING.txt').read_bytes() == (root / 'LICENSE').read_bytes()
        for name in build_addon.FILES:
            if name.endswith('.py'):
                assert b'SPDX-License-Identifier: GPL-3.0-or-later' in (source / name).read_bytes()
                assert b'Copyright (C) 2026 Blank Glyph' in (source / name).read_bytes()
        static.append('PASS: exact source parity, matching metadata/credits, GPL notices, files-only permission; eight text files in extension, six in legacy installer; no bundled artwork/fonts/binaries')
    except (AssertionError, ValueError, OSError) as error:
        blockers.append(f'Package/source/licensing verification: {error}')
    records = []
    for path in sorted(evidence.rglob('result.json')):
        try:
            records.append(json.loads(path.read_text(encoding='utf-8')))
        except (OSError, ValueError) as error:
            blockers.append(f'Unreadable evidence {path.name}: {error}')
    gui_path = root / 'submission/gui-results.json'
    try:
        gui = json.loads(gui_path.read_text(encoding='utf-8')).get('results', []) if gui_path.exists() else []
    except (OSError, ValueError) as error:
        gui = []
        blockers.append(f'Unreadable GUI evidence: {error}')
    matrix, local, failures = evaluate(records, gui, archive_hash, legacy_hash)
    blockers += failures
    if os.environ.get('GITHUB_SHA'):
        if any(r.get('github_sha') != os.environ['GITHUB_SHA'] for r in records):
            blockers.append('Hosted results must all come from this workflow source revision')
    for record in gui:
        for image in record.get('images', {}).values():
            path = root / image.get('file', '')
            if not path.is_file() or not path.resolve().is_relative_to(root / 'submission') or digest(path) != image.get('sha256'):
                blockers.append(f'GUI image evidence missing or stale: {image.get("file")}')
    try:
        capture = json.loads((root / 'submission/capture.json').read_text(encoding='utf-8'))
        assert capture['status'] == 'PASS' and capture['zip_sha256'] == archive_hash, 'Product captures checked another ZIP'
        assert capture['extension_version'] == version
        assert {'preview', 'apply', 'thumbnail'} <= set(capture['images'])
        for label, image in capture['images'].items():
            path = root / image['path']
            assert path.resolve().is_relative_to(root / 'submission/images')
            assert digest(path) == image['sha256'], f'{label} image changed'
        assert capture['images']['thumbnail']['sha256'] == '21047f3d94413fee5949e5eada902b6c3d31e572d837d233753da3680ff2632e'
        for name in ('README.md', 'docs/installation.md', 'docs/usage.md', 'docs/migration.md',
                     'docs/troubleshooting.md', 'docs/verification.md', 'submission/LISTING.md'):
            text = (root / name).read_text(encoding='utf-8')
            assert text.strip(), f'{name} empty'
        static.append('PASS: final-archive synthetic Preview/Apply captures, unchanged cube thumbnail, public guides and listing present')
    except (AssertionError, KeyError, OSError, ValueError) as error:
        blockers.append(f'Submission materials: {error}')
    run_id = os.environ.get('GITHUB_RUN_ID')
    run_url = f'https://github.com/cheinu-mike/vg-rules/actions/runs/{run_id}' if run_id else None
    return {'schema_version': 1, 'generated_utc': datetime.now(timezone.utc).isoformat(),
            'version': version, 'submission_ready': not blockers,
            'extension': {'path': archive.relative_to(root).as_posix(), 'sha256': archive_hash},
            'gumroad': {'path': legacy.relative_to(root).as_posix(), 'sha256': legacy_hash},
            'workflow_run': run_url, 'matrix': matrix, 'local_gui': local, 'static_checks': static,
            'unsupported': [{'platform': 'macos-x64', 'blender': '5.2.0',
                             'reason': 'No official Intel distribution; user accepted Intel checks on 4.2.0 and 4.2.23'}],
            'blockers': blockers,
            'scope': ['Headless checks on every required hosted platform; local GUI checks on Windows only',
                      'Update uses a synthetic previous-version package with a marker, followed by a real process restart',
                      'Runtime tests are offline and block Python socket/URL entry points; not an OS firewall trace',
                      'Legacy migration uses generated saved mixed-list rules and JSON, not personal projects',
                      'Platform upload and moderation are subsequent release steps']}


def markdown(report):
    lines = ['# VG Rules compliance report', '',
             f'Version: **{report["version"]}**. Submission-ready: **{"YES" if report["submission_ready"] else "NO"}**.',
             f'Generated UTC: {report["generated_utc"]}', '',
             f'Extension SHA-256: `{report["extension"]["sha256"]}`',
             f'Gumroad SHA-256: `{report["gumroad"]["sha256"]}`', '']
    if report.get('workflow_run'):
        lines += [f'[Hosted verification run]({report["workflow_run"]})', '']
    lines += ['| Platform | Blender | Actual result |', '| --- | --- | --- |']
    lines += [f'| {r["platform"]} | {r["blender"]} | {r["status"]} |' for r in report['matrix']]
    lines += ['| macos-x64 | 5.2.0 | Unsupported; no official build |', '', 'Local native GUI checks:', '']
    lines += [f'- Windows / {r["blender"]}: {r["status"]}' for r in report['local_gui']]
    lines += ['', 'Package and submission materials:', ''] + ['- ' + s for s in report['static_checks']]
    lines += ['', 'Verification scope:', ''] + ['- ' + s for s in report['scope']]
    if report['blockers']:
        lines += ['', 'Release blockers:', ''] + ['- ' + s for s in report['blockers']]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-ready', action='store_true')
    args = parser.parse_args()
    report = collect(ROOT, args.evidence.resolve())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'compliance.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    text = markdown(report)
    (args.output / 'COMPLIANCE.md').write_text(text, encoding='utf-8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a', encoding='utf-8') as stream:
            stream.write(text)
    print(f'Submission-ready: {report["submission_ready"]}; blockers: {len(report["blockers"])}')
    return 1 if args.require_ready and not report['submission_ready'] else 0


if __name__ == '__main__':
    raise SystemExit(main())

