#!/usr/bin/env python3
"""Rebuild every generated asset in the right order.

Usage:
    python3 tools/asset_pipeline/build_all.py            # assets + data bundle
    python3 tools/asset_pipeline/build_all.py --docs     # ... plus the design sheet
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

STEPS = [
    ("font", [sys.executable, str(HERE / "font5x7.py")]),
    ("characters", [sys.executable, str(HERE / "build_characters.py")]),
    ("stage", [sys.executable, str(HERE / "build_stage.py")]),
    ("bundle", [sys.executable, str(HERE / "bundle_data.py")]),
]
DOC_STEPS = [
    ("design sheet", [sys.executable, str(HERE / "design_sheet.py")]),
    ("asset validation", [sys.executable, str(ROOT / "tools/validation/validate_assets.py")]),
]


def run(label, cmd):
    print(f"== {label}")
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        print(f"!! {label} failed with exit code {proc.returncode}")
        raise SystemExit(proc.returncode)


if __name__ == "__main__":
    for label, cmd in STEPS:
        run(label, cmd)
    if "--docs" in sys.argv:
        for label, cmd in DOC_STEPS:
            run(label, cmd)
    print("asset pipeline complete")
