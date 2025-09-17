"""Sketch arcs → pad integration test exercising multiple arc modes.

Builds a closed shape using lines and arcs with different specifications, then pads and
asserts on bbox/volume plausibility (exact area depends on chosen geometry).
"""

from pathlib import Path
import math
from .conftest import run_build_part_callable


def build_part(ctx):
    s = sketch(name='A', plane='XY', at=(0, 0, 0), visible=False)
    R = 5.0
    H = 10.0
    # Start at (R,0)
    s.from_(R, 0)
    # 1) Center+end (absolute): semicircle to (-R,0) ccw
    s.arc(radius=R, dir='ccw', centerAt=(0, 0), endAt=(-R, 0))
    # 2) Line down to (-R,-R), then line right to (R,-R)
    s.to(-R, -R)
    s.to(R, -R)
    # 3) R+E+dir: arc up to (R,0) with radius R, dir=ccw (center inferred)
    s.arc(radius=R, endAt=(R, 0), dir='ccw')
    s.close()
    # Pad and commit
    s.pad(H).add()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    bb = data["bbox"]
    assert bb[2] == 0.0 and bb[5] == 10.0
    # Expect roughly x in [-5, 5] based on chosen geometry
    assert bb[0] <= -5.0 + 1e-6 and bb[3] >= 5.0 - 1e-6
    assert data["volume"] > 0


def test_sketch_arcs_pad():
    main()


if __name__ == "__main__":
    main()



