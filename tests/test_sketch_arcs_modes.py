"""Arc modes test: two modes in one sketch

Modes covered:
- center + sweep (end inferred)
- radius + end + sweep (explicit degrees)
"""

from pathlib import Path
import math
from .conftest import run_build_part_callable


def build_part(ctx):
    s = sketch(name='ArcModes', plane='XY', at=(0, 0, 0), visible=False)
    R = 5.0
    H = 10.0
    # Start at (R,0)
    s.from_(R, 0)
    # 1) center + sweep=90° CCW: go to (0,R) along quarter-circle
    s.arc(centerAt=(0, 0), sweep=90)
    # Edge across top to (-R,R)
    s.to(-R, R)
    # 2) radius + end + sweep (CW quarter back to (-R,0))
    s.arc(radius=R, endAt=(-R, 0), dir='cw', sweep=-90)
    # Close bottom edge back to (R,0)
    s.to(R, 0)
    s.close()
    # Pad and commit
    s.pad(H).add()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    R = 5.0
    # Expect two quarter-circle arcs of length ≈ pi*R/2
    circle_lengths = (data.get("edge_metrics", {}) or {}).get("circle_lengths", [])
    assert circle_lengths, "No circular edges detected on padded solid"
    target = math.pi * R / 2.0
    near_quarters = [L for L in circle_lengths if abs(L - target) < 0.5]
    assert len(near_quarters) >= 2, f"Expected two quarter arcs; lengths={circle_lengths}"
    # Basic bbox sanity
    bb = data["bbox"]
    assert abs(bb[0] - (-R)) < 1e-6 and abs(bb[3] - R) < 1e-6
    assert abs(bb[2] - 0.0) < 1e-6


def test_arc_modes():
    main()


if __name__ == "__main__":
    main()


