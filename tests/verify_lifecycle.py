# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Real install, legacy migration, update/restart and uninstall/restart phases."""

import hashlib
import json
import os
from pathlib import Path
import sys
from zipfile import ZipFile

import bpy


PROFILE = Path(os.environ['VGR_EXTENSION_TEST_DIR']).resolve()
assert PROFILE.is_relative_to(Path(os.environ['VGR_TEST_RUN_ROOT']).resolve())
assert not bpy.app.online_access
PHASE = os.environ['VGR_LIFECYCLE_PHASE']
NAMESPACE = os.environ['VGR_TEST_NAMESPACE']
MODULE = f'bl_ext.{NAMESPACE}.vg_rules'
ZIP = Path(os.environ['VGR_TEST_ARCHIVE']).resolve()
LEGACY = Path(os.environ['VGR_TEST_LEGACY_ARCHIVE']).resolve()
INSTALLED = PROFILE / 'extensions' / NAMESPACE / 'vg_rules'
BLEND = PROFILE / 'saved_rules.blend'
BACKUP = PROFILE / 'saved_rules.json'
STATE = PROFILE / 'lifecycle.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parity(archive_path, directory, legacy=False):
    with ZipFile(archive_path) as archive:
        for name in archive.namelist():
            target = name.removeprefix('vg_rules/') if legacy else name
            assert (directory / target).read_bytes() == archive.read(name), target


def repository():
    repo = next((item for item in bpy.context.preferences.extensions.repos if item.module == NAMESPACE), None)
    if repo is None:
        directory = INSTALLED.parent
        directory.mkdir(parents=True, exist_ok=True)
        repo = bpy.context.preferences.extensions.repos.new(
            name='VG Rules lifecycle', module=NAMESPACE, custom_directory=str(directory))
        repo.use_remote_url = False
    assert not repo.use_remote_url and Path(repo.directory).resolve() == INSTALLED.parent
    return repo


def install(archive=ZIP):
    repo = repository()
    assert bpy.ops.extensions.package_install_files(
        filepath=str(archive), repo=repo.module, enable_on_install=True) == {'FINISHED'}
    parity(archive, INSTALLED)
    addon = sys.modules[MODULE]
    assert Path(addon.__file__).resolve().parent == INSTALLED and addon.__package__ == MODULE
    assert addon.owns_scene_property()
    return addon


def uninstall():
    repo = repository()
    index = list(bpy.context.preferences.extensions.repos).index(repo)
    assert bpy.ops.extensions.package_uninstall(repo_index=index, pkg_id='vg_rules') == {'FINISHED'}
    assert not INSTALLED.exists() and MODULE not in bpy.context.preferences.addons
    assert not hasattr(bpy.types.Scene, 'vgr_settings')


def check_saved(addon):
    state = json.loads(STATE.read_text())
    assert digest(BLEND) == state['blend_sha256'] and digest(BACKUP) == state['json_sha256']
    assert bpy.ops.wm.open_mainfile(filepath=str(BLEND)) == {'FINISHED'}
    addon.initialize_pending_scenes()
    assert addon.export_rules(bpy.context.scene) == state['rules']
    assert not bpy.context.scene.vgr_settings.rules[1].enabled
    assert bpy.context.scene.vgr_settings.rules[0].target == bpy.context.scene.objects['Migration Cube']
    before = snapshot()
    assert bpy.ops.vgr.preview(scope='ALL') == {'FINISHED'}
    assert snapshot() == before
    restored = PROFILE / f'{PHASE}_backup.json'
    assert bpy.ops.vgr.export_rules(filepath=str(restored)) == {'FINISHED'}
    assert json.loads(restored.read_text()) == state['rules']
    addon.load_rules(bpy.context.scene, {})
    assert bpy.ops.vgr.import_rules(filepath=str(BACKUP)) == {'FINISHED'}
    assert addon.export_rules(bpy.context.scene) == state['rules']
    assert digest(BLEND) == state['blend_sha256'] and digest(BACKUP) == state['json_sha256']


def snapshot():
    return {obj.name: ([(g.name, g.lock_weight) for g in obj.vertex_groups],
                       [[(i.group, i.weight) for i in v.groups] for v in obj.data.vertices],
                       [(m.name, m.type, m.use_mirror_vertex_groups) for m in obj.modifiers if m.type == 'MIRROR'])
            for obj in bpy.context.scene.objects if obj.type == 'MESH'}


