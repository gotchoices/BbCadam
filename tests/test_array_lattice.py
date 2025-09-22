"""Array tests: 3D lattice array volume and bbox checks."""

from pathlib import Path
from .conftest import run_build_part_callable


def build_part(ctx):
    # Base cuboid 2×3×4 at origin
    f = box(size=(2, 3, 4))
    # 3D lattice: 2×3×2 with spacings 5,6,7
    arr = f.array(nx=2, sx=5, ny=3, sy=6, nz=2, sz=7)
    arr.add()


def test_array_lattice_volume_bbox():
    data = run_build_part_callable(build_part, Path.cwd())
    # Volume = 2*3*2 copies × (2*3*4) = 12 × 24 = 288
    assert abs(data["volume"] - 288.0) < 1e-6
    bb = data["bbox"]
    # X: 0..(2 + 1*5)=7, Y: 0..(3 + 2*6)=15, Z: 0..(4 + 1*7)=11
    assert abs(bb[0] - 0.0) < 1e-6 and abs(bb[3] - 7.0) < 1e-6
    assert abs(bb[1] - 0.0) < 1e-6 and abs(bb[4] - 15.0) < 1e-6
    assert abs(bb[2] - 0.0) < 1e-6 and abs(bb[5] - 11.0) < 1e-6


