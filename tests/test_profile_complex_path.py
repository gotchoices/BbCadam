"""Test complex path features similar to worm.py path construction."""

import pytest
from pathlib import Path
from tests.conftest import run_build_part_callable


def build_part(ctx):
    """Test complex path with problematic arcs from worm.py - PATH ONLY."""
    
    # Parameters from worm.py
    radius1 = param('radius_1', 20)
    radius2 = param('radius_2', 15)
    seg1 = param('seg1', 30)
    seg2 = param('seg2', 25)
    seg3 = param('seg3', 20)
    thick = 5.0

    # Exact path from worm.py lines 21-35 - using profile (part-based)
    p = profile(name='worm_path', plane='XY', at=(0, 0, 0))
    p.from_(x=0, y=0)
    p.go(dx=seg1, dy=0)
    # 90° CCW arc with given radius; let center be inferred
    p.arc(radius=radius1, dir='ccw', end=(radius1, radius1))
    p.go(dx=0, dy=seg2)
    # 45° CW arc: specify sweep and a plausible center to infer end consistently
    start_x, start_y = 20.0, float(radius1 + seg2)
    center_at = (start_x + float(radius2), start_y)
    p.arc(
        radius=radius2,
        dir='cw',
        sweep=45,
    )
    # Continue along 45° tangent using radial go
    p.go(r=seg3, a_deg=45)

    # Add segment back to Y axis, then finalize closure and pad
    p.to(x=0)
    p.to(y=0)

    # Pad the closed sketch to produce a solid for measurable assertions
    p.pad(thick)


def test_profile_complex_path_chain():
    """Test the complex path construction."""
    
    # Run the test and get geometry data
    work_dir = Path(__file__).parent / "build" / "tmp"
    result = run_build_part_callable(build_part, work_dir)
    
    # Basic validation - now we have a solid and sane extents
    vol = result['volume']
    print(f"[complex_path] volume={vol}")
    # Lock in volume to catch arc-direction regressions (rounded empirical)
    expected_vol = 17891.10
    assert abs(vol - expected_vol) < 0.1
    bbox = result['bbox']
    assert bbox[3] >= 50.0 - 1e-6  # xMax
    assert bbox[4] >= 45.0 - 1e-6  # yMax (20 + 25)
