from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.user import UserRole

NOTIFICATIONS_URL = "/api/v1/notifications"
PRODUCTS_URL = "/api/v1/products"
PURCHASE_ORDERS_URL = "/api/v1/purchase-orders"
SALES_URL = "/api/v1/sales"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_category(client: TestClient, token: str, name: str = "Electronics") -> int:
    response = client.post("/api/v1/categories", json={"name": name}, headers=_auth_header(token))
    return int(response.json()["id"])


def _create_supplier(client: TestClient, token: str, company_name: str = "Acme Supply Co.") -> int:
    response = client.post(
        "/api/v1/suppliers",
        json={
            "company_name": company_name,
            "contact_person": "Jane Doe",
            "email": "jane@acme.example",
            "phone": "555-0100",
            "address": "123 Warehouse Rd",
            "lead_time_days": 7,
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
    minimum_quantity: int = 0,
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
        SALES_URL,
        json={
            "warehouse_id": warehouse_id,
            "customer_name": "Notification Test Customer",
            "items": [{"product_id": product_id, "quantity": quantity, "unit_price": "9.99"}],
        },
        headers=_auth_header(token),
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _backdate_sale(db_session: Session, sale_id: int, created_at: datetime) -> None:
    db_session.execute(
        text("UPDATE sales SET created_at = :created_at WHERE id = :id"),
        {"created_at": created_at, "id": sale_id},
    )
    db_session.commit()


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
    """One sale per day for `days` consecutive days ending on `ending`,
    backdated so the product has continuous prior-day history for anomaly
    detection to compare against."""
    _set_level(client, token, product_id, warehouse_id, days * quantity * 10)
    start = ending - timedelta(days=days - 1)
    for offset in range(days):
        day = start + timedelta(days=offset)
        sale_id = _create_sale(client, token, warehouse_id, product_id, quantity)
        _backdate_sale(db_session, sale_id, datetime(day.year, day.month, day.day, 12, tzinfo=UTC))


def _create_purchase_order(
    client: TestClient,
    token: str,
    supplier_id: int,
    warehouse_id: int,
    product_id: int,
    quantity: int,
) -> int:
    response = client.post(
        PURCHASE_ORDERS_URL,
        json={
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_id,
            "notes": None,
            "items": [
                {"product_id": product_id, "quantity_ordered": quantity, "unit_cost": "4.25"}
            ],
        },
        headers=_auth_header(token),
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def _receive_purchase_order(client: TestClient, token: str, purchase_order_id: int) -> None:
    client.post(f"{PURCHASE_ORDERS_URL}/{purchase_order_id}/ship", headers=_auth_header(token))
    response = client.post(
        f"{PURCHASE_ORDERS_URL}/{purchase_order_id}/receive", headers=_auth_header(token)
    )
    assert response.status_code == 200, response.text


class Fixture:
    def __init__(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        self.token = auth_token_for(UserRole.MANAGER, email="notif-manager@example.com")
        self.category_id = _create_category(client, self.token)
        self.supplier_id = _create_supplier(client, self.token)
        self.warehouse_id = _create_warehouse(client, self.token)


def _list_notifications(
    client: TestClient, token: str, unread_only: bool = False
) -> list[dict[str, object]]:
    response = client.get(
        NOTIFICATIONS_URL,
        params={"unread_only": unread_only},
        headers=_auth_header(token),
    )
    assert response.status_code == 200, response.text
    return list(response.json()["items"])


class TestAccess:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get(NOTIFICATIONS_URL).status_code == 401

    def test_any_authenticated_role_can_list(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(NOTIFICATIONS_URL, headers=_auth_header(token))

        assert response.status_code == 200
        body = response.json()
        assert body == {"items": [], "total": 0, "page": 1, "page_size": 20}


class TestLowStockTrigger:
    def test_sale_crossing_minimum_creates_low_stock_notification(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "LOW-1",
            minimum_quantity=5,
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10)

        _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 6)

        notifications = _list_notifications(client, fixture.token)
        low_stock = [n for n in notifications if n["type"] == "low_stock"]
        assert len(low_stock) == 1
        assert low_stock[0]["product_id"] == product_id
        assert low_stock[0]["severity"] == "warning"
        assert low_stock[0]["is_read"] is False

    def test_sale_not_crossing_minimum_does_not_create_notification(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "LOW-2",
            minimum_quantity=5,
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10)

        _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 2)

        notifications = _list_notifications(client, fixture.token)
        assert [n for n in notifications if n["type"] == "low_stock"] == []

    def test_selling_to_zero_creates_critical_severity(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "LOW-3",
            minimum_quantity=5,
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10)

        _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 10)

        notifications = _list_notifications(client, fixture.token)
        low_stock = [n for n in notifications if n["type"] == "low_stock"]
        assert len(low_stock) == 1
        assert low_stock[0]["severity"] == "critical"

    def test_recrossing_while_unread_does_not_duplicate(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "LOW-4",
            minimum_quantity=5,
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10)
        _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 6)  # crosses: 10 -> 4

        # Restock above the minimum, then cross below it again while the
        # first low-stock notification is still unread.
        purchase_order_id = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, product_id, 20
        )
        _receive_purchase_order(client, fixture.token, purchase_order_id)  # 4 -> 24
        _create_sale(
            client, fixture.token, fixture.warehouse_id, product_id, 21
        )  # crosses: 24 -> 3

        notifications = _list_notifications(client, fixture.token)
        low_stock = [n for n in notifications if n["type"] == "low_stock"]
        assert len(low_stock) == 1

    def test_recrossing_after_acknowledging_creates_a_new_notification(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "LOW-5",
            minimum_quantity=5,
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10)
        _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 6)  # crosses: 10 -> 4

        first = [n for n in _list_notifications(client, fixture.token) if n["type"] == "low_stock"][
            0
        ]
        client.patch(f"{NOTIFICATIONS_URL}/{first['id']}/read", headers=_auth_header(fixture.token))

        purchase_order_id = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, product_id, 20
        )
        _receive_purchase_order(client, fixture.token, purchase_order_id)  # 4 -> 24
        _create_sale(
            client, fixture.token, fixture.warehouse_id, product_id, 21
        )  # crosses: 24 -> 3

        low_stock = [
            n for n in _list_notifications(client, fixture.token) if n["type"] == "low_stock"
        ]
        assert len(low_stock) == 2


