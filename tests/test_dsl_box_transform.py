"""Abbreviated DSL: build a translated box to validate transforms via JSON export."""

from pathlib import Path
from .conftest import run_build_part_callable


def build_part(ctx):
    # base box 2×3×4, then translate by (1,2,3)
    box((2, 3, 4)).at((1, 2, 3)).add()


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    # BBox should be [1,2,3, 3,5,7]
    assert data["bbox"] == [1.0, 2.0, 3.0, 3.0, 5.0, 7.0]
    # Volume remains the same
    assert abs(data["volume"] - 24.0) < 1e-6


def test_box_transform():
    main()


if __name__ == "__main__":
    main()



