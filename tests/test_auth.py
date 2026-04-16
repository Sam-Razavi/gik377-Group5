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