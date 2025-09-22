"""Profile arc plane variant: XZ plane with center+sweep arcs (two quarters)."""

from pathlib import Path
import math
from .conftest import run_build_part_callable


def build_part(ctx):
    p = profile(name='ArcXZP', plane='XZ', at=(0, 0, 0))
    R = 3.0
    H = 6.0
    p.from_(R, 0)
    p.arc(centerAt=(0, 0), sweep=90)
    p.arc(centerAt=(0, 0), sweep=90)
    p.to(R, 0)
    p.close()
    p.pad(H).add()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    R = 3.0
    H = 6.0
    circle_lengths = (data.get("edge_metrics", {}) or {}).get("circle_lengths", [])
    assert circle_lengths, "No circular edges detected"
    target = math.pi * R / 2.0
    quarters = sum(1 for L in circle_lengths if abs(L - target) < 0.5)
    assert quarters >= 2, f"Expected two quarter arcs; lengths={circle_lengths}"
    bb = data["bbox"]
    assert abs(bb[1] - 0.0) < 1e-6 and abs(bb[4] - H) < 1e-6


def test_profile_arc_plane_xz():
    main()


if __name__ == "__main__":
    main()


