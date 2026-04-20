"""Tester för Notification Service."""

import sys
import os

# Måste sättas INNAN någon modul importeras
os.environ["HELLOSMS_USERNAME"] = os.environ.get("HELLOSMS_USERNAME", "test_user")
os.environ["HELLOSMS_PASSWORD"] = os.environ.get("HELLOSMS_PASSWORD", "test_pass")
os.environ["SMTP2GO_API_KEY"] = os.environ.get("SMTP2GO_API_KEY", "test_key")

# PostgreSQL-inställningar för tester (använd en separat testdatabas)
os.environ.setdefault("NOTIFICATION_PG_HOST", "localhost")
os.environ.setdefault("NOTIFICATION_PG_PORT", "5432")
os.environ.setdefault("NOTIFICATION_PG_DATABASE", "notification_test")
os.environ.setdefault("NOTIFICATION_PG_USER", "postgres")
os.environ.setdefault("NOTIFICATION_PG_PASSWORD", "postgres")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import unittest
from unittest.mock import patch

from services.notification import db
from services.notification.service import (
    send_notification,
    subscribe,
    unsubscribe,
    get_subscribers,
    trigger_for_location,
)


class BaseTestCase(unittest.TestCase):
    """Rensa databasen innan varje test."""

    def setUp(self):
        conn = db._connect()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sent_log")
            cur.execute("DELETE FROM subscriber_sites")
            cur.execute("DELETE FROM subscribers")
        conn.commit()
        conn.close()


class TestSendNotification(BaseTestCase):

    @patch("services.notification.service.sms_provider")
    def test_send_sms_success(self, mock_sms):
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        result = send_notification("sms", "+46701234567", "Hej!")
        self.assertTrue(result["success"])
        mock_sms.send.assert_called_once_with(to="+46701234567", message="Hej!")

    @patch("services.notification.service.email_provider")
    def test_send_email_success(self, mock_email):
        mock_email.send.return_value = {"success": True, "channel": "email", "detail": {}}
        result = send_notification("email", "test@example.com", "Hej!", subject="Test")
        self.assertTrue(result["success"])
        mock_email.send.assert_called_once()

    def test_send_unknown_type_returns_error(self):
        result = send_notification("fax", "+46701234567", "Hej!")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "invalid_type")

    def test_send_sms_invalid_phone(self):
        result = send_notification("sms", "not-a-phone", "Hej!")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "invalid_recipient")

    def test_send_email_invalid_address(self):
        result = send_notification("email", "not-an-email", "Hej!")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "invalid_recipient")

    @patch("services.notification.service.sms_provider")
    def test_cooldown_blocks_same_channel(self, mock_sms):
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        send_notification("sms", "+46701234567", "Hej!", user_id="u1", site_id="s1")
        result = send_notification("sms", "+46701234567", "Hej!", user_id="u1", site_id="s1")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "cooldown")

    @patch("services.notification.service.email_provider")
    @patch("services.notification.service.sms_provider")
    def test_cooldown_does_not_block_different_channel(self, mock_sms, mock_email):
        """SMS-cooldown ska inte blockera e-post för samma plats."""
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        mock_email.send.return_value = {"success": True, "channel": "email", "detail": {}}
        send_notification("sms", "+46701234567", "Hej!", user_id="u1", site_id="s1")
        result = send_notification("email", "test@example.com", "Hej!", user_id="u1", site_id="s1")
        self.assertTrue(result["success"])


