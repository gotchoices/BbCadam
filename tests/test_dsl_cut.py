"""Abbreviated DSL: boolean cut (difference) on boxes, assert resulting volume."""

from pathlib import Path
from .conftest import run_build_part_callable


def build_part(ctx):
    # Base box: 4×4×4 → volume 64
    box((4, 4, 4)).add()
    # Inner box fully inside: 2×2×2 at (1,1,1) → volume 8; cut from base
    box((2, 2, 2)).at((1, 1, 1)).cut()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    # 64 - 8 = 56 expected after cut
    assert abs(data["volume"] - 56.0) < 1e-6


def test_box_cut():
    main()


if __name__ == "__main__":
    main()



