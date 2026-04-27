"""Tester för PaymentService — kör med: python -m pytest services/payment/"""

import pytest
from unittest.mock import patch
from services.payment.service import PaymentService
from services.payment.providers import MockProvider, InvoiceProvider


@pytest.fixture
def service():
    with patch("services.payment.service.build_provider", return_value=MockProvider()):
        yield PaymentService()


# ---------------------------------------------------------------------------
# Kortbetalning (MockProvider)
# ---------------------------------------------------------------------------

def test_create_card_subscription(service):
    record = service.create_subscription("user_1", "plan_basic", method="card")
    assert record["user_id"] == "user_1"
    assert record["plan_id"] == "plan_basic"
    assert record["status"] == "active"
    assert "id" in record


def test_cancel_card_subscription(service):
    record = service.create_subscription("user_1", "plan_basic", method="card")
    result = service.cancel_subscription(record["id"], method="card")
    assert result is True


def test_cancel_nonexistent_card_subscription(service):
    result = service.cancel_subscription("finns-inte", method="card")
    assert result is False


def test_get_card_subscription(service):
    record = service.create_subscription("user_2", "plan_pro", method="card")
    fetched = service.get_subscription(record["id"], method="card")
    assert fetched["id"] == record["id"]
    assert fetched["status"] == "active"


def test_get_nonexistent_card_subscription(service):
    result = service.get_subscription("finns-inte", method="card")
    assert result is None


# ---------------------------------------------------------------------------
# Fakturabetalning (InvoiceProvider)
# ---------------------------------------------------------------------------

def test_create_invoice_subscription(service):
    record = service.create_subscription("user_3", "plan_basic", method="invoice")
    assert record["provider"] == "invoice"
    assert record["invoice_status"] == "pending"
    assert record["status"] == "active"


def test_cancel_invoice_subscription(service):
    record = service.create_subscription("user_3", "plan_basic", method="invoice")
    result = service.cancel_subscription(record["id"], method="invoice")
    assert result is True


def test_cancel_nonexistent_invoice_subscription(service):
    result = service.cancel_subscription("finns-inte", method="invoice")
    assert result is False


def test_get_invoice_subscription_after_cancel(service):
    record = service.create_subscription("user_4", "plan_basic", method="invoice")
    service.cancel_subscription(record["id"], method="invoice")
    fetched = service.get_subscription(record["id"], method="invoice")
    assert fetched["status"] == "cancelled"
    assert fetched["invoice_status"] == "cancelled"


# ---------------------------------------------------------------------------
# Felhantering
# ---------------------------------------------------------------------------

def test_invalid_method_create_raises(service):
    with pytest.raises(ValueError, match="stöds inte"):
        service.create_subscription("user_1", "plan_basic", method="paypal")


def test_invalid_method_cancel_raises(service):
    with pytest.raises(ValueError, match="stöds inte"):
        service.cancel_subscription("sub_1", method="swish")


def test_invalid_method_get_raises(service):
    with pytest.raises(ValueError, match="stöds inte"):
        service.get_subscription("sub_1", method="bitcoin")
