"""Abbreviated DSL module: defines build_part(ctx) and an optional main().

Used by pytest wrappers to run headless and assert on JSON export.
"""

from pathlib import Path
import math
from .conftest import run_build_part_callable


def build_part(ctx):
    # box: width=10, depth=20, height=30
    box((10, 20, 30)).add()  # DSL symbols are injected by bbcadam-build


def main() -> None:
    data = run_build_part_callable(build_part, Path.cwd())
    assert data["counts"]["faces"] == 6
    assert data["counts"]["edges"] == 12
    assert data["counts"]["vertices"] == 8
    assert data["bbox"] == [0.0, 0.0, 0.0, 10.0, 20.0, 30.0]
    assert abs(data["volume"] - 6000.0) < 1e-6


if __name__ == "__main__":
    main()


