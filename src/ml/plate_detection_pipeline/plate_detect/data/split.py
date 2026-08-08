"""Stratified deterministic splitting of items into named buckets."""
from __future__ import annotations
import random
from collections import defaultdict


def stratified_split(
    items: list[str], labels: list[int], ratios: dict[str, float], seed: int = 42
) -> dict[str, list[str]]:
    if abs(sum(ratios.values()) - 1.0) > 1e-6:
        raise ValueError(f"ratios must sum to 1.0, got {sum(ratios.values())}")
    rng = random.Random(seed)
    by_label: dict[int, list[str]] = defaultdict(list)
    for it, lb in zip(items, labels):
        by_label[lb].append(it)
    names = list(ratios.keys())
    out: dict[str, list[str]] = {n: [] for n in names}
    for lb in sorted(by_label):
        group = sorted(by_label[lb])   # stable pre-shuffle
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
