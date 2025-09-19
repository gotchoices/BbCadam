"""Arc mode: radius + end + dir (defaults to minor arc)

We create two chained arcs using radius+end+dir and assert that both are minor arcs
by checking their lengths against known targets.
"""

from pathlib import Path
import math
from .conftest import run_build_part_callable


def build_part(ctx):
    import math  # ensure available when preview extracts only function body
    s = sketch(name='ArcRED', plane='XY', at=(0, 0, 0), visible=False)
    R = 6.0
    H = 8.0
    # Start at (R,0), aim to (-R/2, sqrt(3)/2 R) with minor arc ccw (60°)
    s.from_(R, 0)
    s.arc(radius=R, endAt=(R*0.5, R*math.sqrt(3)/2.0), dir='ccw')
    # Continue to (-R,0) with another minor arc ccw (60°)
    # Move to an intermediate point on the same circle for a second minor arc
    s.arc(radius=R, endAt=(R*0.0, R*1.0), dir='ccw')
    # Close with lines to form a pad-able region
    s.to(0, 0)
    s.to(R, 0)
    s.close()
    s.pad(H).add()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    R = 6.0
    circle_lengths = (data.get("edge_metrics", {}) or {}).get("circle_lengths", [])
    assert circle_lengths, "No circular edges on padded solid"
    # Expect two ~60° arcs: length ≈ R * pi/3
    target = R * math.pi / 3.0
    near_minor = [L for L in circle_lengths if abs(L - target) < 0.6]
    assert len(near_minor) >= 2, f"Expected two minor arcs; lengths={circle_lengths}"


def test_arc_radius_end_dir_minor():
    main()


if __name__ == "__main__":
    main()


