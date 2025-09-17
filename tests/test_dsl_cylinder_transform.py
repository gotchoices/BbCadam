"""Abbreviated DSL: cylinder transform tests (.at())."""

from pathlib import Path
from .conftest import run_build_part_callable


def build_part(ctx):
    # Cylinder d=10,h=20 translated by (3,4,5)
    cylinder(d=10, h=20).at((3, 4, 5)).add()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    bb = data["bbox"]
    assert bb[0] >= 3.0 - 5.1 and bb[3] <= 3.0 + 5.1  # allow small tolerance
    assert bb[2] == 5.0 and bb[5] == 25.0


def test_cylinder_at():
    main()


if __name__ == "__main__":
    main()



