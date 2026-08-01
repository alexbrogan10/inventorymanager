"""Feature engineering for the demand-forecasting model.

Turns the sparse `(product_id, date, quantity)` rows
`ForecastRepository.get_daily_sales` returns - one row per day a product
actually sold something - into a dense daily time series per product
(zero-filled on days with no sales) with the lag/rolling/calendar features
the model trains on. All the pandas resampling and rolling-window math
lives here; nothing in this module talks to the database.
"""

from datetime import date

import pandas as pd

# product_id is included as a feature (not just a grouping key) so one
# global model can learn per-product demand levels instead of training a
# separate model per product - reasonable at this catalog's size, and it
# means every product benefits from patterns (day-of-week seasonality, for
# instance) learned across the whole sales history, not just its own.
FEATURE_COLUMNS = ["product_id", "day_of_week", "day_of_month", "month", "lag_1", "rolling_mean_7"]
TARGET_COLUMN = "quantity"

# A lag-1 + 7-day-rolling-mean feature pair needs at least 7 prior days of
# history to mean anything - shorter than that and the rolling mean would
# be an average of fewer, unrepresentative days.
_MIN_HISTORY_DAYS = 7


def _daily_series_for_product(product_id: int, rows: pd.DataFrame) -> pd.DataFrame:
    """Reindexes one product's sparse sale-day rows onto every calendar day
    between its first and last sale, filling gaps with 0 - a model trained
    only on days that had sales would never learn what "no demand" looks
    like, and gaps would otherwise silently corrupt the rolling/lag window
    below (pandas would compute it over non-adjacent calendar days).
    """
    rows = rows.set_index("sale_date").sort_index()
    full_index = pd.date_range(rows.index.min(), rows.index.max(), freq="D")
    daily = rows.reindex(full_index, fill_value=0)
    daily.index.name = "sale_date"
    daily["product_id"] = product_id
    daily["day_of_week"] = daily.index.dayofweek
    daily["day_of_month"] = daily.index.day
    daily["month"] = daily.index.month
    # Shifted by 1 so a day's features only ever describe days strictly
    # before it - using same-day figures would leak the answer into the
    # inputs.
    shifted = daily["quantity"].shift(1)
    daily["lag_1"] = shifted
    daily["rolling_mean_7"] = shifted.rolling(window=7, min_periods=7).mean()
    return daily.reset_index()


def build_training_frame(daily_sales: list[tuple[int, date, int]]) -> pd.DataFrame:
    """Returns a DataFrame with FEATURE_COLUMNS + TARGET_COLUMN, one row per
    (product, day) - excluding each product's first 7 days, since those
    can't have a complete lag/rolling window yet."""
    if not daily_sales:
        return pd.DataFrame(columns=[*FEATURE_COLUMNS, TARGET_COLUMN])

    raw = pd.DataFrame(daily_sales, columns=["product_id", "sale_date", "quantity"])
    raw["sale_date"] = pd.to_datetime(raw["sale_date"])

    per_product = [
        _daily_series_for_product(product_id, group[["sale_date", "quantity"]])
        for product_id, group in raw.groupby("product_id")
    ]
    daily = pd.concat(per_product, ignore_index=True)
    training = daily.dropna(subset=["lag_1", "rolling_mean_7"])
    return training[[*FEATURE_COLUMNS, TARGET_COLUMN]].reset_index(drop=True)


def build_next_day_feature_row(
    product_id: int, sales_history: list[tuple[date, int]]
) -> pd.DataFrame | None:
    """Builds the single feature row describing the day after this
    product's most recent known day, for a one-step-ahead "predict
    tomorrow's demand" query. Returns None when there's under a week of
    continuous history to compute lag_1/rolling_mean_7 from - the caller
    is expected to fall back to a simpler, model-free estimate in that case.
    """
    if not sales_history:
        return None

    rows = pd.DataFrame(sales_history, columns=["sale_date", "quantity"])
    rows["sale_date"] = pd.to_datetime(rows["sale_date"])
    daily = _daily_series_for_product(product_id, rows)
    if len(daily) < _MIN_HISTORY_DAYS:
        return None

    last_row = daily.iloc[-1]
    next_date = last_row["sale_date"] + pd.Timedelta(days=1)
    last_7_days = daily["quantity"].tail(_MIN_HISTORY_DAYS)

    feature_row = pd.DataFrame(
        [
            {
                "product_id": product_id,
                "day_of_week": next_date.dayofweek,
                "day_of_month": next_date.day,
                "month": next_date.month,
                "lag_1": float(last_row["quantity"]),
                "rolling_mean_7": float(last_7_days.mean()),
            }
        ]
    )
    return feature_row[FEATURE_COLUMNS]
