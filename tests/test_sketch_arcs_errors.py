"""Arc error cases: invalid inputs should raise and fail headless build."""

from pathlib import Path
from .conftest import run_abbrev_script_expect_failure


def test_arc_invalid_start_not_on_circle(tmp_path: Path):
    # With centerAt fixed, start must lie on the circle; here it doesn't
    src = """
def build_part(ctx):
    from bbcadam import sketch
    s = sketch('E', plane='XY')
    s.from_(1, 0)
    s.arc(centerAt=(0,0), radius=0.4, endAt=(-1, 0))
    s.close()
    s.pad(1).add()
"""
    run_abbrev_script_expect_failure(src, tmp_path, "end not on circle")


def test_arc_start_equals_end(tmp_path: Path):
    src = """
def build_part(ctx):
    from bbcadam import sketch
    s = sketch('E2', plane='XY')
    s.from_(1, 0)
    s.arc(centerAt=(0,0), radius=1.0, endAt=(1, 0))
    s.close()
    s.pad(1).add()
"""
    run_abbrev_script_expect_failure(src, tmp_path, "start and end coincide")


def test_arc_full_circle_rejected(tmp_path: Path):
    src = """
def build_part(ctx):
    from bbcadam import sketch
    s = sketch('E3', plane='XY')
    s.from_(1, 0)
    # Attempt a full circle via sweep=360
    s.arc(centerAt=(0,0), radius=1.0, sweep=360)
    s.close()
    s.pad(1).add()
"""
    run_abbrev_script_expect_failure(src, tmp_path, "start and end coincide")


