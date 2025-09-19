"""Arc plane variant: XZ plane with center+sweep arcs (two quarters)."""

from pathlib import Path
import math
from .conftest import run_build_part_callable


def build_part(ctx):
    s = sketch(name='ArcXZ', plane='XZ', at=(0, 0, 0), visible=False)
    R = 3.0
    H = 6.0
    # Start at (R,0) in local XZ; build two quarter arcs around center
    s.from_(R, 0)
    s.arc(centerAt=(0, 0), sweep=90)
    s.arc(centerAt=(0, 0), sweep=90)
    # Close base back to (R,0)
    s.to(R, 0)
    s.close()
    s.pad(H).add()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    R = 3.0
    H = 6.0
    circle_lengths = (data.get("edge_metrics", {}) or {}).get("circle_lengths", [])
    assert circle_lengths, "No circular edges detected"
    target = math.pi * R / 2.0
    quarters = sum(1 for L in circle_lengths if abs(L - target) < 0.5)
    assert quarters >= 2, f"Expected two quarter arcs; lengths={circle_lengths}"
    # In XZ plane, pad is along +Y; expect Y bbox span == H
    bb = data["bbox"]
    assert abs(bb[1] - 0.0) < 1e-6 and abs(bb[4] - H) < 1e-6


def test_arc_plane_xz():
    main()


if __name__ == "__main__":
    main()


