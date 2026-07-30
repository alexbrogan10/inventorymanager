from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models.user import UserRole

CATEGORIES_URL = "/api/v1/categories"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_category(
    client: TestClient, token: str, name: str = "Electronics", description: str | None = "Gadgets"
) -> dict:
    response = client.post(
        CATEGORIES_URL, json={"name": name, "description": description}, headers=_auth_header(token)
    )
    return response.json()


class TestReadAccess:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get(CATEGORIES_URL).status_code == 401

    def test_any_authenticated_role_can_list(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(CATEGORIES_URL, headers=_auth_header(token))

        assert response.status_code == 200
        assert response.json() == []

    def test_get_missing_category_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(f"{CATEGORIES_URL}/999", headers=_auth_header(token))

        assert response.status_code == 404


class TestWriteAccess:
    def test_employee_cannot_create(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.post(
            CATEGORIES_URL, json={"name": "Electronics"}, headers=_auth_header(token)
        )

        assert response.status_code == 403

    def test_manager_can_create(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.post(
            CATEGORIES_URL,
            json={"name": "Electronics", "description": "Gadgets"},
            headers=_auth_header(token),
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Electronics"
        assert body["description"] == "Gadgets"

    def test_admin_can_create(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        token = auth_token_for(UserRole.ADMIN)

        response = client.post(CATEGORIES_URL, json={"name": "Tools"}, headers=_auth_header(token))

        assert response.status_code == 201

    def test_duplicate_name_conflicts(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        _create_category(client, token, name="Electronics")

        response = client.post(
            CATEGORIES_URL, json={"name": "Electronics"}, headers=_auth_header(token)
        )

        assert response.status_code == 409


class TestUpdate:
    def test_manager_can_update(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        category = _create_category(client, token, name="Electronics")

        response = client.put(
            f"{CATEGORIES_URL}/{category['id']}",
            json={"name": "Consumer Electronics", "description": "Updated"},
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Consumer Electronics"

    def test_employee_cannot_update(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        manager_token = auth_token_for(UserRole.MANAGER, email="manager@example.com")
        category = _create_category(client, manager_token, name="Electronics")
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = client.put(
            f"{CATEGORIES_URL}/{category['id']}",
            json={"name": "Hacked"},
            headers=_auth_header(employee_token),
        )

        assert response.status_code == 403

    def test_update_missing_category_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.put(
            f"{CATEGORIES_URL}/999", json={"name": "Anything"}, headers=_auth_header(token)
        )

        assert response.status_code == 404

    def test_renaming_to_another_categorys_name_conflicts(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        _create_category(client, token, name="Electronics")
        tools = _create_category(client, token, name="Tools")

        response = client.put(
            f"{CATEGORIES_URL}/{tools['id']}",
            json={"name": "Electronics"},
            headers=_auth_header(token),
        )

        assert response.status_code == 409


class TestDelete:
    def test_manager_can_delete(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        category = _create_category(client, token)

        delete_response = client.delete(
            f"{CATEGORIES_URL}/{category['id']}", headers=_auth_header(token)
        )
        get_response = client.get(f"{CATEGORIES_URL}/{category['id']}", headers=_auth_header(token))

        assert delete_response.status_code == 204
        assert get_response.status_code == 404

    def test_employee_cannot_delete(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        manager_token = auth_token_for(UserRole.MANAGER, email="manager@example.com")
        category = _create_category(client, manager_token)
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = client.delete(
            f"{CATEGORIES_URL}/{category['id']}", headers=_auth_header(employee_token)
        )

        assert response.status_code == 403

    def test_delete_missing_category_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.delete(f"{CATEGORIES_URL}/999", headers=_auth_header(token))

        assert response.status_code == 404
