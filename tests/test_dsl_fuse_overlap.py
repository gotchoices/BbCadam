"""Abbreviated DSL: overlapping fuse of two boxes, assert reduced volume."""

from pathlib import Path
from .conftest import run_build_part_callable


def build_part(ctx):
    # Two 2×2×2 boxes overlapping by a 1×2×2 slab (overlap volume 4)
    # Total = 8 + 8 - 4 = 12
    box((2, 2, 2)).add()
    box((2, 2, 2)).at((1, 0, 0)).add()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    assert abs(data["volume"] - 12.0) < 1e-6


def test_fuse_overlap():
    main()


if __name__ == "__main__":
    main()
