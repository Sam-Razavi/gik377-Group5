"""Tester för PaymentService — kör med: python -m pytest services/payment/"""

import pytest
from unittest.mock import MagicMock, patch
from payment.service import PaymentService
from payment.providers import InvoiceProvider


# ---------------------------------------------------------------------------
# Fixture — ersätter StripeProvider med en mock så inga riktiga API-anrop görs
# ---------------------------------------------------------------------------

@pytest.fixture
def stripe_mock():
    mock = MagicMock()
    mock.create_subscription.return_value = {
        "id": "sub_test_123",
        "user_id": "user_1",
        "plan_id": "price_test",
        "status": "active",
        "provider": "stripe",
        "client_secret": "pi_test_secret",
    }
    mock.create_payment_intent.return_value = {
        "client_secret": "pi_test_secret",
        "subscription_id": "sub_test_123",
        "provider": "stripe",
    }
    mock.create_checkout_session.return_value = {
        "id": "cs_test_123",
        "url": "https://checkout.stripe.com/test",
        "provider": "stripe",
    }
    mock.cancel_subscription.return_value = True
    mock.get_subscription.return_value = {
        "id": "sub_test_123",
        "status": "active",
        "provider": "stripe",
    }
    return mock


@pytest.fixture
def service(stripe_mock):
    with patch("payment.service.build_provider", return_value=stripe_mock):
        yield PaymentService()


# ---------------------------------------------------------------------------
# create_payment_intent
# ---------------------------------------------------------------------------

def test_create_payment_intent_returnerar_client_secret(service):
    result = service.create_payment_intent("price_test", "test@epost.se")
    assert "client_secret" in result
    assert result["client_secret"] == "pi_test_secret"


def test_create_payment_intent_har_subscription_id(service):
    result = service.create_payment_intent("price_test", "test@epost.se")
    assert "subscription_id" in result


# ---------------------------------------------------------------------------
# create_checkout_session
# ---------------------------------------------------------------------------

def test_create_checkout_session_returnerar_url(service):
    result = service.create_checkout_session(
        "price_test",
        "http://localhost/lyckades",
        "http://localhost/avbruten"
    )
    assert "url" in result
    assert result["url"].startswith("https://")


# ---------------------------------------------------------------------------
# create_subscription — card (Stripe mock)
# ---------------------------------------------------------------------------

def test_create_card_subscription(service):
    record = service.create_subscription("user_1", "price_test", method="card")
    assert record["status"] == "active"
    assert "id" in record


def test_create_card_subscription_fel_metod(service):
    with pytest.raises(ValueError, match="stöds inte"):
        service.create_subscription("user_1", "price_test", method="swish")


# ---------------------------------------------------------------------------
# create_subscription — invoice (InvoiceProvider, ingen mock behövs)
# ---------------------------------------------------------------------------

def test_create_invoice_subscription(service):
    record = service.create_subscription("user_2", "plan_basic", method="invoice")
    assert record["provider"] == "invoice"
    assert record["invoice_status"] == "pending"
    assert record["status"] == "active"
    assert "id" in record


def test_cancel_invoice_subscription(service):
    record = service.create_subscription("user_2", "plan_basic", method="invoice")
    result = service.cancel_subscription(record["id"], method="invoice")
    assert result is True


def test_cancel_invoice_som_inte_finns(service):
    result = service.cancel_subscription("finns-inte", method="invoice")
    assert result is False


def test_get_invoice_efter_avbryt(service):
    record = service.create_subscription("user_3", "plan_basic", method="invoice")
    service.cancel_subscription(record["id"], method="invoice")
    fetched = service.get_subscription(record["id"], method="invoice")
    assert fetched["status"] == "cancelled"
    assert fetched["invoice_status"] == "cancelled"


def test_get_invoice_som_inte_finns(service):
    result = service.get_subscription("finns-inte", method="invoice")
    assert result is None


# ---------------------------------------------------------------------------
# Felhantering — ogiltiga metoder
# ---------------------------------------------------------------------------

def test_ogiltig_metod_create_kastar_fel(service):
    with pytest.raises(ValueError, match="stöds inte"):
        service.create_subscription("user_1", "plan_basic", method="paypal")


def test_ogiltig_metod_cancel_kastar_fel(service):
    with pytest.raises(ValueError, match="stöds inte"):
        service.cancel_subscription("sub_1", method="bitcoin")


def test_ogiltig_metod_get_kastar_fel(service):
    with pytest.raises(ValueError, match="stöds inte"):
        service.get_subscription("sub_1", method="klarna")