if PHASE == 'legacy':
    # Exercise the real legacy installer, without accidentally importing checkout source.
    root = Path(__file__).resolve().parents[1]
    sys.path[:] = [p for p in sys.path if Path(p or os.getcwd()).resolve() != root]
    assert bpy.ops.preferences.addon_install(filepath=str(LEGACY)) == {'FINISHED'}
    assert bpy.ops.preferences.addon_enable(module='vg_rules') == {'FINISHED'}
    addon = sys.modules['vg_rules']
    folder = Path(addon.__file__).resolve().parent
    assert folder.is_relative_to(PROFILE) and folder.name == 'vg_rules'
    parity(LEGACY, folder, legacy=True)
    cube = bpy.context.scene.objects['Cube']
    cube.name = 'Migration Cube'
    cube.modifiers.new('Migration Mirror', 'MIRROR').use_mirror_vertex_groups = False
    for name in ('KeepOriginal', 'RemoveTemp', 'MigrationWeight.R'):
        cube.vertex_groups.new(name=name).add(list(range(8)), 0.25, 'REPLACE')
    cube.vertex_groups['MigrationWeight.R'].lock_weight = True
    bpy.ops.mesh.primitive_cube_add()
    disabled = bpy.context.object
    disabled.name = 'Migration Disabled'
    addon.load_rules(bpy.context.scene, {
        cube.name: {'keep_only_prefixes': ['Keep'], 'keep_case_sensitive': True,
                    'delete_exact': ['RemoveTemp'], 'assign_all_vertices': [
                        {'group': 'MigrationWeight', 'side': 'L', 'mirror': True}]},
        disabled.name: {'enabled': False, 'assign_all_vertices': ['DisabledWeight']}})
    expected = addon.export_rules(bpy.context.scene)
    assert bpy.ops.vgr.export_rules(filepath=str(BACKUP)) == {'FINISHED'}
    # Save an older mixed-list representation to exercise .blend data migration.
    rule = bpy.context.scene.vgr_settings.rules[0]
    rule.keep_patterns.clear()
    rule.delete_patterns.clear()
    for kind, text in (('keep_only_prefixes', 'Keep'), ('delete_exact', 'RemoveTemp')):
        entry = rule.patterns.add()
        entry.kind, entry.value = kind, text
    rule.pattern_lists_split = False
    assert bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), check_existing=False) == {'FINISHED'}
    STATE.write_text(json.dumps({'rules': expected, 'blend_sha256': digest(BLEND),
                                'json_sha256': digest(BACKUP)}, indent=2), encoding='utf-8')
    assert bpy.ops.preferences.addon_disable(module='vg_rules') == {'FINISHED'}
    # Blender's removal operator redraws an editor even in background mode.
    window = next(iter(bpy.context.window_manager.windows))
    with bpy.context.temp_override(window=window, area=window.screen.areas[0]):
        assert bpy.ops.preferences.addon_remove(module='vg_rules') == {'FINISHED'}
    assert not folder.exists() and not hasattr(bpy.types.Scene, 'vgr_settings')
elif PHASE == 'migration':
    addon = install()
    check_saved(addon)
elif PHASE == 'migration_restart_old':
    assert MODULE in bpy.context.preferences.addons and MODULE in sys.modules
    addon = sys.modules[MODULE]
    parity(ZIP, INSTALLED)
    check_saved(addon)
    uninstall()
    old = Path(os.environ['VGR_TEST_OLD_ARCHIVE'])
    addon = install(old)
    assert addon.VGR_UPDATE_TEST_MARKER == 'synthetic previous installation'
elif PHASE == 'update':
    assert MODULE in bpy.context.preferences.addons and MODULE in sys.modules
    assert sys.modules[MODULE].VGR_UPDATE_TEST_MARKER == 'synthetic previous installation'
    install()
    # Module caching before restart is allowed; disk bytes must be the final ZIP.
elif PHASE == 'updated_restart_uninstall':
    assert MODULE in bpy.context.preferences.addons and MODULE in sys.modules
    addon = sys.modules[MODULE]
    assert not hasattr(addon, 'VGR_UPDATE_TEST_MARKER')
    parity(ZIP, INSTALLED)
    check_saved(addon)
    assert bpy.ops.preferences.addon_disable(module=MODULE) == {'FINISHED'}
    assert not hasattr(bpy.types.Scene, 'vgr_settings')
    assert bpy.ops.preferences.addon_enable(module=MODULE) == {'FINISHED'}
    assert addon.owns_scene_property()
    uninstall()
elif PHASE == 'uninstalled_restart':
    assert not INSTALLED.exists() and MODULE not in bpy.context.preferences.addons
    assert not hasattr(bpy.types.Scene, 'vgr_settings')
    state = json.loads(STATE.read_text())
    assert digest(BLEND) == state['blend_sha256'] and digest(BACKUP) == state['json_sha256']
else:
    raise ValueError(PHASE)
assert not bpy.app.online_access
assert bpy.ops.wm.save_userpref() == {'FINISHED'}
print('VGR_LIFECYCLE_PASS', PHASE)
