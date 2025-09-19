"""Arc modes test 2: center+sweep and center+radius+sweep (single loop, XY)"""

from pathlib import Path
import math
from .conftest import run_build_part_callable


def build_part(ctx):
    # Single loop in XY: first arc uses center+sweep, second uses center+radius+sweep
    s = sketch(name='A1', plane='XY', at=(0, 0, 0), visible=False)
    R = 4.0
    H = 8.0
    s.from_(R, 0)
    # center + sweep (end inferred): quarter to (0,R)
    s.arc(centerAt=(0, 0), sweep=90)
    # center + radius + sweep: next quarter to (-R,0)
    s.arc(centerAt=(0, 0), radius=R, sweep=90)
    # bottom edge back to (R,0)
    s.to(R, 0)
    s.close()
    s.pad(H).add()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    R = 4.0
    circle_lengths = (data.get("edge_metrics", {}) or {}).get("circle_lengths", [])
    assert circle_lengths, "No circular edges detected"
    target = math.pi * R / 2.0
    quarters = sum(1 for L in circle_lengths if abs(L - target) < 0.5)
    assert quarters >= 2, f"Quarter arcs missing; lengths={circle_lengths}"
    bb = data["bbox"]
    assert abs(bb[0] - (-R)) < 1e-6 and abs(bb[3] - R) < 1e-6
    assert abs(bb[2] - 0.0) < 1e-6


def test_arc_modes_plane_and_radius():
    main()


if __name__ == "__main__":
    main()