class TestSubscription(BaseTestCase):

    @patch("services.notification.service.sms_provider")
    def test_subscribe_new_user(self, mock_sms):
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        result = subscribe("u1", phone="+46701234567", sites=["s1"])
        self.assertTrue(result["success"])
        self.assertIn("u1", get_subscribers())

    @patch("services.notification.service.email_provider")
    @patch("services.notification.service.sms_provider")
    def test_subscribe_updates_existing(self, mock_sms, mock_email):
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        mock_email.send.return_value = {"success": True, "channel": "email", "detail": {}}
        subscribe("u1", phone="+46701234567", sites=["s1"])
        subscribe("u1", email="a@b.com", sites=["s2"])
        sub = get_subscribers()["u1"]
        self.assertEqual(sub["phone"], "+46701234567")
        self.assertEqual(sub["email"], "a@b.com")
        self.assertIn("s1", sub["sites"])
        self.assertIn("s2", sub["sites"])

    def test_subscribe_invalid_phone(self):
        result = subscribe("u1", phone="abc")
        self.assertFalse(result["success"])

    def test_subscribe_invalid_email(self):
        result = subscribe("u1", email="abc")
        self.assertFalse(result["success"])

    def test_subscribe_sites_must_be_list(self):
        result = subscribe("u1", sites="not-a-list")
        self.assertFalse(result["success"])

    @patch("services.notification.service.sms_provider")
    def test_unsubscribe_all(self, mock_sms):
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        subscribe("u1", phone="+46701234567", sites=["s1"])
        unsubscribe("u1")
        self.assertNotIn("u1", get_subscribers())

    @patch("services.notification.service.sms_provider")
    def test_unsubscribe_specific_sites(self, mock_sms):
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        subscribe("u1", phone="+46701234567", sites=["s1", "s2"])
        unsubscribe("u1", sites=["s1"])
        self.assertEqual(get_subscribers()["u1"]["sites"], ["s2"])

    def test_unsubscribe_nonexistent_user(self):
        result = unsubscribe("ghost")
        self.assertFalse(result["success"])

    @patch("services.notification.service.sms_provider")
    def test_welcome_sms_sent_on_new_subscribe(self, mock_sms):
        """Välkomst-SMS ska skickas vid ny registrering."""
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        subscribe("u1", phone="+46701234567", sites=["s1"])
        # Första anropet är välkomstmeddelandet
        welcome_call = mock_sms.send.call_args_list[0]
        self.assertIn("Tack för att du registrerat dig", welcome_call[1]["message"])

    @patch("services.notification.service.email_provider")
    def test_welcome_email_sent_on_new_subscribe(self, mock_email):
        """Välkomstmejl ska skickas vid ny registrering."""
        mock_email.send.return_value = {"success": True, "channel": "email", "detail": {}}
        subscribe("u1", email="a@b.com", sites=["s1"])
        welcome_call = mock_email.send.call_args_list[0]
        self.assertIn("Välkommen", welcome_call[1]["subject"])

    @patch("services.notification.service.sms_provider")
    def test_unsubscribe_confirmation_sms_sent(self, mock_sms):
        """Bekräftelse-SMS ska skickas vid avprenumeration."""
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        subscribe("u1", phone="+46701234567", sites=["s1"])
        mock_sms.send.reset_mock()
        unsubscribe("u1")
        unsub_call = mock_sms.send.call_args_list[0]
        self.assertIn("avregistrerats", unsub_call[1]["message"])


class TestTriggerForLocation(BaseTestCase):

    def test_trigger_no_subscription(self):
        results = trigger_for_location("u1", "s1", "Drottningholm")
        self.assertFalse(results[0]["success"])

    @patch("services.notification.service.sms_provider")
    def test_trigger_not_subscribed_to_site(self, mock_sms):
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        subscribe("u1", phone="+46701234567", sites=["s2"])
        results = trigger_for_location("u1", "s1", "Drottningholm")
        self.assertFalse(results[0]["success"])

    @patch("services.notification.service.sms_provider")
    def test_trigger_sends_sms_with_correct_message(self, mock_sms):
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        subscribe("u1", phone="+46701234567", sites=["s1"])
        results = trigger_for_location("u1", "s1", "Drottningholm")
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["success"])
        # Verifiera att rätt meddelande skickades (location trigger, inte welcome)
        trigger_call = mock_sms.send.call_args_list[-1]
        self.assertIn("Du är nära Drottningholm", trigger_call[1]["message"])

    @patch("services.notification.service.email_provider")
    @patch("services.notification.service.sms_provider")
    def test_trigger_sends_both_sms_and_email(self, mock_sms, mock_email):
        """Både SMS och e-post ska skickas utan att cooldown blockerar."""
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        mock_email.send.return_value = {"success": True, "channel": "email", "detail": {}}
        subscribe("u1", phone="+46701234567", email="a@b.com", sites=["s1"])
        results = trigger_for_location("u1", "s1", "Drottningholm")
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]["success"])
        self.assertTrue(results[1]["success"])

    @patch("services.notification.service.email_provider")
    @patch("services.notification.service.sms_provider")
    def test_trigger_cooldown_blocks_second_trigger(self, mock_sms, mock_email):
        """Andra triggern för samma plats ska blockeras per kanal."""
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        mock_email.send.return_value = {"success": True, "channel": "email", "detail": {}}
        subscribe("u1", phone="+46701234567", email="a@b.com", sites=["s1"])

        results1 = trigger_for_location("u1", "s1", "Drottningholm")
        self.assertTrue(results1[0]["success"])
        self.assertTrue(results1[1]["success"])

        results2 = trigger_for_location("u1", "s1", "Drottningholm")
        self.assertFalse(results2[0]["success"])
        self.assertEqual(results2[0]["error"], "cooldown")
        self.assertFalse(results2[1]["success"])
        self.assertEqual(results2[1]["error"], "cooldown")

    def test_trigger_no_contact_info(self):
        # Lägg till direkt i DB utan välkomstmeddelande
        db.add_subscriber("u1", sites=["s1"])
        results = trigger_for_location("u1", "s1", "Drottningholm")
        self.assertFalse(results[0]["success"])
        self.assertIn("kontaktinfo", results[0]["error"])

    @patch("services.notification.service.sms_provider")
    def test_trigger_includes_link(self, mock_sms):
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        subscribe("u1", phone="+46701234567", sites=["s1"])
        trigger_for_location("u1", "s1", "Drottningholm", link="https://example.com")
        trigger_call = mock_sms.send.call_args_list[-1]
        self.assertIn("Läs mer: https://example.com", trigger_call[1]["message"])


