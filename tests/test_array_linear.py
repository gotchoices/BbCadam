"""Array tests: 1D linear array volume and bbox checks."""

from pathlib import Path
from .conftest import run_build_part_callable


def build_part(ctx):
    # Base cube 10×10×10 at origin
    f = box(size=(10, 10, 10))
    # 1D array: 3 copies along X with spacing 20 → x spans [0, 10 + 2*20] = [0, 50]
    arr = f.array(nx=3, sx=20)
    arr.add()


def test_array_linear_volume_bbox():
    data = run_build_part_callable(build_part, Path.cwd())
    # Volume = 3 cubes × 1000
    assert abs(data["volume"] - 3000.0) < 1e-6
    bb = data["bbox"]
    # X: 0..50, Y: 0..10, Z: 0..10
    assert abs(bb[0] - 0.0) < 1e-6 and abs(bb[3] - 50.0) < 1e-6
    assert abs(bb[1] - 0.0) < 1e-6 and abs(bb[4] - 10.0) < 1e-6
    assert abs(bb[2] - 0.0) < 1e-6 and abs(bb[5] - 10.0) < 1e-6


