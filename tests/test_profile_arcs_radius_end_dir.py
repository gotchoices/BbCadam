"""Profile arc mode: radius + end + dir (minor arcs)."""

from pathlib import Path
import math
from .conftest import run_build_part_callable


def build_part(ctx):
    import math
    p = profile(name='ArcREDP', plane='XY', at=(0, 0, 0))
    R = 6.0
    H = 8.0
    p.from_(R, 0)
    p.arc(radius=R, endAt=(R*0.5, R*math.sqrt(3)/2.0), dir='ccw')
    p.arc(radius=R, endAt=(0.0, R*1.0), dir='ccw')
    p.to(0, 0)
    p.to(R, 0)
    p.close()
    p.pad(H).add()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    R = 6.0
    circle_lengths = (data.get("edge_metrics", {}) or {}).get("circle_lengths", [])
    assert circle_lengths, "No circular edges on padded solid"
    target = R * math.pi / 3.0
    near_minor = [L for L in circle_lengths if abs(L - target) < 0.6]
    assert len(near_minor) >= 2, f"Expected two minor arcs; lengths={circle_lengths}"


def test_profile_arc_radius_end_dir_minor():
    main()


if __name__ == "__main__":
    main()


