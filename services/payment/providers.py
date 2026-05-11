"""Betalningsproviders.

Ansvarig: Nina Bentmosse
Modul: Betaltjänst – providers

Providers:
- StripeProvider   : Stripe i testläge, stöder Visa och Mastercard
- InvoiceProvider  : Simulerad fakturalösning (faktura, ingen extern API)

Kräver i .env:
    STRIPE_SECRET_KEY=sk_test_...
    STRIPE_PUBLISHABLE_KEY=pk_test_...
    PAYMENT_PROVIDER=stripe
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

        # Lås API-versionen till en stabil version som stöder payment_intent på Invoice
        self._stripe.api_version = "2024-11-20.acacia"

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
            "client_secret": (
                subscription.latest_invoice.payment_intent.client_secret
                if subscription.latest_invoice and subscription.latest_invoice.payment_intent
                else None
            ),
        }

    def create_checkout_session(self, price_id: str, success_url: str, cancel_url: str) -> Dict:
        session = self._stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return {"id": session.id, "url": session.url, "provider": "stripe"}

    def create_payment_intent(self, price_id: str, email: str = "") -> Dict:
        customer = self._stripe.Customer.create(email=email or None)
        subscription = self._stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": price_id}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )
        pi = subscription.latest_invoice.payment_intent
        if not pi:
            raise ValueError("Stripe returnerade inget payment_intent — kontrollera att price_id är korrekt.")
        return {
            "client_secret":   pi.client_secret,
            "subscription_id": subscription.id,
            "provider":        "stripe",
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
# Factory
# ---------------------------------------------------------------------------

def build_provider():
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if key:
        try:
            return StripeProvider()
        except (ValueError, ImportError) as e:
            logger.warning(
                "StripeProvider kunde inte initieras: %s. "
                "Faller tillbaka till InvoiceProvider.",
                e,
            )
    logger.info(
        "Payment provider: InvoiceProvider (mock - satt STRIPE_SECRET_KEY for Stripe)"
    )
    return InvoiceProvider()


__all__ = ["StripeProvider", "InvoiceProvider", "build_provider"]
