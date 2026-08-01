from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

import app.api.v1.endpoints.forecasting as forecasting_module
import app.api.v1.endpoints.recommendations as recommendations_module
from app.core.config import Settings
from app.models.user import UserRole

RECOMMENDATIONS_URL = "/api/v1/recommendations"
TRAIN_URL = "/api/v1/forecasting/train"
PRODUCTS_URL = "/api/v1/products"


@pytest.fixture(autouse=True)
def _isolate_ml_model_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both the forecasting and recommendations endpoints resolve the
    trained-model path from settings independently - both must be pointed
    at the same per-test temp directory so a model trained in a test is
    actually visible to that same test's recommendations request."""
    fake_settings = Settings(ml_model_dir=str(tmp_path))
    monkeypatch.setattr(forecasting_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(recommendations_module, "get_settings", lambda: fake_settings)


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_category(client: TestClient, token: str, name: str = "Electronics") -> int:
    response = client.post("/api/v1/categories", json={"name": name}, headers=_auth_header(token))
    return int(response.json()["id"])


def _create_supplier(
    client: TestClient, token: str, company_name: str = "Acme Supply Co.", lead_time_days: int = 7
) -> int:
    response = client.post(
        "/api/v1/suppliers",
        json={
            "company_name": company_name,
            "contact_person": "Jane Doe",
            "email": "jane@acme.example",
            "phone": "555-0100",
            "address": "123 Warehouse Rd",
            "lead_time_days": lead_time_days,
            "notes": None,
        },
        headers=_auth_header(token),
    )
    return int(response.json()["id"])


def _create_warehouse(client: TestClient, token: str, name: str = "Main Warehouse") -> int:
    response = client.post(
        "/api/v1/warehouses",
        json={"name": name, "address": "Somewhere", "notes": None},
        headers=_auth_header(token),
    )
    return int(response.json()["id"])


def _create_product(
    client: TestClient,
    token: str,
    category_id: int,
    supplier_id: int,
    sku: str,
    minimum_quantity: int = 5,
    maximum_quantity: int | None = None,
) -> int:
    response = client.post(
        PRODUCTS_URL,
        json={
            "sku": sku,
            "barcode": None,
            "name": f"Product {sku}",
            "description": None,
            "category_id": category_id,
            "supplier_id": supplier_id,
            "purchase_price": "5.00",
            "selling_price": "9.99",
            "minimum_quantity": minimum_quantity,
            "maximum_quantity": maximum_quantity,
            "unit_type": "each",
        },
        headers=_auth_header(token),
    )
    return int(response.json()["id"])


def _set_level(
    client: TestClient, token: str, product_id: int, warehouse_id: int, quantity: int
) -> None:
    client.put(
        f"{PRODUCTS_URL}/{product_id}/inventory/{warehouse_id}",
        json={"quantity": quantity},
        headers=_auth_header(token),
    )


def _create_sale(
    client: TestClient, token: str, warehouse_id: int, product_id: int, quantity: int
) -> int:
    response = client.post(
        "/api/v1/sales",
        json={
            "warehouse_id": warehouse_id,
            "customer_name": "Recommendation Test Customer",
            "items": [{"product_id": product_id, "quantity": quantity, "unit_price": "9.99"}],
        },
        headers=_auth_header(token),
    )
    return int(response.json()["id"])


def _backdate_sale(db_session: Session, sale_id: int, created_at: datetime) -> None:
    db_session.execute(
        text("UPDATE sales SET created_at = :created_at WHERE id = :id"),
        {"created_at": created_at, "id": sale_id},
    )
    db_session.commit()


def _backdate_sale_to_date(db_session: Session, sale_id: int, day: date) -> None:
    _backdate_sale(db_session, sale_id, datetime(day.year, day.month, day.day, 12, tzinfo=UTC))


def _seed_daily_sales(
    client: TestClient,
    db_session: Session,
    token: str,
    warehouse_id: int,
    product_id: int,
    *,
    days: int,
    quantity: int,
    ending: date,
) -> None:
    """Creates one sale per day for `days` consecutive days ending on
    `ending`, backdated so the product has continuous daily history."""
    _set_level(client, token, product_id, warehouse_id, days * quantity * 2)
    start = ending - timedelta(days=days - 1)
    for offset in range(days):
        day = start + timedelta(days=offset)
        sale_id = _create_sale(client, token, warehouse_id, product_id, quantity)
        _backdate_sale(db_session, sale_id, datetime(day.year, day.month, day.day, 12, tzinfo=UTC))


def _seed_weighted_daily_sales(
    client: TestClient,
    db_session: Session,
    token: str,
    warehouse_id: int,
    product_id: int,
    *,
    days: int,
    weekend_quantity: int,
    weekday_quantity: int,
    ending: date,
) -> None:
    """Like _seed_daily_sales, but with a different quantity on
    Sat/Sun vs Mon-Fri, for exercising seasonal-trend detection."""
    max_quantity = max(weekend_quantity, weekday_quantity)
    _set_level(client, token, product_id, warehouse_id, days * max_quantity * 2)
    start = ending - timedelta(days=days - 1)
    for offset in range(days):
        day = start + timedelta(days=offset)
        quantity = weekend_quantity if day.weekday() >= 5 else weekday_quantity
        sale_id = _create_sale(client, token, warehouse_id, product_id, quantity)
        _backdate_sale(db_session, sale_id, datetime(day.year, day.month, day.day, 12, tzinfo=UTC))


class Fixture:
    def __init__(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        self.token = auth_token_for(UserRole.MANAGER, email="recommend-manager@example.com")
        self.category_id = _create_category(client, self.token)
        self.supplier_id = _create_supplier(client, self.token, lead_time_days=7)
        self.warehouse_id = _create_warehouse(client, self.token)


def _make_fixture(client: TestClient, auth_token_for: Callable[..., str]) -> Fixture:
    return Fixture(client, auth_token_for)


class TestAccess:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get(RECOMMENDATIONS_URL).status_code == 401

    def test_any_authenticated_role_can_read(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(token))

        assert response.status_code == 200


class TestModelTrainedFlag:
    def test_reorder_suggestions_empty_and_flag_false_before_training(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        body = response.json()
        assert body["model_trained"] is False
        assert body["reorder_suggestions"] == []

    def test_other_categories_still_compute_before_training(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "RECOMMEND-1",
            maximum_quantity=50,
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 100)

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        body = response.json()
        assert body["model_trained"] is False
        skus = {w["sku"] for w in body["overstock_warnings"]}
        assert "RECOMMEND-1" in skus


class TestReorderSuggestions:
    def test_suggests_reorder_for_low_stock_high_demand_product(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-2"
        )
        _seed_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=14,
            quantity=10,
            ending=date.today() - timedelta(days=1),
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 5)
        client.post(TRAIN_URL, headers=_auth_header(fixture.token))

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        body = response.json()
        assert body["model_trained"] is True
        suggestion = next(s for s in body["reorder_suggestions"] if s["sku"] == "RECOMMEND-2")
        assert suggestion["reorder_quantity"] > 0
        assert suggestion["current_quantity"] == 5

    def test_does_not_suggest_reorder_for_well_stocked_product(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-3"
        )
        _seed_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=14,
            quantity=1,
            ending=date.today() - timedelta(days=1),
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10000)
        client.post(TRAIN_URL, headers=_auth_header(fixture.token))

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        skus = {s["sku"] for s in response.json()["reorder_suggestions"]}
        assert "RECOMMEND-3" not in skus


class TestOverstockWarnings:
    def test_flags_stock_above_maximum_quantity(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "RECOMMEND-4",
            maximum_quantity=50,
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 100)

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        warning = next(
            w for w in response.json()["overstock_warnings"] if w["sku"] == "RECOMMEND-4"
        )
        assert warning["current_quantity"] == 100
        assert warning["maximum_quantity"] == 50
        assert any("maximum_quantity" in reason for reason in warning["reasons"])

    def test_flags_slow_sell_through_pace(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-5"
        )
        _seed_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=60,
            quantity=1,
            ending=date.today(),
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10000)

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        warning = next(
            w for w in response.json()["overstock_warnings"] if w["sku"] == "RECOMMEND-5"
        )
        assert warning["days_of_supply"] > 180

    def test_no_warning_for_well_balanced_stock(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-6"
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10)

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        skus = {w["sku"] for w in response.json()["overstock_warnings"]}
        assert "RECOMMEND-6" not in skus


