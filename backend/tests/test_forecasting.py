from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

import app.api.v1.endpoints.forecasting as forecasting_module
from app.core.config import Settings
from app.models.user import UserRole

TRAIN_URL = "/api/v1/forecasting/train"
PRODUCTS_URL = "/api/v1/products"


def _predict_url(product_id: int) -> str:
    return f"/api/v1/forecasting/products/{product_id}/predict"


@pytest.fixture(autouse=True)
def _isolate_ml_model_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Trained models are written to a per-test temp directory instead of
    the real backend/ml_artifacts/ folder, so tests never see a model left
    over from a previous test (or the real dev model) and never leave
    files behind - same technique as test_products.py's upload isolation."""
    fake_settings = Settings(ml_model_dir=str(tmp_path))
    monkeypatch.setattr(forecasting_module, "get_settings", lambda: fake_settings)


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
            "maximum_quantity": None,
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
            "customer_name": "Forecast Customer",
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


class Fixture:
    def __init__(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        self.token = auth_token_for(UserRole.MANAGER, email="forecast-manager@example.com")
        self.category_id = _create_category(client, self.token)
        self.supplier_id = _create_supplier(client, self.token, lead_time_days=7)
        self.warehouse_id = _create_warehouse(client, self.token)


def _make_fixture(client: TestClient, auth_token_for: Callable[..., str]) -> Fixture:
    return Fixture(client, auth_token_for)


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
    `ending`, backdated so the product has continuous daily history - the
    minimum shape build_next_day_feature_row/build_training_frame need."""
    # Stock the warehouse generously first - each sale deducts inventory,
    # and this helper cares about sales history, not stock-level edge cases.
    _set_level(client, token, product_id, warehouse_id, days * quantity * 2)
    start = ending - timedelta(days=days - 1)
    for offset in range(days):
        day = start + timedelta(days=offset)
        sale_id = _create_sale(client, token, warehouse_id, product_id, quantity)
        _backdate_sale(db_session, sale_id, datetime(day.year, day.month, day.day, 12, tzinfo=UTC))


class TestAccess:
    def test_train_requires_authentication(self, client: TestClient) -> None:
        assert client.post(TRAIN_URL).status_code == 401

    def test_train_requires_write_role(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)
        assert client.post(TRAIN_URL, headers=_auth_header(token)).status_code == 403

    def test_predict_requires_authentication(self, client: TestClient) -> None:
        assert client.get(_predict_url(1)).status_code == 401

    def test_predict_allows_any_authenticated_role(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "FORECAST-1"
        )
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="forecast-employee@example.com")

        # No model trained yet -> 409, but that already proves the RBAC
        # dependency let an employee through to the service.
        response = client.get(_predict_url(product_id), headers=_auth_header(employee_token))

        assert response.status_code == 409


class TestTrain:
    def test_fails_with_no_sales_history_at_all(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER, email="train-empty@example.com")

        response = client.post(TRAIN_URL, headers=_auth_header(token))

        assert response.status_code == 422

    def test_trains_successfully_with_some_history(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "FORECAST-2"
        )
        _seed_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=10,
            quantity=4,
            ending=date.today() - timedelta(days=1),
        )

        response = client.post(TRAIN_URL, headers=_auth_header(fixture.token))

        body = response.json()
        assert response.status_code == 200
        assert body["training_row_count"] == 3  # 10 days - 7 warm-up days
        assert body["accuracy"] is None  # too few rows for a train/test split
        assert set(body["feature_importance"].keys()) == {
            "product_id",
            "day_of_week",
            "day_of_month",
            "month",
            "lag_1",
            "rolling_mean_7",
        }


class TestPredict:
    def test_predict_before_training_is_409(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "FORECAST-3"
        )

        response = client.get(_predict_url(product_id), headers=_auth_header(fixture.token))

        assert response.status_code == 409

    def test_predict_for_unknown_product_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "FORECAST-4"
        )
        _seed_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=10,
            quantity=4,
            ending=date.today() - timedelta(days=1),
        )
        client.post(TRAIN_URL, headers=_auth_header(fixture.token))

        response = client.get(_predict_url(999999), headers=_auth_header(fixture.token))

        assert response.status_code == 404

    def test_predict_with_sufficient_history(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "FORECAST-5"
        )
        _seed_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=14,
            quantity=5,
            ending=date.today() - timedelta(days=1),
        )
        # Set the final on-hand quantity after seeding history, since
        # _seed_daily_sales itself stocks (and sales then deplete) the
        # warehouse to whatever level the historical sales needed.
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 100)
        client.post(TRAIN_URL, headers=_auth_header(fixture.token))

        response = client.get(_predict_url(product_id), headers=_auth_header(fixture.token))

        body = response.json()
        assert response.status_code == 200
        assert body["has_sufficient_history"] is True
        assert body["current_quantity"] == 100
        assert body["predicted_daily_demand"] > 0
        assert body["stock_depletion_date"] is not None
        assert 0.0 <= body["confidence_score"] <= 1.0
        assert body["reorder_quantity"] >= 0

    def test_predict_falls_back_for_product_with_no_history(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = _make_fixture(client, auth_token_for)
        trained_product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "FORECAST-6"
        )
        _seed_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            trained_product_id,
            days=10,
            quantity=4,
            ending=date.today() - timedelta(days=1),
        )
        client.post(TRAIN_URL, headers=_auth_header(fixture.token))

        never_sold_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "FORECAST-7",
            minimum_quantity=20,
        )
        _set_level(client, fixture.token, never_sold_id, fixture.warehouse_id, 3)

        response = client.get(_predict_url(never_sold_id), headers=_auth_header(fixture.token))

        body = response.json()
        assert response.status_code == 200
        assert body["has_sufficient_history"] is False
        assert body["predicted_daily_demand"] == 0.0
        assert body["stock_depletion_date"] is None
        assert body["confidence_score"] == 0.0
        # Falls back to "top up to minimum_quantity": 20 - 3 = 17.
        assert body["reorder_quantity"] == 17
