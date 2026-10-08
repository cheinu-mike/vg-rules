# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""Run source and installed-extension checks in fresh offline Blender profiles."""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", type=Path, required=True, help="Path to Blender 4.2 or newer")
    args = parser.parse_args()
    blender = args.blender.expanduser().resolve()
    if not blender.is_file():
        parser.error(f"Blender executable not found: {blender}")
    artifacts = ROOT / "tests/.artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="blender-", dir=artifacts)).resolve()
    if not run.is_relative_to(artifacts.resolve()):
        raise RuntimeError("Test output must stay inside the artifacts directory.")
    for check in ("verify_addon", "verify_runtime", "verify_extension"):
        profile = run / check
        profile.mkdir()
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["BLENDER_USER_RESOURCES"] = str(profile)
        environment["VGR_EXTENSION_TEST_DIR"] = str(profile)
        environment["VGR_TEST_ARTIFACT_DIR"] = str(profile / "fixtures")
        for key, name in (("BLENDER_USER_CONFIG", "config"),
                          ("BLENDER_USER_SCRIPTS", "scripts"),
                          ("BLENDER_USER_DATAFILES", "datafiles"),
                          ("BLENDER_USER_EXTENSIONS", "extensions")):
            environment[key] = str(profile / name)
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        try:
            result = subprocess.run(
                [str(blender), "--background", "--factory-startup", "--offline-mode",
                 "--python-exit-code", "1", "--python", str(ROOT / "tests" / f"{check}.py")],
                cwd=ROOT, env=environment, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=180, **options)
        except subprocess.TimeoutExpired:
            print(f"FAIL: {check} timed out. Artifacts: {run}")
            return 1
        (run / f"{check}.stdout.txt").write_text(result.stdout, encoding="utf-8")
        (run / f"{check}.stderr.txt").write_text(result.stderr, encoding="utf-8")
        marker = {"verify_addon": "ALL ADD-ON INTEGRATION CHECKS PASSED",
                  "verify_runtime": "ALL RUNTIME COMPLIANCE CHECKS PASSED",
                  "verify_extension": '"status": "PASS"'}[check]
        if result.returncode or marker not in result.stdout:
            print(result.stdout)
            print(result.stderr)
            print(f"FAIL: {check}. Artifacts: {run}")
            return 1
        print(f"PASS: {check}")
    print(f"All Blender checks passed. Artifacts: {run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
