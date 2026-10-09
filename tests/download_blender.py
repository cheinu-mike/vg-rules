# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Download checksum-pinned official Blender distributions for tests only."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from zipfile import ZipFile


def platform_id():
    system = {'Windows': 'windows', 'Linux': 'linux', 'Darwin': 'macos'}[platform.system()]
    arch = {'AMD64': 'x64', 'x86_64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}[platform.machine()]
    return f'{system}-{arch}'


def download(version, directory):
    target = platform_id()
    checksums = json.loads(Path(__file__).with_name('blender_downloads.json').read_text())
    if target not in checksums[version]:
        raise ValueError(f'No pinned official Blender {version} distribution for {target}')
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    suffix = '.zip' if target.startswith('windows') else '.tar.xz' if target.startswith('linux') else '.dmg'
    filename = f'blender-{version}-{target}{suffix}'
    url = f'https://download.blender.org/release/Blender{".".join(version.split(".")[:2])}/{filename}'
    archive = directory / filename
    expected = checksums[version][target]
    cached = None
    if archive.exists():
        with archive.open('rb') as stream:
            cached = hashlib.file_digest(stream, 'sha256').hexdigest()
    if cached != expected:
        subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--max-time', '600',
                        '--output', str(archive), url], check=True)
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
            raise ValueError('Official Blender archive checksum mismatch')
    if target.startswith('windows'):
        with ZipFile(archive) as package:
            assert all((directory / name).resolve().is_relative_to(directory) for name in package.namelist())
            package.extractall(directory)
        executable = directory / filename.removesuffix('.zip') / 'blender.exe'
    elif target.startswith('linux'):
        subprocess.run(['tar', '-xf', str(archive), '-C', str(directory)], check=True)
        executable = directory / filename.removesuffix('.tar.xz') / 'blender'
    else:
        mount = directory / 'mount'
        mount.mkdir(exist_ok=True)
        subprocess.run(['hdiutil', 'attach', str(archive), '-readonly', '-nobrowse', '-mountpoint', str(mount)], check=True)
        try:
            subprocess.run(['ditto', str(mount / 'Blender.app'), str(directory / 'Blender.app')], check=True)
        finally:
            subprocess.run(['hdiutil', 'detach', str(mount)], check=True)
        executable = directory / 'Blender.app/Contents/MacOS/Blender'
    assert executable.is_file()
    return executable


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True, choices=('4.2.0', '4.2.23', '5.2.0'))
    parser.add_argument('--directory', required=True, type=Path)
    args = parser.parse_args()
    executable = download(args.version, args.directory)
    print(executable)
    if os.environ.get('GITHUB_ENV'):
        with Path(os.environ['GITHUB_ENV']).open('a', encoding='utf-8') as environment:
            environment.write(f'VGR_BLENDER={executable}\n')
