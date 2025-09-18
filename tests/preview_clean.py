#!/usr/bin/env python3
"""
preview_clean: Remove preview artifacts under tests/build/.

Usage:
  python tests/preview_clean.py
"""

from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    target = (repo_root / "tests" / "build").resolve()
    if target.exists():
        print(f"Removing {target}")
        shutil.rmtree(target)
    else:
        print(f"Nothing to remove: {target}")


if __name__ == "__main__":
    main()


