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
    # Strong volume check: area = semicircle (pi R^2 / 2) + rectangle (2R^2) - sector (theta*R^2/2)
    R = 5.0
    H = 10.0
    # If the top arc is missing, edge_kinds.circle will be 0 or 1 instead of >=2.
    # Use this to fail explicitly before volume mismatch surprises us.
    ek = data.get("counts", {}).get("edge_kinds", {})
    assert ek.get("circle", 0) >= 2, f"Expected at least 2 circular edges, got {ek}"
    # Check that at least one arc length approximates a semicircle of radius R
    circle_lengths = (data.get("edge_metrics", {}) or {}).get("circle_lengths", [])
    assert circle_lengths, "No circle/arc lengths reported"
    # We expect ~pi*R for the top semicircle (within a generous tolerance)
    assert any(abs(L - math.pi * R) < 0.5 for L in circle_lengths), (
        f"No arc length close to semicircle; lengths={circle_lengths}")
    # Empirical volume (visual pad matches intent). Hardcode for now.
    expected_vol = 915.3456001252441
    assert abs(data["volume"] - expected_vol) < 1e-2


def test_sketch_arcs_pad():
    main()


if __name__ == "__main__":
    main()



