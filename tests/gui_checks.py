# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Local GUI checks with real dialog clicks and Undo in a synthetic saved scene.

The session pauses at its warning dialog. Inspect warning.png, then place a
command.json in the printed evidence directory: {"action": "cancel" or
"continue", "x": window_x, "y": window_y, "visual_review": true}.
Coordinates use Blender's bottom-left window origin. Only this test session
and its disposable profile are changed. Logs/screenshots persist as evidence.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import traceback
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def launch():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from run_blender import environment
    release = tomllib.loads((ROOT / 'vg_rules/blender_manifest.toml').read_text())
    args.archive = ROOT / f'dist/blender_extensions/vg_rules-{release["version"]}.zip'
    args.legacy_archive = ROOT / f'dist/vg_rules-{release["version"]}.zip'
    base = ROOT / 'tests/.artifacts'
    base.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vgr-gui-', dir=base) as temporary:
        run = Path(temporary).resolve()
        profile = run / 'profile'
        env = environment(profile, run, args)
        env.update(VGR_GUI_OUTPUT=str(output), VGR_LIFECYCLE_PHASE='legacy')
        options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        fixture = subprocess.run([str(args.blender), '--background', '--factory-startup', '--offline-mode',
                                  '--python-exit-code', '1', '--python', str(ROOT / 'tests/verify_lifecycle.py')],
                                 cwd=profile, env=env, capture_output=True, text=True, timeout=60, **options)
        (output / 'legacy.stdout.txt').write_text(fixture.stdout, encoding='utf-8')
        (output / 'legacy.stderr.txt').write_text(fixture.stderr, encoding='utf-8')
        if fixture.returncode:
            raise RuntimeError(f'GUI migration fixture failed; see {output}')
        options = {}
        if os.name == 'nt':
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = subprocess.SW_HIDE
            options['startupinfo'] = startup
        command = [str(args.blender), '--factory-startup', '--offline-mode', '--enable-event-simulate',
                   '--window-geometry', '0', '0', '1800', '1100', '--python-exit-code', '1',
                   '--python', str(Path(__file__).resolve()), '--', '--inside-blender']
        print(f'GUI evidence and dialog command directory: {output}', flush=True)
        with (output / 'stdout.txt').open('w', encoding='utf-8') as stdout, \
             (output / 'stderr.txt').open('w', encoding='utf-8') as stderr:
            result = subprocess.run(command, cwd=profile, env=env, stdout=stdout, stderr=stderr, timeout=300, **options)
        if result.returncode or not (output / 'result.json').exists():
            raise RuntimeError(f'GUI checks failed; see {output}')
        report = json.loads((output / 'result.json').read_text())
        if report['status'] != 'PASS' or 'Traceback (most recent call last)' in (output / 'stderr.txt').read_text():
            raise RuntimeError(f'GUI checks reported failure; see {output}')
        print('PASS: actual dialog Cancel/Continue, Undo, warning layout and legacy .blend/JSON migration', flush=True)


