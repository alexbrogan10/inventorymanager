from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models.user import UserRole

WAREHOUSES_URL = "/api/v1/warehouses"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_warehouse(
    client: TestClient, token: str, name: str = "Main Warehouse", address: str = "123 Storage Rd"
) -> dict:
    response = client.post(
        WAREHOUSES_URL,
        json={"name": name, "address": address, "notes": None},
        headers=_auth_header(token),
    )
    return response.json()


class TestReadAccess:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get(WAREHOUSES_URL).status_code == 401

    def test_any_authenticated_role_can_list(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(WAREHOUSES_URL, headers=_auth_header(token))

        assert response.status_code == 200
        assert response.json() == []

    def test_get_missing_warehouse_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(f"{WAREHOUSES_URL}/999", headers=_auth_header(token))

        assert response.status_code == 404


class TestWriteAccess:
    def test_employee_cannot_create(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.post(
            WAREHOUSES_URL,
            json={"name": "Main Warehouse", "address": "123 Storage Rd"},
            headers=_auth_header(token),
        )

        assert response.status_code == 403

    def test_manager_can_create(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.post(
            WAREHOUSES_URL,
            json={"name": "Main Warehouse", "address": "123 Storage Rd", "notes": "HQ"},
            headers=_auth_header(token),
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Main Warehouse"
        assert body["notes"] == "HQ"

    def test_admin_can_create(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        token = auth_token_for(UserRole.ADMIN)

        response = client.post(
            WAREHOUSES_URL,
            json={"name": "East Warehouse", "address": "456 East St"},
            headers=_auth_header(token),
        )

        assert response.status_code == 201

    def test_duplicate_name_conflicts(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        _create_warehouse(client, token, name="Main Warehouse")

        response = client.post(
            WAREHOUSES_URL,
            json={"name": "Main Warehouse", "address": "Somewhere else"},
            headers=_auth_header(token),
        )

        assert response.status_code == 409


class TestUpdate:
    def test_manager_can_update(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        warehouse = _create_warehouse(client, token, name="Main Warehouse")

        response = client.put(
            f"{WAREHOUSES_URL}/{warehouse['id']}",
            json={"name": "Main Warehouse (renamed)", "address": "123 Storage Rd"},
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Main Warehouse (renamed)"

    def test_employee_cannot_update(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        manager_token = auth_token_for(UserRole.MANAGER, email="manager@example.com")
        warehouse = _create_warehouse(client, manager_token)
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = client.put(
            f"{WAREHOUSES_URL}/{warehouse['id']}",
            json={"name": "Hacked", "address": "n/a"},
            headers=_auth_header(employee_token),
        )

        assert response.status_code == 403

    def test_update_missing_warehouse_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.put(
            f"{WAREHOUSES_URL}/999",
            json={"name": "Anything", "address": "n/a"},
            headers=_auth_header(token),
        )

        assert response.status_code == 404

    def test_renaming_to_another_warehouses_name_conflicts(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        _create_warehouse(client, token, name="Main Warehouse")
        east = _create_warehouse(client, token, name="East Warehouse")

        response = client.put(
            f"{WAREHOUSES_URL}/{east['id']}",
            json={"name": "Main Warehouse", "address": "456 East St"},
            headers=_auth_header(token),
        )

        assert response.status_code == 409


class TestDelete:
    def test_manager_can_delete(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        warehouse = _create_warehouse(client, token)

        delete_response = client.delete(
            f"{WAREHOUSES_URL}/{warehouse['id']}", headers=_auth_header(token)
        )
        get_response = client.get(
            f"{WAREHOUSES_URL}/{warehouse['id']}", headers=_auth_header(token)
        )

        assert delete_response.status_code == 204
        assert get_response.status_code == 404

    def test_employee_cannot_delete(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        manager_token = auth_token_for(UserRole.MANAGER, email="manager@example.com")
        warehouse = _create_warehouse(client, manager_token)
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = client.delete(
            f"{WAREHOUSES_URL}/{warehouse['id']}", headers=_auth_header(employee_token)
        )

        assert response.status_code == 403

    def test_delete_missing_warehouse_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.delete(f"{WAREHOUSES_URL}/999", headers=_auth_header(token))

        assert response.status_code == 404