class TestOverstockTrigger:
    def test_receiving_crossing_maximum_creates_overstock_notification(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "OVER-1",
            maximum_quantity=20,
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10)

        purchase_order_id = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, product_id, 15
        )
        _receive_purchase_order(client, fixture.token, purchase_order_id)

        notifications = _list_notifications(client, fixture.token)
        overstock = [n for n in notifications if n["type"] == "overstock"]
        assert len(overstock) == 1
        assert overstock[0]["product_id"] == product_id

    def test_receiving_not_crossing_maximum_does_not_create_notification(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "OVER-2",
            maximum_quantity=20,
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10)

        purchase_order_id = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, product_id, 5
        )
        _receive_purchase_order(client, fixture.token, purchase_order_id)

        notifications = _list_notifications(client, fixture.token)
        assert [n for n in notifications if n["type"] == "overstock"] == []


class TestOrderArrivedTrigger:
    def test_receiving_creates_order_arrived_notification(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "ARR-1"
        )

        purchase_order_id = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, product_id, 10
        )
        _receive_purchase_order(client, fixture.token, purchase_order_id)

        notifications = _list_notifications(client, fixture.token)
        arrived = [n for n in notifications if n["type"] == "order_arrived"]
        assert len(arrived) == 1
        assert arrived[0]["purchase_order_id"] == purchase_order_id
        assert arrived[0]["severity"] == "info"


class TestAnomalyTrigger:
    def test_sale_spike_creates_anomaly_notification(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "ANOM-1"
        )
        today = date.today()
        _seed_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=7,
            quantity=2,
            ending=today - timedelta(days=1),
        )

        _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 10)

        notifications = _list_notifications(client, fixture.token)
        anomalies = [n for n in notifications if n["type"] == "anomaly"]
        assert len(anomalies) == 1
        assert anomalies[0]["product_id"] == product_id

    def test_typical_sale_does_not_create_anomaly_notification(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "ANOM-2"
        )
        today = date.today()
        _seed_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=7,
            quantity=5,
            ending=today - timedelta(days=1),
        )

        _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 6)

        notifications = _list_notifications(client, fixture.token)
        assert [n for n in notifications if n["type"] == "anomaly"] == []

    def test_insufficient_history_does_not_create_anomaly_notification(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client, fixture.token, fixture.category_id, fixture.supplier_id, "ANOM-3"
        )
        today = date.today()
        _seed_daily_sales(
            client,
            db_session,
            fixture.token,
            fixture.warehouse_id,
            product_id,
            days=3,
            quantity=2,
            ending=today - timedelta(days=1),
        )

        _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 10)

        notifications = _list_notifications(client, fixture.token)
        assert [n for n in notifications if n["type"] == "anomaly"] == []


class TestListAndMarkRead:
    def test_unread_count_endpoint(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "MRK-1",
            minimum_quantity=5,
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10)
        _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 6)

        response = client.get(
            f"{NOTIFICATIONS_URL}/unread-count", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 200
        assert response.json() == {"count": 1}

    def test_unread_only_filter(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "MRK-2",
            minimum_quantity=5,
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10)
        _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 6)
        notification = _list_notifications(client, fixture.token)[0]
        client.patch(
            f"{NOTIFICATIONS_URL}/{notification['id']}/read", headers=_auth_header(fixture.token)
        )

        unread = _list_notifications(client, fixture.token, unread_only=True)

        assert unread == []

    def test_mark_read(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        fixture = Fixture(client, auth_token_for)
        product_id = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "MRK-3",
            minimum_quantity=5,
        )
        _set_level(client, fixture.token, product_id, fixture.warehouse_id, 10)
        _create_sale(client, fixture.token, fixture.warehouse_id, product_id, 6)
        notification = _list_notifications(client, fixture.token)[0]

        response = client.patch(
            f"{NOTIFICATIONS_URL}/{notification['id']}/read", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 200
        assert response.json()["is_read"] is True

    def test_mark_read_missing_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.patch(f"{NOTIFICATIONS_URL}/999/read", headers=_auth_header(token))

        assert response.status_code == 404

    def test_mark_all_read(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        fixture = Fixture(client, auth_token_for)
        product_a = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "MRK-4A",
            minimum_quantity=5,
        )
        product_b = _create_product(
            client,
            fixture.token,
            fixture.category_id,
            fixture.supplier_id,
            "MRK-4B",
            minimum_quantity=5,
        )
        _set_level(client, fixture.token, product_a, fixture.warehouse_id, 10)
        _set_level(client, fixture.token, product_b, fixture.warehouse_id, 10)
        _create_sale(client, fixture.token, fixture.warehouse_id, product_a, 6)
        _create_sale(client, fixture.token, fixture.warehouse_id, product_b, 6)

        response = client.patch(
            f"{NOTIFICATIONS_URL}/read-all", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 200
        assert response.json() == {"marked_count": 2}
        assert _list_notifications(client, fixture.token, unread_only=True) == []