def inside():
    import bpy
    from mathutils import Quaternion

    sys.dont_write_bytecode = True
    output = Path(os.environ['VGR_GUI_OUTPUT'])
    profile = Path(os.environ['VGR_EXTENSION_TEST_DIR'])
    archive = Path(os.environ['VGR_TEST_ARCHIVE'])
    namespace = os.environ['VGR_TEST_NAMESPACE']
    module_name = f'bl_ext.{namespace}.vg_rules'
    original = json.loads((profile / 'lifecycle.json').read_text())
    report = {'status': 'FAIL', 'blender': '.'.join(map(str, bpy.app.version)), 'platform': 'windows-x64',
              'archive_sha256': digest(archive), 'checks': [], 'images': {}}
    session = {}
    for library in list(bpy.context.preferences.filepaths.asset_libraries):
        bpy.context.preferences.filepaths.asset_libraries.remove(library)

    def later(function, interval=1.5):
        def guarded():
            try:
                function()
            except Exception:
                report['error'] = traceback.format_exc()
                (output / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
                traceback.print_exc()
                bpy.ops.wm.quit_blender()
            return None
        bpy.app.timers.register(guarded, first_interval=interval)

    def viewport():
        return next(a for a in bpy.context.window.screen.areas if a.type == 'VIEW_3D')

    def context():
        area = viewport()
        return bpy.context.temp_override(area=area, region=next(r for r in area.regions if r.type == 'WINDOW'))

    def snapshot():
        return {obj.name: ([(g.name, g.lock_weight) for g in obj.vertex_groups],
                           [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices],
                           [(m.name, m.type, m.use_mirror_vertex_groups) for m in obj.modifiers if m.type == 'MIRROR'])
                for obj in bpy.data.objects if obj.type == 'MESH'}

    def check(name):
        report['checks'].append({'name': name, 'status': 'PASS'})

    def capture(label):
        path = output / f'{label}.png'
        with context():
            assert bpy.ops.screen.screenshot_area(filepath=str(path), hide_props_region=False) == {'FINISHED'}
        area = viewport()
        report['images'][label] = {'file': path.name, 'sha256': digest(path),
                                   'area': [area.x, area.y, area.width, area.height]}

    def prepare():
        assert not bpy.app.online_access
        directory = profile / 'extensions' / namespace
        directory.mkdir(parents=True, exist_ok=True)
        repo = bpy.context.preferences.extensions.repos.new(name='VG Rules GUI', module=namespace, custom_directory=str(directory))
        repo.use_remote_url = False
        assert bpy.ops.extensions.package_install_files(filepath=str(archive), repo=namespace, enable_on_install=True) == {'FINISHED'}
        addon = sys.modules[module_name]
        with ZipFile(archive) as package:
            for name in package.namelist():
                assert (directory / 'vg_rules' / name).read_bytes() == package.read(name)
        assert bpy.ops.wm.open_mainfile(filepath=str(profile / 'saved_rules.blend'), load_ui=False) == {'FINISHED'}
        # File loading replaces ID context; resume after Blender restores the GUI window.
        later(prepare_scene, 2)

    def prepare_scene():
        addon = sys.modules[module_name]
        addon.initialize_pending_scenes()
        assert addon.export_rules(bpy.context.scene) == original['rules']
        assert all(r.pattern_lists_split for r in bpy.context.scene.vgr_settings.rules)
        check('legacy_saved_blend_migration')
        addon.load_rules(bpy.context.scene, {})
        assert bpy.ops.vgr.import_rules(filepath=str(profile / 'saved_rules.json')) == {'FINISHED'}
        assert addon.export_rules(bpy.context.scene) == original['rules']
        check('legacy_json_backup_migration')
        scene = bpy.context.scene
        scene.name = 'GUI Primary Scene with a long descriptive display name'
        other = bpy.data.scenes.new('GUI Second Scene with a long descriptive display name')
        obj = scene.objects['Migration Cube']
        obj.name = 'GUI Shared Target with a long descriptive display name'
        other.collection.objects.link(obj)
        alias = obj.copy()
        alias.name = 'GUI Shared Alias with a long descriptive display name'
        other.collection.objects.link(alias)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        session['target_name'] = obj.name
        session['names'] = [obj.name, alias.name, scene.name, other.name]
        session['before'] = snapshot()
        bpy.context.scene.vgr_settings.rule_index = 0
        assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
        assert snapshot() == session['before']
        warning = next(line.message for line in bpy.context.scene.vgr_settings.log if line.kind == 'WARNING')
        assert all(name in warning for name in session['names'])
        with context():
            bpy.ops.screen.screen_full_area(use_hide_panels=False)
        area = viewport()
        area.spaces.active.show_region_ui = True
        area.spaces.active.show_region_toolbar = False
        area.spaces.active.region_3d.view_rotation = Quaternion((0.882, 0.414, -0.094, -0.208)).normalized()
        area.spaces.active.region_3d.view_distance = 8
        bpy.context.preferences.view.ui_scale = 0.9
        bpy.context.preferences.system.use_region_overlap = False
        later(activate)

    def activate():
        area = viewport()
        ui = next(r for r in area.regions if r.type == 'UI')
        ui.active_panel_category = 'VG Rules'
        session['drag'] = [ui.x, ui.y + ui.height // 2]
        bpy.context.window.event_simulate(type='MOUSEMOVE', value='NOTHING', x=ui.x, y=session['drag'][1])
        later(press, 0.5)

    def press():
        x, y = session['drag']
        bpy.context.window.event_simulate(type='LEFTMOUSE', value='PRESS', x=x, y=y)
        later(start_drag, 0.5)

    def start_drag():
        x, y = session['drag']
        bpy.context.window.event_simulate(type='MOUSEMOVE', value='NOTHING', x=x - 25, y=y)
        later(drag, 0.5)

    def drag():
        x, y = session['drag']
        bpy.context.window.event_simulate(type='MOUSEMOVE', value='NOTHING', x=viewport().width - 640, y=y)
        later(release, 0.5)

    def release():
        bpy.context.window.event_simulate(type='LEFTMOUSE', value='RELEASE', x=viewport().width - 640, y=session['drag'][1])
        bpy.context.window.event_simulate(type='MOUSEMOVE', value='NOTHING', x=550, y=600)
        later(dialog)

    def dialog():
        with context():
            assert bpy.ops.ed.undo_push(message='VG Rules GUI before Apply') == {'FINISHED'}
            assert bpy.ops.vgr.apply('INVOKE_DEFAULT', scope='ALL') == {'RUNNING_MODAL'}
        session['expected_action'] = 'cancel'
        later(ready)

    def ready():
        capture('warning' if session['expected_action'] == 'cancel' else 'confirmation')
        (output / 'waiting.json').write_text(json.dumps({'action': session['expected_action'],
                                                       'images': report['images'], 'names': session['names']}, indent=2), encoding='utf-8')
        later(poll_command, 0.3)

    def poll_command():
        path = output / 'command.json'
        if not path.exists():
            later(poll_command, 0.3)
            return
        command = json.loads(path.read_text())
        path.unlink()
        assert command['action'] == session['expected_action'] and command['visual_review']
        x, y = command['x'], command['y']
        bpy.context.window.event_simulate(type='MOUSEMOVE', value='NOTHING', x=x, y=y)
        bpy.context.window.event_simulate(type='LEFTMOUSE', value='PRESS', x=x, y=y)
        bpy.context.window.event_simulate(type='LEFTMOUSE', value='RELEASE', x=x, y=y)
        later(cancelled if command['action'] == 'cancel' else continued)

    def cancelled():
        assert not any(op.bl_idname == 'VGR_OT_apply' for op in bpy.context.window.modal_operators)
        assert snapshot() == session['before']
        check('cancel_preserves_groups_weights_modifiers')
        check('warning_layout_reviewed')
        capture('cancelled')
        bpy.context.window.event_simulate(type='MOUSEMOVE', value='NOTHING', x=550, y=600)
        later(confirm_again, 0.5)

    def confirm_again():
        with context():
            assert bpy.ops.vgr.apply('INVOKE_DEFAULT', scope='ALL') == {'RUNNING_MODAL'}
        session['expected_action'] = 'continue'
        later(ready)

    def continued():
        assert not any(op.bl_idname == 'VGR_OT_apply' for op in bpy.context.window.modal_operators)
        assert bpy.context.scene.vgr_settings.status.startswith('Applied 1 rule(s)')
        obj = bpy.context.scene.objects[session['target_name']]
        assert obj.vertex_groups.get('RemoveTemp') is None
        assert all(obj.vertex_groups['MigrationWeight.L'].weight(v.index) == 1.0 for v in obj.data.vertices)
        opposite = obj.vertex_groups['MigrationWeight.R'].index
        assert all(all(item.group != opposite for item in v.groups) for v in obj.data.vertices)
        assert obj.vertex_groups['MigrationWeight.R'].lock_weight
        assert obj.modifiers['Migration Mirror'].use_mirror_vertex_groups
        assert snapshot() != session['before']
        check('continue_applies_confirmed_changes')
        capture('continued')
        bpy.context.window.event_simulate(type='MOUSEMOVE', value='NOTHING', x=550, y=600)
        later(undo_key, 0.5)

    def undo_key():
        bpy.context.window.event_simulate(type='Z', value='PRESS', ctrl=True)
        bpy.context.window.event_simulate(type='Z', value='RELEASE', ctrl=True)
        later(undone, 2)

    def undone():
        assert snapshot() == session['before'], 'Undo must restore every shared user and modifier'
        check('undo_restores_groups_weights_modifiers')
        assert digest(profile / 'saved_rules.blend') == original['blend_sha256']
        assert digest(profile / 'saved_rules.json') == original['json_sha256']
        check('migration_backups_unchanged')
        capture('undo')
        report['status'] = 'PASS'
        (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        bpy.ops.wm.quit_blender()

    later(prepare, 3)


if __name__ == '__main__':
    inside() if '--inside-blender' in sys.argv else launch()
