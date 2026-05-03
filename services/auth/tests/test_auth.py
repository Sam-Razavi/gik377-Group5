import pyotp

from uuid import uuid4

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(
    email: str,
    password: str = "test1234",
    full_name: str = "Test User",
) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    ).json()["access_token"]


def _enable_2fa_for_user(token: str) -> str:
    secret = client.post(
        "/auth/2fa/setup",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["secret"]

    client.post(
        "/auth/2fa/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": pyotp.TOTP(secret).now()},
    )

    return secret


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

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
    assert data["two_factor_enabled"] is False
    assert "id" in data
    assert "created_at" in data


def test_register_without_full_name_succeeds():
    unique_email = f"nofullname_{uuid4().hex}@example.com"

    response = client.post(
        "/auth/register",
        json={"email": unique_email, "password": "test1234"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] is None


def test_register_duplicate_email_fails():
    unique_email = f"duplicate_{uuid4().hex}@example.com"

    client.post(
        "/auth/register",
        json={"email": unique_email, "password": "test1234", "full_name": "First User"},
    )

    second_response = client.post(
        "/auth/register",
        json={"email": unique_email, "password": "test1234", "full_name": "Second User"},
    )

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "A user with this email already exists."


def test_register_with_invalid_email_fails():
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "test1234", "full_name": "Bad Email"},
    )

    assert response.status_code == 422


