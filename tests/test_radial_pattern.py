"""Radial pattern tests: count, radius, bbox/volume sanity."""

from pathlib import Path
from .conftest import run_build_part_callable


def build_part(ctx):
    # Base cylinder: diameter 4, height 5 (volume ≈ π*2^2*5 = 20π)
    f = cylinder(d=4, h=5)
    # 6 posts on radius 20, around Z
    arr = f.radial(n=6, radius=20, axis='Z', start_deg=0, sweep_deg=360, orient='none')
    arr.add()


def test_radial_volume_bbox():
    import math
    data = run_build_part_callable(build_part, Path.cwd())
    # Volume ≈ 6 * 20π
    assert abs(data["volume"] - (6 * 20.0 * math.pi)) < 1.0
    bb = data["bbox"]
    # X extent hits ±(radius + r_cyl) = ±22
    assert bb[0] <= -22.0 and bb[3] >= 22.0
    # Y extent hits ±(radius*sin(60°) + r_cyl) ≈ ±19.32 (for 6 spokes)
    import math
    y_ext = 20.0 * math.sin(math.radians(60.0)) + 2.0
    assert bb[1] <= -y_ext and bb[4] >= y_ext
    # Height 5
    assert abs(bb[2] - 0.0) < 1e-6 and abs(bb[5] - 5.0) < 1e-6