class TestRoutes(BaseTestCase):
    """Testar Flask-endpoints direkt."""

    def setUp(self):
        super().setUp()
        from flask import Flask
        from services.notification.routes import notification_bp
        app = Flask(__name__)
        app.register_blueprint(notification_bp)
        self.client = app.test_client()

    def test_health(self):
        resp = self.client.get("/notification/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "ok")

    def test_send_missing_body(self):
        resp = self.client.post("/notification/send-notification")
        self.assertEqual(resp.status_code, 400)

    def test_send_missing_fields(self):
        resp = self.client.post("/notification/send-notification",
                                json={"type": "sms"})
        self.assertEqual(resp.status_code, 400)

    def test_send_invalid_type_returns_400(self):
        resp = self.client.post("/notification/send-notification",
                                json={"type": "fax", "to": "+46701234567", "message": "hej"})
        self.assertEqual(resp.status_code, 400)

    @patch("services.notification.service.sms_provider")
    def test_send_sms_via_route(self, mock_sms):
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        resp = self.client.post("/notification/send-notification",
                                json={"type": "sms", "to": "+46701234567", "message": "Hej!"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])

    def test_trigger_missing_params(self):
        resp = self.client.get("/notification/trigger-notification")
        self.assertEqual(resp.status_code, 400)

    def test_subscribe_missing_user_id(self):
        resp = self.client.post("/notification/subscribe", json={})
        self.assertEqual(resp.status_code, 400)

    @patch("services.notification.service.sms_provider")
    def test_subscribe_via_route(self, mock_sms):
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        resp = self.client.post("/notification/subscribe",
                                json={"user_id": "u1", "phone": "+46701234567", "sites": ["s1"]})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])

    def test_unsubscribe_nonexistent(self):
        resp = self.client.post("/notification/unsubscribe",
                                json={"user_id": "ghost"})
        self.assertEqual(resp.status_code, 404)

    def test_subscribers_requires_token(self):
        resp = self.client.get("/notification/subscribers")
        self.assertEqual(resp.status_code, 403)

    @patch("services.notification.routes.ADMIN_TOKEN", "secret123")
    def test_subscribers_with_valid_token(self):
        resp = self.client.get("/notification/subscribers",
                               headers={"Authorization": "Bearer secret123"})
        self.assertEqual(resp.status_code, 200)

    @patch("services.notification.routes.ADMIN_TOKEN", "secret123")
    def test_subscribers_with_wrong_token(self):
        resp = self.client.get("/notification/subscribers",
                               headers={"Authorization": "Bearer wrong"})
        self.assertEqual(resp.status_code, 403)

    def test_trigger_no_subscription_returns_404(self):
        resp = self.client.get("/notification/trigger-notification?user_id=u1&site_id=s1")
        self.assertEqual(resp.status_code, 404)

    @patch("services.notification.service.sms_provider")
    def test_trigger_success_returns_200(self, mock_sms):
        mock_sms.send.return_value = {"success": True, "channel": "sms", "detail": {}}
        self.client.post("/notification/subscribe",
                         json={"user_id": "u1", "phone": "+46701234567", "sites": ["s1"]})
        resp = self.client.get("/notification/trigger-notification?user_id=u1&site_id=s1&site_name=Test")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
