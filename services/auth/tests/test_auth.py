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

def test_bankid_status_complete_creates_user_and_returns_token(monkeypatch):
    async def mock_collect_bankid_status(order_ref: str):
        return {
            "status": "complete",
            "hintCode": None,
            "orderRef": order_ref,
            "completionData": {
                "user": {
                    "personalNumber": "199001011234",
                    "name": "BankID Test User",
                }
            },
        }

    monkeypatch.setattr(
        "services.auth.router.collect_bankid_status",
        mock_collect_bankid_status,
    )

    response = client.get("/auth/bankid/status/test-order-ref")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "complete"
    assert data["orderRef"] == "test-order-ref"
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    user = data["user"]
    assert user["email"] == "bankid_199001011234@example.com"
    assert user["full_name"] == "BankID Test User"
    assert user["is_active"] is True

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

def test_bankid_status_complete_creates_user_and_returns_token(monkeypatch):
    async def mock_collect_bankid_status(order_ref: str):
        return {
            "status": "complete",
            "hintCode": None,
            "orderRef": order_ref,
            "completionData": {
                "user": {
                    "personalNumber": "199001011234",
                    "name": "BankID Test User",
                }
            },
        }

    monkeypatch.setattr(
        "services.auth.router.collect_bankid_status",
        mock_collect_bankid_status,
    )

    response = client.get("/auth/bankid/status/test-order-ref")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "complete"
    assert data["orderRef"] == "test-order-ref"
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    user = data["user"]
    assert user["email"] == "bankid_199001011234@example.com"
    assert user["full_name"] == "BankID Test User"
    assert user["is_active"] is True

def test_bankid_status_complete_reuses_existing_user(monkeypatch):
    async def mock_collect_bankid_status(order_ref: str):
        return {
            "status": "complete",
            "hintCode": None,
            "orderRef": order_ref,
            "completionData": {
                "user": {
                    "personalNumber": "199001011234",
                    "name": "BankID Test User",
                }
            },
        }

    monkeypatch.setattr(
        "services.auth.router.collect_bankid_status",
        mock_collect_bankid_status,
    )

    first_response = client.get("/auth/bankid/status/test-order-ref-1")
    second_response = client.get("/auth/bankid/status/test-order-ref-2")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_user = first_response.json()["user"]
    second_user = second_response.json()["user"]

    assert first_user["id"] == second_user["id"]
    assert first_user["email"] == second_user["email"]

def test_bankid_status_complete_without_personal_number_fails(monkeypatch):
    async def mock_collect_bankid_status(order_ref: str):
        return {
            "status": "complete",
            "hintCode": None,
            "orderRef": order_ref,
            "completionData": {
                "user": {
                    "name": "BankID Test User",
                }
            },
        }

    monkeypatch.setattr(
        "services.auth.router.collect_bankid_status",
        mock_collect_bankid_status,
    )

    response = client.get("/auth/bankid/status/test-order-ref")

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "BankID completed but no personal number was returned"
    )

def test_bankid_status_pending_returns_pending_response(monkeypatch):
    async def mock_collect_bankid_status(order_ref: str):
        return {
            "status": "pending",
            "hintCode": "outstandingTransaction",
            "orderRef": order_ref,
            "completionData": None,
            "errorCode": None,
            "details": None,
        }

    monkeypatch.setattr(
        "services.auth.router.collect_bankid_status",
        mock_collect_bankid_status,
    )

    response = client.get("/auth/bankid/status/test-order-ref")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "pending"
    assert data["hintCode"] == "outstandingTransaction"
    assert data["orderRef"] == "test-order-ref"

def test_bankid_initiate_returns_order_data(monkeypatch):
    async def mock_initiate_bankid_auth():
        return {
            "orderRef": "test-order-ref",
            "autoStartToken": "test-auto-start-token",
            "qrStartToken": "test-qr-start-token",
            "qrStartSecret": "test-qr-start-secret",
        }

    monkeypatch.setattr(
        "services.auth.router.initiate_bankid_auth",
        mock_initiate_bankid_auth,
    )

    response = client.post("/auth/bankid/initiate")

    assert response.status_code == 200
    data = response.json()
    assert data["orderRef"] == "test-order-ref"
    assert "autoStartToken" in data
    assert "qrStartToken" in data
    assert "qrStartSecret" in data