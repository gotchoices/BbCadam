"""Abbreviated DSL: fuse two non-overlapping boxes and assert volume via harness."""

from pathlib import Path
from .conftest import run_build_part_callable


def build_part(ctx):
    # Box A: 2×3×4 at origin → volume 24
    box((2, 3, 4)).add()
    # Box B: 1×1×1 translated so it doesn't overlap (shift +5 in X) → volume 1
    box((1, 1, 1)).at((5, 0, 0)).add()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    assert abs(data["volume"] - 25.0) < 1e-6


def test_fuse():
    main()


if __name__ == "__main__":
    main()