class TestSlowMovingProducts:
    def test_flags_product_never_sold(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-7"
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 20)

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        entry = next(
            p for p in response.json()["slow_moving_products"] if p["sku"] == "RECOMMEND-7"
        )
        assert entry["days_since_last_sale"] is None
        assert entry["quantity_sold_last_60_days"] == 0

    def test_flags_product_with_only_old_sales(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-8"
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 20)
        sale_id = _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 2)
        _backdate_sale_to_date(db_session, sale_id, date.today() - timedelta(days=100))

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        entry = next(
            p for p in response.json()["slow_moving_products"] if p["sku"] == "RECOMMEND-8"
        )
        assert entry["days_since_last_sale"] == 100

    def test_never_sold_products_sort_before_stale_ones(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        never_sold_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-9A"
        )
        _set_level(client, fixture.token, never_sold_id, fixture.warehouse_id, 20)
        stale_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-9B"
        )
        _set_level(client, fixture.token, stale_id, fixture.warehouse_id, 20)
        sale_id = _create_sale(client, fixture.token, fixture.warehouse_id, stale_id, 2)
        _backdate_sale_to_date(db_session, sale_id, date.today() - timedelta(days=90))

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        skus_in_order = [p["sku"] for p in response.json()["slow_moving_products"]]
        assert skus_in_order.index("RECOMMEND-9A") < skus_in_order.index("RECOMMEND-9B")

    def test_recently_sold_product_is_not_flagged(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-10"
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 20)
        _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 2)

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        skus = {p["sku"] for p in response.json()["slow_moving_products"]}
        assert "RECOMMEND-10" not in skus

    def test_out_of_stock_product_is_not_flagged_as_slow_moving(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-11"
        )

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        skus = {p["sku"] for p in response.json()["slow_moving_products"]}
        assert "RECOMMEND-11" not in skus