def test_register_with_missing_password_fails():
    response = client.post(
        "/auth/register",
        json={"email": f"nopwd_{uuid4().hex}@example.com", "full_name": "No Password"},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_user():
    unique_email = f"login_{uuid4().hex}@example.com"
    password = "test1234"

    client.post(
        "/auth/register",
        json={"email": unique_email, "password": password, "full_name": "Login User"},
    )

    login_response = client.post(
        "/auth/login",
        json={"email": unique_email, "password": password},
    )

    assert login_response.status_code == 200

    data = login_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_with_wrong_password_fails():
    unique_email = f"wrongpass_{uuid4().hex}@example.com"

    client.post(
        "/auth/register",
        json={"email": unique_email, "password": "correct123", "full_name": "Wrong Password User"},
    )

    login_response = client.post(
        "/auth/login",
        json={"email": unique_email, "password": "wrong123"},
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Invalid email or password"


def test_login_with_nonexistent_email_fails():
    response = client.post(
        "/auth/login",
        json={"email": f"ghost_{uuid4().hex}@example.com", "password": "test1234"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------

def test_get_current_user_with_token():
    unique_email = f"me_{uuid4().hex}@example.com"
    password = "test1234"

    client.post(
        "/auth/register",
        json={"email": unique_email, "password": password, "full_name": "Me User"},
    )

    access_token = client.post(
        "/auth/login",
        json={"email": unique_email, "password": password},
    ).json()["access_token"]

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert me_response.status_code == 200

    data = me_response.json()
    assert data["email"] == unique_email
    assert data["full_name"] == "Me User"
    assert data["is_active"] is True


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


# ---------------------------------------------------------------------------
# Profile update
# ---------------------------------------------------------------------------

def test_update_profile_full_name():
    email = f"profile_{uuid4().hex}@example.com"
    token = _register_and_login(email, full_name="Old Name")

    response = client.patch(
        "/auth/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "New Name"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "New Name"


def test_update_profile_home_address_and_coords():
    email = f"homeaddr_{uuid4().hex}@example.com"
    token = _register_and_login(email)

    response = client.patch(
        "/auth/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"home_address": "Main Street 1", "home_lat": 59.3293, "home_lon": 18.0686},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["home_address"] == "Main Street 1"
    assert data["home_lat"] == 59.3293
    assert data["home_lon"] == 18.0686


def test_update_profile_partial_does_not_clear_other_fields():
    email = f"partial_{uuid4().hex}@example.com"
    token = _register_and_login(email, full_name="Keep Me")

    client.patch(
        "/auth/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"home_address": "First Street"},
    )

    response = client.patch(
        "/auth/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"home_lat": 55.0},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["full_name"] == "Keep Me"
    assert data["home_address"] == "First Street"
    assert data["home_lat"] == 55.0


def test_update_profile_without_token_fails():
    response = client.patch("/auth/me/profile", json={"full_name": "Hacker"})

    assert response.status_code == 401


def test_get_me_reflects_updated_profile():
    email = f"reflectprofile_{uuid4().hex}@example.com"
    token = _register_and_login(email)

    client.patch(
        "/auth/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Updated Name", "home_address": "Updated Street"},
    )

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200

    data = me_response.json()
    assert data["full_name"] == "Updated Name"
    assert data["home_address"] == "Updated Street"


# ---------------------------------------------------------------------------
# 2FA status
# ---------------------------------------------------------------------------

def test_two_factor_status_is_false_for_new_user():
    email = f"2fastatus_{uuid4().hex}@example.com"
    token = _register_and_login(email)

    response = client.get(
        "/auth/2fa/status",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["two_factor_enabled"] is False


def test_two_factor_status_is_true_after_enabling():
    email = f"2fastatuson_{uuid4().hex}@example.com"
    token = _register_and_login(email)

    _enable_2fa_for_user(token)

    response = client.get(
        "/auth/2fa/status",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["two_factor_enabled"] is True


# ---------------------------------------------------------------------------
# 2FA setup
# ---------------------------------------------------------------------------

def test_setup_two_factor_returns_secret_and_uri():
    email = f"twofa_setup_{uuid4().hex}@example.com"
    token = _register_and_login(email)

    response = client.post(
        "/auth/2fa/setup",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert "secret" in data
    assert "provisioning_uri" in data
    assert data["provisioning_uri"].startswith("otpauth://")


def test_setup_two_factor_for_bankid_user_fails(monkeypatch):
    personal_number = f"19900101{uuid4().int % 10000:04d}"

    async def mock_collect_bankid_status(order_ref: str):
        return {
            "status": "complete",
            "hintCode": None,
            "orderRef": order_ref,
            "completionData": {
                "user": {
                    "personalNumber": personal_number,
                    "name": "BankID Only User",
                }
            },
        }

    monkeypatch.setattr("services.auth.router.collect_bankid_status", mock_collect_bankid_status)

    bankid_token = client.get(
        "/auth/bankid/status/setup-bankid-ref"
    ).json()["access_token"]

    response = client.post(
        "/auth/2fa/setup",
        headers={"Authorization": f"Bearer {bankid_token}"},
    )

    assert response.status_code == 400
    assert "email/password" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 2FA enable
# ---------------------------------------------------------------------------

def test_enable_two_factor_and_login_requires_2fa():
    email = f"twofa_enable_{uuid4().hex}@example.com"
    password = "test1234"
    token = _register_and_login(email, password)

    secret = client.post(
        "/auth/2fa/setup",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["secret"]

    enable_response = client.post(
        "/auth/2fa/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": pyotp.TOTP(secret).now()},
    )

    assert enable_response.status_code == 200
    assert enable_response.json()["two_factor_enabled"] is True

    login_data = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    ).json()

    assert login_data["requires_2fa"] is True
    assert "temp_token" in login_data
    assert login_data["access_token"] is None


def test_enable_two_factor_with_wrong_code_fails():
    email = f"twofa_wrongcode_{uuid4().hex}@example.com"
    token = _register_and_login(email)

    client.post("/auth/2fa/setup", headers={"Authorization": f"Bearer {token}"})

    response = client.post(
        "/auth/2fa/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "000000"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid 2FA code"


def test_enable_two_factor_without_setup_fails():
    email = f"twofa_nosetup_{uuid4().hex}@example.com"
    token = _register_and_login(email)

    response = client.post(
        "/auth/2fa/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "123456"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "2FA setup has not been started"


# ---------------------------------------------------------------------------
# 2FA disable
# ---------------------------------------------------------------------------

def test_disable_two_factor_with_valid_code():
    email = f"disable2fa_{uuid4().hex}@example.com"
    token = _register_and_login(email)
    secret = _enable_2fa_for_user(token)

    response = client.post(
        "/auth/2fa/disable",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": pyotp.TOTP(secret).now()},
    )

    assert response.status_code == 200
    assert response.json()["two_factor_enabled"] is False


def test_disable_two_factor_with_wrong_code_fails():
    email = f"disable2fa_wrong_{uuid4().hex}@example.com"
    token = _register_and_login(email)
    _enable_2fa_for_user(token)

    response = client.post(
        "/auth/2fa/disable",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "000000"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid 2FA code"


def test_disable_two_factor_when_not_enabled_fails():
    email = f"disable2fa_notenabled_{uuid4().hex}@example.com"
    token = _register_and_login(email)

    response = client.post(
        "/auth/2fa/disable",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "123456"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "2FA is not enabled"


def test_login_after_disable_two_factor_returns_token_directly():
    email = f"disable2fa_relogin_{uuid4().hex}@example.com"
    password = "test1234"
    token = _register_and_login(email, password)
    secret = _enable_2fa_for_user(token)

    client.post(
        "/auth/2fa/disable",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": pyotp.TOTP(secret).now()},
    )

    login_data = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    ).json()

    assert "access_token" in login_data
    assert login_data["requires_2fa"] is False


# ---------------------------------------------------------------------------
# 2FA login completion
# ---------------------------------------------------------------------------

def test_complete_two_factor_login_returns_access_token():
    email = f"twofa_login_{uuid4().hex}@example.com"
    password = "test1234"
    token = _register_and_login(email, password)
    secret = _enable_2fa_for_user(token)

    temp_token = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    ).json()["temp_token"]

    complete_response = client.post(
        "/auth/login/2fa",
        json={"temp_token": temp_token, "code": pyotp.TOTP(secret).now()},
    )

    assert complete_response.status_code == 200

    data = complete_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_2fa_with_invalid_temp_token_fails():
    response = client.post(
        "/auth/login/2fa",
        json={"temp_token": "this.is.garbage", "code": "123456"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired 2FA temporary token"


def test_login_2fa_with_wrong_code_fails():
    email = f"twofa_wrongotp_{uuid4().hex}@example.com"
    password = "test1234"
    token = _register_and_login(email, password)
    _enable_2fa_for_user(token)

    temp_token = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    ).json()["temp_token"]

    response = client.post(
        "/auth/login/2fa",
        json={"temp_token": temp_token, "code": "000000"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid 2FA code"


# ---------------------------------------------------------------------------
# BankID
# ---------------------------------------------------------------------------

def test_bankid_initiate_returns_order_data(monkeypatch):
    async def mock_initiate_bankid_auth():
        return {
            "orderRef": "test-order-ref",
            "autoStartToken": "test-auto-start-token",
            "qrStartToken": "test-qr-start-token",
            "qrStartSecret": "test-qr-start-secret",
        }

    monkeypatch.setattr("services.auth.router.initiate_bankid_auth", mock_initiate_bankid_auth)

    response = client.post("/auth/bankid/initiate")

    assert response.status_code == 200

    data = response.json()
    assert data["orderRef"] == "test-order-ref"
    assert "autoStartToken" in data
    assert "qrStartToken" in data
    assert "qrStartSecret" in data


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

    monkeypatch.setattr("services.auth.router.collect_bankid_status", mock_collect_bankid_status)

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

    monkeypatch.setattr("services.auth.router.collect_bankid_status", mock_collect_bankid_status)

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

    monkeypatch.setattr("services.auth.router.collect_bankid_status", mock_collect_bankid_status)

    response = client.get("/auth/bankid/status/test-order-ref")

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "BankID completed but no personal number was returned"
    )


def test_bankid_status_complete_without_name_creates_user_with_none_name(monkeypatch):
    personal_number = f"19900101{uuid4().int % 10000:04d}"

    async def mock_collect_bankid_status(order_ref: str):
        return {
            "status": "complete",
            "hintCode": None,
            "orderRef": order_ref,
            "completionData": {
                "user": {
                    "personalNumber": personal_number,
                }
            },
        }

    monkeypatch.setattr("services.auth.router.collect_bankid_status", mock_collect_bankid_status)

    response = client.get("/auth/bankid/status/noname-ref")

    assert response.status_code == 200
    assert response.json()["user"]["full_name"] is None


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

    monkeypatch.setattr("services.auth.router.collect_bankid_status", mock_collect_bankid_status)

    response = client.get("/auth/bankid/status/test-order-ref")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "pending"
    assert data["hintCode"] == "outstandingTransaction"
    assert data["orderRef"] == "test-order-ref"


def test_bankid_status_failed_returns_failed_response(monkeypatch):
    async def mock_collect_bankid_status(order_ref: str):
        return {
            "status": "failed",
            "hintCode": "userCancel",
            "orderRef": order_ref,
            "completionData": None,
            "errorCode": None,
            "details": None,
        }

    monkeypatch.setattr("services.auth.router.collect_bankid_status", mock_collect_bankid_status)

    response = client.get("/auth/bankid/status/cancelled-ref")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "failed"
    assert data["hintCode"] == "userCancel"


def test_bankid_user_cannot_login_with_email_password(monkeypatch):
    personal_number = f"19900201{uuid4().int % 10000:04d}"

    async def mock_collect_bankid_status(order_ref: str):
        return {
            "status": "complete",
            "hintCode": None,
            "orderRef": order_ref,
            "completionData": {
                "user": {
                    "personalNumber": personal_number,
                    "name": "BankID Only User",
                }
            },
        }

    monkeypatch.setattr("services.auth.router.collect_bankid_status", mock_collect_bankid_status)

    bankid_email = client.get(
        "/auth/bankid/status/bankid-only-ref"
    ).json()["user"]["email"]

    login_response = client.post(
        "/auth/login",
        json={"email": bankid_email, "password": "anypassword"},
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Invalid email or password"
