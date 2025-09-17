"""Headless DSL test using bbcadam-py. Lets the CLI locate FreeCAD.

Requires FreeCAD to be installed and discoverable. The test will fail if not.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest


def test_box_export_json_headless(tmp_path: Path):
    # Create a temporary full-python script that prints exported JSON
    script = tmp_path / "make_box.py"
    script.write_text("\n".join([
        "# Abbreviated format: builder provides ctx",
        "from pathlib import Path",
        "def build_part(ctx):",
        "    import bbcadam",
        "    _ = bbcadam.box((10, 20, 30)).add()",
        "    out = Path(__file__).with_suffix('.json')",
        "    bbcadam.export('json', to=str(out))",
    ]))

    # Run bbcadam-py headless; rely on its FreeCAD detection
    result = subprocess.run(["bbcadam-build", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, f"bbcadam-py failed: {result.stderr}"

    # Read JSON written next to the script
    out_path = script.with_suffix('.json')
    assert out_path.exists(), f"Expected JSON file not found: {out_path}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    payload = out_path.read_text()
    print("=== export json ===\n" + payload)
    data = json.loads(payload)

    # Basic sanity checks
    assert abs(data.get("volume", 0) - 6000) < 1e-6  # 10*20*30
    assert data.get("counts", {}).get("faces") == 6
    assert data.get("counts", {}).get("edges") == 12
    assert data.get("counts", {}).get("vertices") == 8
    assert data.get("bbox") == [0.0, 0.0, 0.0, 10.0, 20.0, 30.0]
    com = data.get("center_of_mass", [])
    assert len(com) == 3 and all(abs(a - b) < 1e-6 for a, b in zip(com, [5.0, 10.0, 15.0]))
    assert abs(data.get("area", 0) - 2200.0) < 1e-6


