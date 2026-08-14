"""CLI entry point for batch color-distribution analysis of plate crops.

Usage:
    plate_color <glob-pattern> [<glob-pattern> ...]

Expands each argument as a recursive glob, classifies the color of every
readable image, and prints a summary table to stdout.
"""
from __future__ import annotations

import sys
import glob
import collections

import cv2

from .pipeline import process_plate

_EXT = (".jpg", ".jpeg", ".png")


def color_distribution(paths: list[str]) -> dict:
    """Count color labels across a list of image paths.

    Non-image paths (extensions other than .jpg/.jpeg/.png) are skipped so
    that glob patterns matching mixed directories don't crash the classifier.
    Unreadable files (corrupted, missing after glob expansion) are also skipped
    silently — they would otherwise produce None from cv2.imread and crash
    process_plate.

    Args:
        paths: Absolute or relative file paths to candidate plate crop images.

    Returns:
        Plain dict mapping color label strings to occurrence counts.
    """
    cnt: collections.Counter = collections.Counter()
    for p in paths:
        # Skip non-image files matched by a broad glob pattern
        if not p.lower().endswith(_EXT):
            continue
        im = cv2.imread(p)
        # Skip files that cv2 cannot decode (missing, truncated, permission error)
        if im is None:
            continue
        cnt[process_plate(im).color] += 1
    return dict(cnt)


def main(argv: list[str] | None = None) -> int:
    """Batch-classify plate crops matched by glob patterns and print the distribution.

    Args:
        argv: List of glob patterns.  Defaults to ``sys.argv[1:]`` when None.

    Returns:
        Exit code 0 on success.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    files: list[str] = []
    for pat in argv:
        files += glob.glob(pat, recursive=True)
    dist = color_distribution(files)
    total = sum(dist.values()) or 1  # guard against division-by-zero on empty input
    print(f"analyzed {sum(dist.values())} crops")
    for k, v in sorted(dist.items(), key=lambda kv: -kv[1]):
        print(f"  {k:10s} {v:5d}  {100 * v / total:5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
