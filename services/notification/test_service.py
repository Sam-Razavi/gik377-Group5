"""Tests for Notification Service mock mode."""

import os

os.environ["NOTIFICATION_MOCK_MODE"] = "true"

from fastapi.testclient import TestClient

import services.notification.db as db
from services.notification.providers import MockEmailProvider, MockSMSProvider
from services.notification.routes import router
from services.notification.service import (
    get_subscribers,
    send_notification,
    subscribe,
    trigger_for_location,
)

from fastapi import FastAPI


_app = FastAPI()
_app.include_router(router)
client = TestClient(_app)


def clear_mock_db():
    db._mock_subscribers.clear()
    db._mock_sent_log.clear()
    db._mock_visited.clear()


def test_notification_uses_mock_storage():
    assert db.using_mock_storage() is True


def test_mock_sms_provider_returns_success():
    result = MockSMSProvider().send("+46701234567", "Hej!")
    assert result == {"success": True, "channel": "sms", "detail": {"mock": True}}


def test_mock_email_provider_returns_success():
    result = MockEmailProvider().send("test@example.com", "Test", "Hej!")
    assert result == {"success": True, "channel": "email", "detail": {"mock": True}}


def test_subscribe_uses_in_memory_db():
    clear_mock_db()
    result = subscribe(
        "user_1",
        phone="+46701234567",
        email="test@example.com",
        sites=["site_1"],
    )

    assert result["success"] is True
    assert get_subscribers()["user_1"]["phone"] == "+46701234567"
    assert get_subscribers()["user_1"]["email"] == "test@example.com"
    assert get_subscribers()["user_1"]["sites"] == ["site_1"]


def test_send_notification_returns_success_in_mock_mode():
    clear_mock_db()
    result = send_notification("sms", "+46701234567", "Hej!", user_id="u1", site_id="s1")

    assert result["success"] is True
    assert result["channel"] == "sms"


def test_trigger_for_location_uses_mock_providers():
    clear_mock_db()
    subscribe("user_1", phone="+46701234567", email="test@example.com", sites=["site_1"])

    results = trigger_for_location("user_1", "site_1", "Drottningholm")

    assert len(results) == 2
    assert all(result["success"] for result in results)


def test_subscribe_route_works_in_mock_mode():
    clear_mock_db()
    response = client.post(
        "/api/notification/subscribe",
        json={
            "user_id": "route_user",
            "phone": "+46701234567",
            "sites": ["site_1"],
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
