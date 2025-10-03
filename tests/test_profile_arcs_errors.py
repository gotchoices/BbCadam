"""Profile arc error cases: invalid inputs should raise and fail headless build."""

from pathlib import Path
from .conftest import run_abbrev_script_expect_failure


def test_profile_arc_invalid_start_not_on_circle(tmp_path: Path):
    src = """
def build_part(ctx):
    from bbcadam import profile
    p = profile('E', plane='XY')
    p.from_(1, 0)
    p.arc(centerAt=(0,0), radius=0.4, endAt=(-1, 0))
    p.close()
    p.pad(1).add()
"""
    run_abbrev_script_expect_failure(src, tmp_path, "start not on circle")


def test_profile_arc_start_equals_end(tmp_path: Path):
    src = """
def build_part(ctx):
    from bbcadam import profile
    p = profile('E2', plane='XY')
    p.from_(1, 0)
    p.arc(centerAt=(0,0), radius=1.0, endAt=(1, 0))
    p.close()
    p.pad(1).add()
"""
    run_abbrev_script_expect_failure(src, tmp_path, "start and end coincide")


def test_profile_arc_full_circle_rejected(tmp_path: Path):
    src = """
def build_part(ctx):
    from bbcadam import profile
    p = profile('E3', plane='XY')
    p.from_(1, 0)
    p.arc(centerAt=(0,0), radius=1.0, sweep=360)
    p.close()
    p.pad(1).add()
"""
    run_abbrev_script_expect_failure(src, tmp_path, "start and end coincide")


