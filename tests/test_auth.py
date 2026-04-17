from uuid import uuid4

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_user():
    unique_email = f"test_{uuid4().hex}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "password": "test1234",
            "full_name": "Test User",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["email"] == unique_email
    assert data["full_name"] == "Test User"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


def test_login_user():
    unique_email = f"login_{uuid4().hex}@example.com"
    password = "test1234"

    register_response = client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "password": password,
            "full_name": "Login User",
        },
    )

    assert register_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={
            "email": unique_email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    data = login_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email_fails():
    unique_email = f"duplicate_{uuid4().hex}@example.com"

    first_response = client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "password": "test1234",
            "full_name": "First User",
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "password": "test1234",
            "full_name": "Second User",
        },
    )

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "A user with this email already exists."


def test_get_current_user_with_token():
    unique_email = f"me_{uuid4().hex}@example.com"
    password = "test1234"

    register_response = client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "password": password,
            "full_name": "Me User",
        },
    )

    assert register_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={
            "email": unique_email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert me_response.status_code == 200

    data = me_response.json()
    assert data["email"] == unique_email
    assert data["full_name"] == "Me User"
    assert data["is_active"] is True


def test_login_with_wrong_password_fails():
    unique_email = f"wrongpass_{uuid4().hex}@example.com"

    register_response = client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "password": "correct123",
            "full_name": "Wrong Password User",
        },
    )

    assert register_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={
            "email": unique_email,
            "password": "wrong123",
        },
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Invalid email or password"


def test_get_current_user_without_token_fails():
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_get_current_user_with_invalid_token_fails():
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"