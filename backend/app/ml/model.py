"""Random Forest demand-forecasting model: trains on the feature table from
app/ml/features.py, persists to disk via joblib, and exposes predictions
with a per-prediction confidence score derived from the forest's own
tree-to-tree disagreement - a Random Forest already IS an ensemble of
trees that can "vote", so no separate confidence model is needed.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

from app.ml.features import FEATURE_COLUMNS, TARGET_COLUMN

# Below this many rows, a train/test split would be too small to produce a
# meaningful accuracy figure - the deployed model still trains on
# everything available, but `accuracy` is reported as None rather than a
# number computed from a handful of held-out rows.
_MIN_ROWS_FOR_EVALUATION = 20
_TEST_SIZE = 0.2
_RANDOM_STATE = 42
_N_ESTIMATORS = 200


class InsufficientTrainingDataError(Exception):
    """Raised when there isn't enough sales history to train on at all."""


def _confidence_from_spread(mean: float, std: float) -> float:
    if mean <= 0:
        return 1.0 if std == 0 else 0.0
    return max(0.0, min(1.0, 1 - std / mean))


@dataclass
class TrainedModel:
    estimator: RandomForestRegressor
    feature_importances: dict[str, float]
    accuracy: float | None
    training_row_count: int
    trained_at: datetime

    def predict_with_confidence(self, feature_row: pd.DataFrame) -> tuple[float, float]:
        """Returns (prediction, confidence). Confidence comes from how much
        the forest's individual trees agree on this one row: a small
        relative spread across trees means high confidence, a wide spread
        means the forest itself is unsure. This is a property of
        ensembles - a single-estimator model like linear regression has no
        equivalent signal to offer.
        """
        # Individual trees (unlike the RandomForestRegressor itself) weren't
        # fit with column names attached, so predicting straight off the
        # DataFrame triggers a "fitted without feature names" warning even
        # though the columns are already in the right order - pass a plain
        # array instead.
        values = feature_row[FEATURE_COLUMNS].to_numpy()
        tree_predictions = np.array(
            [tree.predict(values)[0] for tree in self.estimator.estimators_]
        )
        mean = float(tree_predictions.mean())
        std = float(tree_predictions.std())
        return max(0.0, mean), _confidence_from_spread(mean, std)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @staticmethod
    def load(path: Path) -> "TrainedModel":
        model = joblib.load(path)
        if not isinstance(model, TrainedModel):
            raise TypeError("Persisted model file does not contain a TrainedModel.")
        return model


def train(training_frame: pd.DataFrame) -> TrainedModel:
    row_count = len(training_frame)
    if row_count == 0:
        raise InsufficientTrainingDataError(
            "No products have at least 7 days of continuous sales history to train on."
        )

    features = training_frame[FEATURE_COLUMNS]
    target = training_frame[TARGET_COLUMN]

    accuracy: float | None = None
    if row_count >= _MIN_ROWS_FOR_EVALUATION:
        x_train, x_test, y_train, y_test = train_test_split(
            features, target, test_size=_TEST_SIZE, random_state=_RANDOM_STATE
        )
        evaluation_model = RandomForestRegressor(
            n_estimators=_N_ESTIMATORS, random_state=_RANDOM_STATE
        )
        evaluation_model.fit(x_train, y_train)
        accuracy = float(r2_score(y_test, evaluation_model.predict(x_test)))

    # The deployed model is always refit on every available row - the
    # train/test split above exists purely to measure accuracy, not to
    # withhold data from the model that actually makes predictions.
    estimator = RandomForestRegressor(n_estimators=_N_ESTIMATORS, random_state=_RANDOM_STATE)
    estimator.fit(features, target)

    importances = {
        column: float(importance)
        for column, importance in zip(FEATURE_COLUMNS, estimator.feature_importances_, strict=True)
    }

    return TrainedModel(
        estimator=estimator,
        feature_importances=importances,
        accuracy=accuracy,
        training_row_count=row_count,
        trained_at=datetime.now(UTC),
    )
