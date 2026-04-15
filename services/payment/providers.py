"""Betalningsproviders.

Ansvarig: Nina Bentmosse
Modul: Betaltjänst – providers

Providers:
- StripeProvider  : Stripe i testläge (STRIPE_SECRET_KEY börjar med sk_test_)
- SwishProvider   : Swish mock/simulerad (ingen riktig koppling)

Välj provider via PAYMENT_PROVIDER i .env:
    PAYMENT_PROVIDER=stripe   (standard)
    PAYMENT_PROVIDER=mock
"""

import os
import uuid
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stripe
# ---------------------------------------------------------------------------

class StripeProvider:
    """Stripe i testläge.

    Kräver:
        pip install stripe
        STRIPE_SECRET_KEY=sk_test_... i .env

    Testkortnummer: 4242 4242 4242 4242 (valfritt utgångsdatum, valfri CVC)
    Se: https://stripe.com/docs/testing
    """

    def __init__(self):
        # Importera Stripe-biblioteket och sätt API-nyckeln från miljövariabel
        import stripe as _stripe
        self._stripe = _stripe
        self._stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

        # Säkerhetskontroll – produktionsnycklar får aldrig användas i testläge
        if not self._stripe.api_key.startswith("sk_test_"):
            raise ValueError(
                "STRIPE_SECRET_KEY måste börja med 'sk_test_' i testläge. "
                "Använd aldrig produktionsnycklar i kod/test."
            )
        logger.info("StripeProvider initierad i testläge.")

    def create_subscription(self, user_id: str, plan_id: str) -> Dict:
        """Skapa en Stripe-kund och prenumeration.

        plan_id ska matcha ett pris-ID i Stripe Dashboard (price_xxx).
        """
        # Skapa en Stripe-kund kopplad till användaren
        customer = self._stripe.Customer.create(
            metadata={"user_id": user_id}
        )

        # Skapa prenumerationen med ofullständig betalning (kräver kortuppgifter från klienten)
        subscription = self._stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": plan_id}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )

        # Returnera prenumerationsdata inkl. client_secret för kortbetalning i frontend
        return {
            "id": subscription.id,
            "user_id": user_id,
            "plan_id": plan_id,
            "status": subscription.status,
            "provider": "stripe",
            "client_secret": (
                subscription.latest_invoice.payment_intent.client_secret
                if subscription.latest_invoice and subscription.latest_invoice.payment_intent
                else None
            ),
        }

    def cancel_subscription(self, subscription_id: str) -> bool:
        # Avbryt prenumerationen i Stripe och returnera True om den är avbruten
        sub = self._stripe.Subscription.cancel(subscription_id)
        return sub.status == "canceled"

    def get_subscription(self, subscription_id: str) -> Optional[Dict]:
        # Hämta prenumerationens status från Stripe
        sub = self._stripe.Subscription.retrieve(subscription_id)
        return {
            "id": sub.id,
            "status": sub.status,
            "provider": "stripe",
        }


# ---------------------------------------------------------------------------
# Swish (mock / simulerad)
# ---------------------------------------------------------------------------

class SwishProvider:
    """Swish – simulerad implementation (ingen riktig API-koppling).

    Swish kräver BankID-certifikat och avtal med Getswish AB.
    Denna mock simulerar flödet för utveckling och demo.

    Statuskoder som simuleras:
        PAID      — betalningen gick igenom
        DECLINED  — betalningen nekades
    """

    # Swish-nummer som alltid simulerar ett misslyckat köp (för tester)
    _DECLINE_NUMBERS = {"0700000000"}

    def __init__(self):
        # In-memory lagring av simulerade prenumerationer
        self._store: Dict[str, Dict] = {}
        logger.info("SwishProvider initierad i mock-läge (simulerad).")

    def create_subscription(self, user_id: str, plan_id: str) -> Dict:
        """Simulera en Swish-betalningsbegäran."""
        # Generera ett unikt betalnings-ID
        payment_id = str(uuid.uuid4())
        swish_number = os.environ.get("SWISH_NUMBER", "0701234567")

        # Simulera godkänd eller nekad betalning baserat på Swish-nummer
        status = "DECLINED" if swish_number in self._DECLINE_NUMBERS else "PAID"

        record = {
            "id": payment_id,
            "user_id": user_id,
            "plan_id": plan_id,
            "status": "active" if status == "PAID" else "incomplete",
            "provider": "swish",
            "swish_status": status,
            "swish_number": swish_number,
        }
        # Spara prenumerationen i minnet
        self._store[payment_id] = record
        logger.info(
            "[mock] Swish-betalning %s för user %s: %s", payment_id, user_id, status
        )
        return record

    def cancel_subscription(self, subscription_id: str) -> bool:
        # Hämta prenumerationen och markera den som avbruten
        rec = self._store.get(subscription_id)
        if not rec:
            return False
        rec["status"] = "cancelled"
        rec["swish_status"] = "REFUNDED"
        logger.info("[mock] Swish-prenumeration %s avbruten.", subscription_id)
        return True

    def get_subscription(self, subscription_id: str) -> Optional[Dict]:
        # Returnera lagrad prenumeration eller None om den inte finns
        return self._store.get(subscription_id)


# ---------------------------------------------------------------------------
# Mock (enkel fallback)
# ---------------------------------------------------------------------------

class MockProvider:
    """Enkel in-memory mock för tester utan extern tjänst."""

    def __init__(self):
        # In-memory lagring av prenumerationer
        self._store: Dict[str, Dict] = {}
        logger.info("PaymentProvider: Mock (in-memory).")

    def create_subscription(self, user_id: str, plan_id: str) -> Dict:
        # Generera ett unikt ID och lagra prenumerationen i minnet
        sub_id = str(uuid.uuid4())
        record = {
            "id": sub_id,
            "user_id": user_id,
            "plan_id": plan_id,
            "status": "active",
            "provider": "mock",
        }
        self._store[sub_id] = record
        return record

    def cancel_subscription(self, subscription_id: str) -> bool:
        # Markera prenumerationen som avbruten om den finns
        rec = self._store.get(subscription_id)
        if not rec:
            return False
        rec["status"] = "cancelled"
        return True

    def get_subscription(self, subscription_id: str) -> Optional[Dict]:
        # Returnera lagrad prenumeration eller None om den inte finns
        return self._store.get(subscription_id)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_provider():
    """Bygg kortprovider baserat på PAYMENT_PROVIDER env-variabel (stripe eller mock).

    Swish hanteras separat direkt i PaymentService – inte här.
    """
    name = os.environ.get("PAYMENT_PROVIDER", "stripe").lower()

    if name == "stripe":
        try:
            # Försök initialisera Stripe med API-nyckeln från .env
            return StripeProvider()
        except Exception as e:
            # Om Stripe misslyckas (t.ex. nyckel saknas) används mock som fallback
            logger.warning("Stripe kunde inte initieras, faller tillbaka till mock: %s", e)

    logger.info("Använder mock-betalningsprovider.")
    return MockProvider()


__all__ = ["StripeProvider", "SwishProvider", "MockProvider", "build_provider"]
