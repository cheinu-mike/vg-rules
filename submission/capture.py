# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Capture genuine Preview/Apply screenshots from the built extension, offline.

Run with Python 3.11+: python submission/capture.py --blender /path/to/blender
Only the child Blender session imports bpy. Profiles and intermediate output
stay in ignored tests/.artifacts; successful captures go to submission/images.
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
import tomllib
import traceback
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "submission/images"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def launch():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True, type=Path)
    args = parser.parse_args()
    artifacts = ROOT / "tests/.artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix="submission-", dir=artifacts)).resolve()
    environment = os.environ.copy()
    environment["VGR_CAPTURE_PROFILE"] = str(profile)
    environment["BLENDER_USER_RESOURCES"] = str(profile)
    for key, directory in (("BLENDER_USER_CONFIG", "config"),
                           ("BLENDER_USER_SCRIPTS", "scripts"),
                           ("BLENDER_USER_DATAFILES", "datafiles"),
                           ("BLENDER_USER_EXTENSIONS", "extensions")):
        environment[key] = str(profile / directory)
        (profile / directory).mkdir(parents=True, exist_ok=True)
    options = {}
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        options["startupinfo"] = startup
    command = [str(args.blender.resolve()), "--factory-startup", "--offline-mode",
               "--enable-event-simulate", "--window-geometry", "0", "0", "1800", "1100",
               "--python-exit-code", "1", "--python", str(Path(__file__).resolve()), "--", "--inside-blender"]
    with (profile / "stdout.txt").open("w", encoding="utf-8") as out, \
         (profile / "stderr.txt").open("w", encoding="utf-8") as err:
        process = subprocess.run(command, env=environment, stdout=out, stderr=err, timeout=90, **options)
    if process.returncode or not (profile / "complete.json").is_file():
        raise RuntimeError(f"Capture failed; see {profile}")
    if "Traceback (most recent call last)" in (profile / "stderr.txt").read_text(encoding="utf-8"):
        raise RuntimeError(f"Blender reported a Python/UI error; see {profile}")
    # Publish only after the GUI session exits cleanly, with no draw errors.
    state = json.loads((profile / "complete.json").read_text(encoding="utf-8"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for label in ("preview", "apply"):
        shutil.copy2(profile / f"{label}.png", OUTPUT / f"{label}.png")
    (ROOT / "submission/capture.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"Captured Preview and Apply from the packaged extension; logs: {profile}")


def capture_in_blender():
    import bpy
    from mathutils import Quaternion, Vector

    sys.dont_write_bytecode = True
    # Clear any asset-library paths carried by the factory startup template.
    # This session uses generated geometry and needs no external library.
    for library in list(bpy.context.preferences.filepaths.asset_libraries):
        bpy.context.preferences.filepaths.asset_libraries.remove(library)
    profile = Path(os.environ["VGR_CAPTURE_PROFILE"]).resolve()
    assert profile.is_relative_to(ROOT / "tests/.artifacts")
    assert not bpy.app.online_access
    release = tomllib.loads((ROOT / "vg_rules/blender_manifest.toml").read_text(encoding="utf-8"))
    archive_path = ROOT / "dist/blender_extensions" / f'{release["id"]}-{release["version"]}.zip'
    state = {"status": "FAIL", "blender": bpy.app.version_string,
             "extension_version": release["version"], "zip": archive_path.relative_to(ROOT).as_posix(),
             "zip_sha256": sha256(archive_path), "scene": "VG Rules Synthetic Demo", "images": {}}
    values = {"Demo Shell": {"keep_only_prefixes": ["DEF-"], "keep_exact": ["cloth_pin"],
                             "delete_prefixes": ["MCH-"], "delete_contains": ["_backup"],
                             "assign_all_vertices": [{"group": "DEF-Demo", "side": "AUTO", "mirror": True}]}}
    state["preset"] = values
    session = {}

    def later(function, seconds=1.5):
        def guarded():
            try:
                function()
            except Exception:
                (profile / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
                traceback.print_exc()
                bpy.ops.wm.quit_blender()
            return None
        bpy.app.timers.register(guarded, first_interval=seconds)

    def area():
        return next(a for a in bpy.context.window.screen.areas if a.type == 'VIEW_3D')

    def context():
        viewport = area()
        return bpy.context.temp_override(area=viewport,
                                         region=next(r for r in viewport.regions if r.type == 'WINDOW'))

    def snapshot():
        obj = session["object"]
        return {group.name: [[vertex.index, item.weight]
                              for vertex in obj.data.vertices for item in vertex.groups
                              if item.group == group.index] for group in obj.vertex_groups}

    def prepare():
        repository = profile / "extensions/vgr_capture"
        repository.mkdir(parents=True, exist_ok=True)
        repo = bpy.context.preferences.extensions.repos.new(
            name="VG Rules capture", module="vgr_capture", custom_directory=str(repository))
        repo.use_remote_url = False
        assert bpy.ops.extensions.package_install_files(
            filepath=str(archive_path), repo=repo.module, enable_on_install=True) == {'FINISHED'}
        namespace = f"bl_ext.{repo.module}.vg_rules"
        module = sys.modules[namespace]
        installed = repository / 'vg_rules'
        assert Path(module.__file__).resolve().parent == installed
        with ZipFile(archive_path) as archive:
            for filename in archive.namelist():
                assert (installed / filename).read_bytes() == archive.read(filename)
        state["namespace"] = namespace
        session["installed"] = installed
        session["package_before"] = {p.relative_to(installed): p.read_bytes()
                                     for p in installed.rglob("*") if p.is_file()}
        module.initialize_pending_scenes()
        bpy.context.scene.name = state["scene"]
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        bpy.ops.mesh.primitive_cube_add(size=2)
        obj = bpy.context.object
        obj.name = "Demo Shell"
        obj.data.name = "Synthetic Eight-Vertex Mesh"
        for vertex in obj.data.vertices:
            vertex.co = (vertex.co.x * 0.7 + 1.0, vertex.co.y * 0.45,
                         vertex.co.z * 1.2)
        obj.modifiers.new("Demo X Mirror", 'MIRROR')
        bevel = obj.modifiers.new("Demo Bevel", 'BEVEL')
        bevel.width = 0.12
        bevel.segments = 3
        for name in ("DEF-Demo.L", "DEF-Demo.R", "cloth_pin", "MCH-temp", "weights_backup"):
            obj.vertex_groups.new(name=name).add(list(range(8)), 0.25, 'REPLACE')
        obj.vertex_groups.active_index = obj.vertex_groups["DEF-Demo.L"].index
        session["object"] = obj
        module.load_rules(bpy.context.scene, values)
        state["before"] = snapshot()
        assert bpy.ops.vgr.preview(scope='ACTIVE') == {'FINISHED'}
        assert snapshot() == state["before"], "Preview mutated the synthetic scene"
        state["preview"] = bpy.context.scene.vgr_settings.status
        assert state["preview"] == "Previewed 1 rule(s): 2 deletion(s), 1 assignment(s), 0 warning(s)."
        state["preview_results"] = [[line.kind, line.message] for line in bpy.context.scene.vgr_settings.log]
        viewport = area()
        with context():
            bpy.ops.screen.screen_full_area(use_hide_panels=False)
        viewport = area()
        space = viewport.spaces.active
        space.show_region_ui = True
        space.show_region_toolbar = False
        space.overlay.show_floor = False
        space.overlay.show_axis_x = False
        space.overlay.show_axis_y = False
        space.region_3d.view_rotation = Quaternion((0.882, 0.414, -0.094, -0.208)).normalized()
        space.region_3d.view_perspective = 'ORTHO'
        space.region_3d.view_location = Vector((0, 0, 0))
        space.region_3d.view_distance = 7
        with context():
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        bpy.context.preferences.view.show_splash = False
        bpy.context.preferences.view.ui_scale = 0.9
        bpy.context.preferences.system.use_region_overlap = False
        viewport.tag_redraw()
        later(resize_sidebar)

    def resize_sidebar():
        viewport = area()
        ui = next(r for r in viewport.regions if r.type == 'UI')
        ui.active_panel_category = 'VG Rules'
        session["drag_y"] = ui.y + ui.height // 2
        session["drag_x"] = ui.x
        window = bpy.context.window
        window.event_simulate(type='MOUSEMOVE', value='NOTHING', x=session["drag_x"], y=session["drag_y"])
        later(press_sidebar, 0.5)

    def press_sidebar():
        bpy.context.window.event_simulate(type='LEFTMOUSE', value='PRESS',
                                         x=session["drag_x"], y=session["drag_y"])
        later(start_sidebar_drag, 0.5)

    def start_sidebar_drag():
        # The first move activates the action-zone resize operator. A second
        # move then changes its width rather than merely starting the modal.
        bpy.context.window.event_simulate(type='MOUSEMOVE', value='NOTHING',
                                         x=session["drag_x"] - 25, y=session["drag_y"])
        later(drag_sidebar, 0.5)

    def drag_sidebar():
        viewport = area()
        destination = viewport.x + viewport.width - 640
        session["drag_x"] = destination
        bpy.context.window.event_simulate(type='MOUSEMOVE', value='NOTHING', x=destination, y=session["drag_y"])
        later(release_sidebar, 0.5)

    def release_sidebar():
        bpy.context.window.event_simulate(type='LEFTMOUSE', value='RELEASE',
                                         x=session["drag_x"], y=session["drag_y"])
        # Move away from controls so no hover tooltip obscures the screenshot.
        move_off_mesh()
        area().tag_redraw()
        later(capture_preview, 3)

    def image(label):
        destination = profile / f"{label}.png"
        # Native editor capture excludes the global top bar and its Blender logo.
        with context():
            assert bpy.ops.screen.screenshot_area(filepath=str(destination),
                                                   hide_props_region=False) == {'FINISHED'}
        assert destination.is_file() and destination.stat().st_size > 1000
        viewport = area()
        ui = next(r for r in viewport.regions if r.type == 'UI')
        assert ui.width >= 600 and ui.active_panel_category == 'VG Rules', "Sidebar must remain readable"
        assert not sys.modules[state["namespace"]].scene_needs_initialization(bpy.context.scene)
        state["images"][label] = {"path": f"submission/images/{label}.png", "sha256": sha256(destination),
                                  "editor_size": [viewport.width, viewport.height], "sidebar_width": ui.width,
                                  "panel": ui.active_panel_category}
        return destination

    def move_off_mesh():
        viewport = area()
        ui = next(r for r in viewport.regions if r.type == 'UI')
        bpy.context.window.event_simulate(type='MOUSEMOVE', value='NOTHING',
                                         x=viewport.x + viewport.width - 50, y=ui.y + 10)

    def capture_preview():
        assert snapshot() == state["before"]
        session["preview_image"] = image("preview")
        with context():
            bpy.ops.object.mode_set(mode='OBJECT')
            assert bpy.ops.vgr.apply(scope='ACTIVE') == {'FINISHED'}
        state["apply"] = bpy.context.scene.vgr_settings.status
        assert state["apply"] == "Applied 1 rule(s): 2 deletion(s), 1 assignment(s), 0 warning(s)."
        state["after"] = snapshot()
        assert set(state["after"]) == {"DEF-Demo.L", "DEF-Demo.R", "cloth_pin"}
        assert state["after"]["DEF-Demo.L"] == [[i, 1.0] for i in range(8)]
        assert not state["after"]["DEF-Demo.R"]
        assert state["after"]["cloth_pin"] == state["before"]["cloth_pin"]
        state["apply_results"] = [[line.kind, line.message] for line in bpy.context.scene.vgr_settings.log]
        state["mirror_vertex_groups"] = session["object"].modifiers["Demo X Mirror"].use_mirror_vertex_groups
        assert state["mirror_vertex_groups"]
        session["object"].vertex_groups.active_index = session["object"].vertex_groups["DEF-Demo.L"].index
        with context():
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        move_off_mesh()
        area().tag_redraw()
        later(capture_apply, 3)

    def capture_apply():
        session["apply_image"] = image("apply")
        installed = session["installed"]
        assert {p.relative_to(installed): p.read_bytes() for p in installed.rglob("*") if p.is_file()} == session["package_before"]
        state["checks"] = ["offline fresh profile", "installed ZIP byte parity", "Preview leaves weights unchanged",
                           "Apply removes two groups", "eight source vertices at full weight",
                           "opposite group emptied", "Keep group unchanged", "Mirror vertex groups enabled",
                           "installed files unchanged", "native editor screenshots; no global Blender-logo bar"]
        state["status"] = "PASS"
        state["images"]["thumbnail"] = {"path": "submission/images/thumbnail.png", "sha256": sha256(OUTPUT / "thumbnail.png"),
                                         "source": "existing VG Rules cube icon, reused unchanged"}
        report = json.dumps(state, indent=2) + "\n"
        (profile / "complete.json").write_text(report, encoding="utf-8")
        bpy.ops.wm.quit_blender()

    later(prepare, 3)


if __name__ == "__main__":
    if "--inside-blender" in sys.argv:
        capture_in_blender()
    else:
        launch()
