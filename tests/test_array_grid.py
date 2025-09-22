"""Array tests: 2D grid array volume and bbox checks."""

from pathlib import Path
from .conftest import run_build_part_callable


def build_part(ctx):
    # Base cuboid 5×7×3 at origin
    f = box(size=(5, 7, 3))
    # 2D grid: nx=4, ny=2, spacings sx=10, sy=9
    arr = f.array(nx=4, sx=10, ny=2, sy=9)
    arr.add()


def test_array_grid_volume_bbox():
    data = run_build_part_callable(build_part, Path.cwd())
    # Volume = 8 copies × (5*7*3) = 8 × 105 = 840
    assert abs(data["volume"] - 840.0) < 1e-6
    bb = data["bbox"]
    # X: 0..(5 + 3*10)=35, Y: 0..(7 + 1*9)=16, Z: 0..3
    assert abs(bb[0] - 0.0) < 1e-6 and abs(bb[3] - 35.0) < 1e-6
    assert abs(bb[1] - 0.0) < 1e-6 and abs(bb[4] - 16.0) < 1e-6
    assert abs(bb[2] - 0.0) < 1e-6 and abs(bb[5] - 3.0) < 1e-6


