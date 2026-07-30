from fastapi.testclient import TestClient

AUTH_PREFIX = "/api/v1/auth"


def _register(
    client: TestClient, email: str = "alice@example.com", password: str = "hunter22"
) -> dict:
    response = client.post(
        f"{AUTH_PREFIX}/register",
        json={"email": email, "password": password, "full_name": "Alice Example"},
    )
    return response.json() if response.status_code == 201 else {}


def _login(client: TestClient, email: str = "alice@example.com", password: str = "hunter22") -> str:
    response = client.post(f"{AUTH_PREFIX}/login", data={"username": email, "password": password})
    return response.json()["access_token"]


class TestRegister:
    def test_creates_an_employee_by_default(self, client: TestClient) -> None:
        response = client.post(
            f"{AUTH_PREFIX}/register",
            json={
                "email": "alice@example.com",
                "password": "hunter22",
                "full_name": "Alice Example",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "alice@example.com"
        assert body["role"] == "employee"
        assert body["is_active"] is True
        assert "hashed_password" not in body

    def test_duplicate_email_is_rejected(self, client: TestClient) -> None:
        _register(client)

        response = client.post(
            f"{AUTH_PREFIX}/register",
            json={
                "email": "alice@example.com",
                "password": "another-pass",
                "full_name": "Someone Else",
            },
        )

        assert response.status_code == 409

    def test_short_password_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            f"{AUTH_PREFIX}/register",
            json={"email": "alice@example.com", "password": "short", "full_name": "Alice Example"},
        )

        assert response.status_code == 422


class TestLogin:
    def test_valid_credentials_return_a_token(self, client: TestClient) -> None:
        _register(client)

        response = client.post(
            f"{AUTH_PREFIX}/login", data={"username": "alice@example.com", "password": "hunter22"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 0

    def test_wrong_password_is_rejected(self, client: TestClient) -> None:
        _register(client)

        response = client.post(
            f"{AUTH_PREFIX}/login",
            data={"username": "alice@example.com", "password": "wrong-password"},
        )

        assert response.status_code == 401

    def test_unknown_email_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            f"{AUTH_PREFIX}/login", data={"username": "nobody@example.com", "password": "hunter22"}
        )

        assert response.status_code == 401


class TestMe:
    def test_requires_a_token(self, client: TestClient) -> None:
        response = client.get(f"{AUTH_PREFIX}/me")

        assert response.status_code == 401

    def test_rejects_an_invalid_token(self, client: TestClient) -> None:
        response = client.get(
            f"{AUTH_PREFIX}/me", headers={"Authorization": "Bearer not-a-real-token"}
        )

        assert response.status_code == 401

    def test_returns_the_authenticated_user(self, client: TestClient) -> None:
        _register(client)
        token = _login(client)

        response = client.get(f"{AUTH_PREFIX}/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["email"] == "alice@example.com"


def test_password_reset_request_returns_a_generic_response(client: TestClient) -> None:
    response = client.post(
        f"{AUTH_PREFIX}/password-reset-request", json={"email": "nobody@example.com"}
    )

    assert response.status_code == 202
    assert "message" in response.json()
