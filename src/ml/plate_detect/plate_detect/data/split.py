"""Stratified deterministic splitting of items into named buckets."""

from __future__ import annotations

import random
from collections import defaultdict


def stratified_split(
    items: list[str], labels: list[int], ratios: dict[str, float], seed: int = 42
) -> dict[str, list[str]]:
    """Split items into named buckets with per-label stratification.

    Args:
        items: List of item identifiers to split.
        labels: List of integer labels corresponding to each item (for stratification).
        ratios: Dict mapping bucket names to their desired ratio. Keys become the
                output bucket names. Must sum to 1.0 (within 1e-6 tolerance).
        seed: Random seed for deterministic shuffling (default 42).

    Returns:
        Dict mapping bucket names (from ratios keys) to lists of items in that bucket.
        All items are disjoint across buckets and cover the entire input.

    Raises:
        ValueError: If ratios do not sum to 1.0.

    Example:
        >>> items = ["img_0", "img_1", "img_2", "img_3"]
        >>> labels = [0, 1, 0, 1]
        >>> out = stratified_split(items, labels, {"val": 0.5, "test": 0.5}, seed=42)
        >>> # Each label has ~50% in val and ~50% in test
    """
    if abs(sum(ratios.values()) - 1.0) > 1e-6:
        raise ValueError(f"ratios must sum to 1.0, got {sum(ratios.values())}")

    rng = random.Random(seed)

    # Group items by label
    by_label: dict[int, list[str]] = defaultdict(list)
    for it, lb in zip(items, labels):
        by_label[lb].append(it)

    # Prepare output buckets
    names = list(ratios.keys())
    out: dict[str, list[str]] = {n: [] for n in names}

    # Stratified split: for each label, distribute its items across buckets
    for lb in sorted(by_label):
        group = sorted(by_label[lb])  # sort first → stable pre-shuffle
        rng.shuffle(group)
        n = len(group)
        cuts, acc = [], 0.0
        for name in names[:-1]:
            acc += ratios[name]
            cuts.append(round(acc * n))
        start = 0
        for name, end in zip(names, cuts + [n]):
            out[name].extend(group[start:end])
            start = end

    return out
