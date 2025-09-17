"""Abbreviated DSL module: defines build_part(ctx) and an optional main().

Used by pytest wrappers to run headless and assert on JSON export.
"""

from pathlib import Path
import math
from .conftest import run_build_part_callable


def build_part(ctx):
    cylinder(d=10, h=20).add()  # DSL symbols are injected by bbcadam-build


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    assert data["counts"]["faces"] == 3
    assert abs(data["volume"] - (math.pi * 25.0 * 20.0)) < 1e-3
    bb = data["bbox"]
    assert bb[2] == 0.0 and bb[5] == 20.0


def test_cylinder():
    main()


if __name__ == "__main__":
    main()



