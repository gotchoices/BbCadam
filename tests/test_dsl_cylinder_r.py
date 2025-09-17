"""Abbreviated DSL: cylinder with radius argument, assert volume and bbox."""

from pathlib import Path
import math
from .conftest import run_build_part_callable


def build_part(ctx):
    # r=5, h=20 → same as d=10
    cylinder(r=5, h=20).add()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    assert data["counts"]["faces"] == 3
    assert abs(data["volume"] - (math.pi * 25.0 * 20.0)) < 1e-3
    bb = data["bbox"]
    assert bb[2] == 0.0 and bb[5] == 20.0


def test_cylinder_r():
    main()


if __name__ == "__main__":
    main()



