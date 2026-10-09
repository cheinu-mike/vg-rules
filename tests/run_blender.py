# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Run source, installed ZIP and restart lifecycle checks in temporary profiles."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import time
import tomllib
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]

def platform_id():
    system = {'Windows': 'windows', 'Linux': 'linux', 'Darwin': 'macos'}[platform.system()]
    arch = {'AMD64': 'x64', 'x86_64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}[platform.machine()]
    return f'{system}-{arch}'

def environment(profile, run, args):
    result = os.environ.copy()
    result.update(PYTHONDONTWRITEBYTECODE='1', BLENDER_USER_RESOURCES=str(profile),
                  VGR_TEST_RUN_ROOT=str(run), VGR_EXTENSION_TEST_DIR=str(profile),
                  VGR_TEST_ARTIFACT_DIR=str(profile / 'fixtures'),
                  VGR_TEST_ARCHIVE=str(args.archive), VGR_TEST_LEGACY_ARCHIVE=str(args.legacy_archive),
                  VGR_TEST_NAMESPACE='qa_rules_' + run.name.replace('-', '_'))
    profile.mkdir(parents=True, exist_ok=True)
    for key, name in (('BLENDER_USER_CONFIG', 'config'), ('BLENDER_USER_SCRIPTS', 'scripts'),
                      ('BLENDER_USER_DATAFILES', 'datafiles'), ('BLENDER_USER_EXTENSIONS', 'extensions')):
        (profile / name).mkdir(exist_ok=True)
        result[key] = str(profile / name)
    return result

def main():
    release = tomllib.loads((ROOT / 'vg_rules/blender_manifest.toml').read_text(encoding='utf-8'))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', type=Path, required=True)
    parser.add_argument('--expect-version', choices=('4.2.0', '4.2.23', '5.2.0'))
    parser.add_argument('--archive', type=Path, default=ROOT / f'dist/blender_extensions/vg_rules-{release["version"]}.zip')
    parser.add_argument('--legacy-archive', type=Path, default=ROOT / f'dist/vg_rules-{release["version"]}.zip')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    for name in ('blender', 'archive', 'legacy_archive'):
        path = getattr(args, name).expanduser().resolve()
        if not path.is_file():
            parser.error(f'Missing {name}: {path}')
        setattr(args, name, path)
    identity = platform_id()
    output = (args.output_dir or ROOT / f'tests/.artifacts/{identity}-{args.expect_version or "local"}').resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {'status': 'FAIL', 'platform': identity, 'expected_blender': args.expect_version,
              'archive_sha256': hashlib.sha256(args.archive.read_bytes()).hexdigest(),
              'legacy_sha256': hashlib.sha256(args.legacy_archive.read_bytes()).hexdigest(),
              'checks': [], 'github_sha': os.environ.get('GITHUB_SHA')}
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    try:
        base = Path(os.environ.get('RUNNER_TEMP', ROOT / 'tests/.artifacts'))
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='vgr-', dir=base) as temporary:
            run = Path(temporary).resolve()

            def invoke(name, profile, script=None, *, factory=True, extra_env=None, expression=None):
                env = environment(profile, run, args)
                env.update(extra_env or {})
                command = [str(args.blender), '--background', '--offline-mode', '--python-exit-code', '1']
                if factory:
                    command.append('--factory-startup')
                if script == 'validate':
                    command += ['--command', 'extension', 'validate', str(args.archive)]
                else:
                    command += ['--python-expr', expression] if expression else ['--python', str(ROOT / 'tests' / script)]
                started = time.monotonic()
                try:
                    result = subprocess.run(command, cwd=profile, env=env, capture_output=True, text=True,
                                            encoding='utf-8', errors='replace', timeout=300, **options)
                except subprocess.TimeoutExpired as error:
                    report['checks'].append({'name': name, 'status': 'FAIL', 'reason': '300-second process timeout'})
                    raise RuntimeError(f'{name} timed out') from error
                (output / f'{name}.stdout.txt').write_text(result.stdout, encoding='utf-8')
                (output / f'{name}.stderr.txt').write_text(result.stderr, encoding='utf-8')
                check = {'name': name, 'status': 'PASS' if result.returncode == 0 else 'FAIL',
                         'seconds': round(time.monotonic() - started, 2), 'exit_code': result.returncode}
                report['checks'].append(check)
                if result.returncode:
                    print(result.stdout[-12000:])
                    print(result.stderr[-12000:])
                    raise RuntimeError(f'{name} failed')
                return result.stdout

            probe = "import bpy,json,platform; print('VGR_PROBE '+json.dumps({'version':'.'.join(map(str,bpy.app.version)), 'architecture':platform.machine(), 'offline':not bpy.app.online_access}))"
            stdout = invoke('version', run / 'probe', expression=probe)
            details = json.loads(next(line.removeprefix('VGR_PROBE ') for line in stdout.splitlines() if line.startswith('VGR_PROBE ')))
            assert details['offline'] and (not args.expect_version or details['version'] == args.expect_version), details
            expected_arch = 'arm64' if identity.endswith('arm64') else 'x64'
            assert {'AMD64': 'x64', 'x86_64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}[details['architecture']] == expected_arch
            report['blender'] = details['version']
            report['blender_architecture'] = details['architecture']
            invoke('official_validation', run / 'validation', 'validate')
            for script, marker in (('verify_addon', 'ALL ADD-ON INTEGRATION CHECKS PASSED'),
                                   ('verify_runtime', 'ALL RUNTIME COMPLIANCE CHECKS PASSED'),
                                   ('verify_extension', '"status": "PASS"')):
                stdout = invoke(script, run / script, f'{script}.py')
                if marker not in stdout:
                    report['checks'][-1]['status'] = 'FAIL'
                    raise RuntimeError(f'{script} did not report completion')
                if script == 'verify_extension':
                    installed = json.loads((run / 'verify_extension_results.json').read_text(encoding='utf-8'))
                    assert installed['sha256'] == report['archive_sha256'] and installed['status'] == 'PASS'
                    report['installed_checks'] = installed['checks']
                print(f'PASS: {script}', flush=True)
            lifecycle = run / 'lifecycle'
            lifecycle.mkdir()
            old_archive = lifecycle / 'synthetic_previous.zip'
            with ZipFile(args.archive) as original, ZipFile(old_archive, 'w', compression=ZIP_DEFLATED) as old:
                for name in original.namelist():
                    payload = original.read(name)
                    if name == 'blender_manifest.toml':
                        payload = payload.replace(f'version = "{release["version"]}"'.encode(), b'version = "0.0.1"')
                    elif name == '__init__.py':
                        payload += b'\nVGR_UPDATE_TEST_MARKER = "synthetic previous installation"\n'
                    old.writestr(name, payload)
            for phase in ('legacy', 'migration', 'migration_restart_old', 'update',
                          'updated_restart_uninstall', 'uninstalled_restart'):
                stdout = invoke(f'lifecycle_{phase}', lifecycle, 'verify_lifecycle.py', factory=phase == 'legacy',
                                extra_env={'VGR_LIFECYCLE_PHASE': phase, 'VGR_TEST_OLD_ARCHIVE': str(old_archive)})
                assert f'VGR_LIFECYCLE_PASS {phase}' in stdout
                print(f'PASS: lifecycle {phase}', flush=True)
            report['status'] = 'PASS'
    except Exception as error:
        report['error'] = str(error)
        print(f'FAIL: {error}', flush=True)
    finally:
        (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'{report["status"]}: Blender verification; evidence: {output}', flush=True)
    return 0 if report['status'] == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
