"""Betalningsproviders.

Ansvarig: Nina Bentmosse
Modul: Betaltjänst – providers

Providers:
- StripeProvider   : Stripe i testläge, stöder Visa och Mastercard
- InvoiceProvider  : Simulerad fakturalösning (mock, ingen extern API)
- MockProvider     : Enkel in-memory fallback om Stripe saknas

Välj kortprovider via PAYMENT_PROVIDER i .env:
    PAYMENT_PROVIDER=stripe  (standard)
    PAYMENT_PROVIDER=mock
"""

import os
import uuid
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stripe — kortbetalning (Visa & Mastercard)
# ---------------------------------------------------------------------------

class StripeProvider:
    """Stripe i testläge — stöder Visa och Mastercard.

    Kräver:
        pip install stripe
        STRIPE_SECRET_KEY=sk_test_... i .env

    Testkort:
        Visa:       4242 4242 4242 4242
        Mastercard: 5555 5555 5555 4444
        (valfritt utgångsdatum och CVC)
    """

    def __init__(self):
        # Importerar Stripe-biblioteket och läser API-nyckeln från .env
        import stripe as _stripe
        self._stripe = _stripe

        # Använd .get() — kraschar inte med KeyError om .env saknas
        self._stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

        # Tydligt felmeddelande om nyckeln saknas helt
        if not self._stripe.api_key:
            raise ValueError(
                "STRIPE_SECRET_KEY saknas i .env. "
                "Lägg till STRIPE_SECRET_KEY=sk_test_... i din .env-fil."
            )

        # Säkerhetskontroll — produktionsnycklar får aldrig användas i testläge
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
        # Skapar en Stripe-kund kopplad till användaren
        customer = self._stripe.Customer.create(
            metadata={"user_id": user_id}
        )

        # Skapar prenumerationen och hämtar client_secret för frontend-betalning
        subscription = self._stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": plan_id}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )

        return {
            "id": subscription.id,
            "user_id": user_id,
            "plan_id": plan_id,
            "status": subscription.status,
            "provider": "stripe",
            # client_secret används av frontend för att visa kortformulär
            "client_secret": (
                subscription.latest_invoice.payment_intent.client_secret
                if subscription.latest_invoice and subscription.latest_invoice.payment_intent
                else None
            ),
        }

    def cancel_subscription(self, subscription_id: str) -> bool:
        # Avbryter prenumerationen direkt i Stripe
        sub = self._stripe.Subscription.cancel(subscription_id)
        return sub.status == "canceled"

    def get_subscription(self, subscription_id: str) -> Optional[Dict]:
        # Hämtar prenumerationens aktuella status från Stripe
        sub = self._stripe.Subscription.retrieve(subscription_id)
        return {
            "id": sub.id,
            "status": sub.status,
            "provider": "stripe",
        }


# ---------------------------------------------------------------------------
# InvoiceProvider — simulerad fakturalösning (mock)
# ---------------------------------------------------------------------------

class InvoiceProvider:
    """Simulerad fakturalösning — ingen extern API-koppling.

    Simulerar ett faktura-flöde för utveckling och demo.

    Två statusfält används parallellt — de beskriver olika saker:

        status — prenumerationens övergripande status:
            "active"    — prenumerationen är skapad och aktiv
            "cancelled" — prenumerationen är avbruten

        invoice_status — fakturans betalstatus:
            "pending"   — faktura skickad, väntar på betalning
            "paid"      — faktura betald
            "cancelled" — faktura avbruten

    Varför två fält?
        status beskriver prenumerationen som helhet — finns den eller inte.
        invoice_status beskriver själva fakturans betalstatus — har den betalats?
        En prenumeration kan vara "active" medan fakturan fortfarande är "pending".

    Flöde: skapande → pending, betalad → paid, avbruten → cancelled
    """

    def __init__(self):
        # In-memory lagring av fakturor (försvinner när servern stoppas)
        self._store: Dict[str, Dict] = {}
        logger.info("InvoiceProvider initierad i mock-läge (simulerad).")

    def create_subscription(self, user_id: str, plan_id: str) -> Dict:
        # Skapar en ny faktura med status "pending"
        invoice_id = str(uuid.uuid4())
        record = {
            "id": invoice_id,
            "user_id": user_id,
            "plan_id": plan_id,
            "status": "active",
            "provider": "invoice",
            "invoice_status": "pending",  # pending → paid → cancelled
        }
        self._store[invoice_id] = record
        logger.info("[mock] Faktura %s skapad för user %s — status: pending", invoice_id, user_id)
        return record

    def cancel_subscription(self, subscription_id: str) -> bool:
        # Sätter fakturans status till "cancelled" om den finns
        rec = self._store.get(subscription_id)
        if not rec:
            return False
        rec["status"] = "cancelled"
        rec["invoice_status"] = "cancelled"
        logger.info("[mock] Faktura %s avbruten.", subscription_id)
        return True

    def get_subscription(self, subscription_id: str) -> Optional[Dict]:
        # Returnerar fakturan eller None om den inte finns
        return self._store.get(subscription_id)


# ---------------------------------------------------------------------------
# MockProvider — enkel fallback om Stripe saknas
# ---------------------------------------------------------------------------

class MockProvider:
    """Enkel in-memory mock för tester utan extern tjänst."""

    def __init__(self):
        # In-memory lagring — ingen extern tjänst krävs
        self._store: Dict[str, Dict] = {}
        logger.info("PaymentProvider: Mock (in-memory).")

    def create_subscription(self, user_id: str, plan_id: str) -> Dict:
        # Skapar en prenumeration direkt i minnet
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
        # Sätter status till "cancelled" om prenumerationen finns
        rec = self._store.get(subscription_id)
        if not rec:
            return False
        rec["status"] = "cancelled"
        return True

    def get_subscription(self, subscription_id: str) -> Optional[Dict]:
        # Returnerar prenumerationen eller None
        return self._store.get(subscription_id)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_provider():
    """Bygg kortprovider baserat på PAYMENT_PROVIDER env-variabel.

    Returnerar StripeProvider om konfigurerad, annars MockProvider.
    InvoiceProvider skapas alltid separat i PaymentService.
    """
    name = os.environ.get("PAYMENT_PROVIDER", "stripe").lower()

    if name == "stripe":
        try:
            # Försöker starta Stripe — faller tillbaka till mock om nyckeln saknas
            return StripeProvider()
        except Exception as e:
            logger.warning("Stripe kunde inte initieras, faller tillbaka till mock: %s", e)

    logger.info("Använder mock-betalningsprovider.")
    return MockProvider()


__all__ = ["StripeProvider", "InvoiceProvider", "MockProvider", "build_provider"]
