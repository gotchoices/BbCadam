"""Sketch complex path features similar to worm.py path construction."""

import pytest
from pathlib import Path
from tests.conftest import run_build_part_callable


def build_part(ctx):
    """Test complex path with sketch; arcs and closure then pad."""
    radius1 = param('radius_1', 20)
    radius2 = param('radius_2', 15)
    seg1 = param('seg1', 30)
    seg2 = param('seg2', 25)
    seg3 = param('seg3', 20)
    thick = 5.0

    s = sketch(name='worm_path', plane='XY', at=(0, 0, 0), visible=True)
    s.from_(x=0, y=0)
    s.go(dx=seg1, dy=0)
    s.arc(radius=radius1, dir='ccw', end=(radius1, radius1))
    s.go(dx=0, dy=seg2)
    s.arc(radius=radius2, dir='cw', sweep=45)
    s.go(r=seg3, a_deg=45)
    s.to(x=0)
    s.to(y=0)
    s.pad(thick)


def test_sketch_complex_path_chain():
    work_dir = Path(__file__).parent / "build" / "tmp"
    result = run_build_part_callable(build_part, work_dir)
    vol = result['volume']
    print(f"[sketch_complex] volume={vol}")
    expected_vol = 17891.10
    assert abs(vol - expected_vol) < 0.1
    bb = result['bbox']
    assert bb[3] >= 50.0 - 1e-6
    assert bb[4] >= 45.0 - 1e-6


