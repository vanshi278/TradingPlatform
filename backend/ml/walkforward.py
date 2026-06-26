"""Time-ordered walk-forward cross-validation.

Train on a window of past months, test on the next unseen block, then roll
forward. Time is never shuffled and a test month is never seen in training —
this is the single most important guard against an over-optimistic ML backtest.
"""
from __future__ import annotations

from typing import Iterator


def walk_forward_splits(
    dates,
    min_train: int = 36,
    test_size: int = 12,
    step: int | None = None,
    expanding: bool = True,
) -> Iterator[tuple[list, list]]:
    """Yield (train_dates, test_dates) over the sorted unique `dates`.

    min_train / test_size / step are counts of unique periods (months here).
    expanding=True grows the train window each fold; False keeps it rolling.
    """
    uniq = sorted(set(dates))
    step = step or test_size
    start = min_train
    while start < len(uniq):
        train = uniq[:start] if expanding else uniq[max(0, start - min_train):start]
        test = uniq[start:start + test_size]
        if not test:
            break
        yield train, test
        start += step
