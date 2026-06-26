from ml.walkforward import walk_forward_splits


def test_splits_are_time_ordered_disjoint_and_expanding():
    folds = list(walk_forward_splits(list(range(100)), min_train=36, test_size=12))
    assert folds
    for train, test in folds:
        assert max(train) < min(test)          # train strictly precedes test
        assert set(train).isdisjoint(test)      # never train on a test period
    assert len(folds[1][0]) > len(folds[0][0])  # expanding window grows


def test_rolling_window_is_fixed_size():
    folds = list(walk_forward_splits(range(100), min_train=24, test_size=12, expanding=False))
    assert all(len(train) == 24 for train, _ in folds)
