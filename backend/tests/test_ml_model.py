from datetime import date, timedelta

from app.ml.features import build_next_day_feature_row, build_training_frame
from app.ml.model import InsufficientTrainingDataError, _confidence_from_spread, train


def test_train_raises_without_any_rows() -> None:
    empty_frame = build_training_frame([])

    try:
        train(empty_frame)
        raise AssertionError("expected InsufficientTrainingDataError")
    except InsufficientTrainingDataError:
        pass


def test_train_computes_accuracy_with_enough_rows() -> None:
    start = date(2026, 1, 1)
    # 34 days -> 34 - 7 warm-up days = 27 training rows, above the
    # evaluation threshold, so a real train/test split + accuracy figure
    # gets computed instead of reporting None.
    rows = [
        (1, start + timedelta(days=i), 5 + (3 if (start + timedelta(days=i)).weekday() >= 5 else 0))
        for i in range(34)
    ]

    frame = build_training_frame(rows)
    model = train(frame)

    assert model.training_row_count == 27
    assert model.accuracy is not None

    history = [(d, q) for _, d, q in rows]
    feature_row = build_next_day_feature_row(1, history)
    assert feature_row is not None
    prediction, confidence = model.predict_with_confidence(feature_row)
    assert prediction >= 0
    assert 0.0 <= confidence <= 1.0


def test_confidence_from_spread_handles_zero_and_negative_mean() -> None:
    assert _confidence_from_spread(mean=0.0, std=0.0) == 1.0
    assert _confidence_from_spread(mean=0.0, std=1.0) == 0.0
    assert _confidence_from_spread(mean=-2.0, std=0.5) == 0.0
