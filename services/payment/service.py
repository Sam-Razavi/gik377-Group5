"""Betaltjänst.

Ansvarig: Nina Bentmosse
Modul: Betaltjänst

Provider väljs via PAYMENT_PROVIDER i .env:
    stripe  — Stripe i testläge (standard)
    mock    — enkel in-memory mock

Publika metoder:
- PaymentService.create_subscription(user_id, plan_id, method="card") -> dict
- PaymentService.cancel_subscription(subscription_id, method="card") -> bool
- PaymentService.get_subscription(subscription_id, method="card") -> dict | None
"""

from typing import Dict, Optional
from .providers import build_provider, SwishProvider


class PaymentService:
    """Betaltjänst med utbytbara providers (Stripe, Swish, Mock).

    method="card"  → Stripe testläge (eller mock-fallback)
    method="swish" → Swish simulerad mock
    """

    def __init__(self):
        # Bygg kortprovider (Stripe eller mock) baserat på PAYMENT_PROVIDER i .env
        self._card_provider = build_provider()
        # Swish är alltid en simulerad mock – ingen riktig API-koppling
        self._swish_provider = SwishProvider()

    def create_subscription(self, user_id: str, plan_id: str, method: str = "card") -> Dict:
        # Skicka Swish-betalning till Swish-mock
        if method == "swish":
            return self._swish_provider.create_subscription(user_id, plan_id)
        # Annars skickas kortbetalning till Stripe (eller mock-fallback)
        return self._card_provider.create_subscription(user_id, plan_id)

    def cancel_subscription(self, subscription_id: str, method: str = "card") -> bool:
        # Avbryt Swish-prenumeration i mock-lagret
        if method == "swish":
            return self._swish_provider.cancel_subscription(subscription_id)
        # Annars avbryt kortprenumeration via Stripe (eller mock-fallback)
        return self._card_provider.cancel_subscription(subscription_id)

    def get_subscription(self, subscription_id: str, method: str = "card") -> Optional[Dict]:
        # Hämta Swish-prenumeration från mock-lagret
        if method == "swish":
            return self._swish_provider.get_subscription(subscription_id)
        # Annars hämta kortprenumeration från Stripe (eller mock-fallback)
        return self._card_provider.get_subscription(subscription_id)


__all__ = ["PaymentService"]