class TestSeasonalTrends:
    def test_detects_weekend_spike(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-12"
        )
        _seed_weighted_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=21,
            weekend_quantity=10,
            weekday_quantity=2,
            ending=date.today(),
        )

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        trend = next(t for t in response.json()["seasonal_trends"] if t["sku"] == "RECOMMEND-12")
        assert trend["pattern"] == "weekend_spike"
        assert trend["weekend_to_weekday_ratio"] > 1.5

    def test_detects_weekday_light(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-13"
        )
        _seed_weighted_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=21,
            weekend_quantity=1,
            weekday_quantity=10,
            ending=date.today(),
        )

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        trend = next(t for t in response.json()["seasonal_trends"] if t["sku"] == "RECOMMEND-13")
        assert trend["pattern"] == "weekday_light"

    def test_no_trend_for_flat_sales(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-14"
        )
        _seed_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=21,
            quantity=5,
            ending=date.today(),
        )

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        skus = {t["sku"] for t in response.json()["seasonal_trends"]}
        assert "RECOMMEND-14" not in skus

    def test_no_trend_with_too_little_history(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "RECOMMEND-15"
        )
        _seed_weighted_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=6,
            weekend_quantity=10,
            weekday_quantity=1,
            ending=date.today(),
        )

        response = client.get(RECOMMENDATIONS_URL, headers=_auth_header(fixture.token))

        skus = {t["sku"] for t in response.json()["seasonal_trends"]}
        assert "RECOMMEND-15" not in skus
