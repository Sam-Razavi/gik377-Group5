"""Betaltjänst.

Ansvarig: Nina Bentmosse
Modul: services/payment/service.py

Stöder två betalmetoder:
    method="card"     — Stripe i testläge (Visa & Mastercard), standard
    method="invoice"  — Simulerad fakturalösning (mock, ingen extern API)

Konfig via .env:
    PAYMENT_PROVIDER=stripe
    STRIPE_SECRET_KEY=sk_test_...

Publika metoder:
    PaymentService.create_subscription(user_id, plan_id, method="card") -> dict
    PaymentService.cancel_subscription(subscription_id, method="card")  -> bool
    PaymentService.get_subscription(subscription_id, method="card")     -> dict | None
"""

from __future__ import annotations
import logging
from typing import Optional
from .providers import build_provider, InvoiceProvider

logger = logging.getLogger(__name__)

# Definierar vilka betalmetoder som är tillåtna
# "card" = Stripe kortbetalning (Visa/Mastercard)
# "invoice" = Simulerad fakturalösning
SUPPORTED_METHODS = {"card", "invoice"}


class PaymentService:
    """Betaltjänst med Stripe (card) och faktura (invoice) som parallella providers.

    Välj betalmetod per anrop via method-parametern:
        method="card"    — Stripe i testläge (standard)
        method="invoice" — Simulerad faktura
    """

    def __init__(self) -> None:
        # Bygger kortprovidern — Stripe om konfigurerad, annars MockProvider
        self._card_provider = build_provider()

        # Fakturaprovidern är alltid tillgänglig (simulerad, kräver ingen config)
        self._invoice_provider = InvoiceProvider()

        # Loggar vilka providers som är aktiva vid uppstart
        logger.info(
            "PaymentService initierad – kort: %s, faktura: %s",
            type(self._card_provider).__name__,
            type(self._invoice_provider).__name__,
        )

    # ------------------------------------------------------------------
    # Publikt API
    # ------------------------------------------------------------------

    def create_checkout_session(
        self, price_id: str, success_url: str, cancel_url: str
    ) -> dict:
        """Skapa en Stripe Checkout Session och returnera betalningslänken."""
        return self._card_provider.create_checkout_session(price_id, success_url, cancel_url)

    def create_payment_intent(self, price_id: str, email: str = "") -> dict:
        """Skapa PaymentIntent för inbäddat kortformulär. Returnerar client_secret."""
        return self._card_provider.create_payment_intent(price_id, email)

    def create_subscription(
        self, user_id: str, plan_id: str, method: str = "card"
    ) -> dict:
        """Skapa en ny prenumeration.

        Args:
            user_id: Användarens unika ID.
            plan_id: Prenumerationsplanens ID (t.ex. "plan_basic").
            method:  Betalmetod – "card" (Stripe) eller "invoice".

        Returns:
            Dict med prenumerationsdata inkl. "id" och "status".

        Raises:
            ValueError: Om method inte är "card" eller "invoice".
        """
        # Kontrollerar att method är "card" eller "invoice" — kastar ValueError annars
        self._validate_method(method)

        # Hämtar rätt provider baserat på method
        provider = self._get_provider(method)

        # Skapar prenumerationen via vald provider
        record = provider.create_subscription(user_id, plan_id)

        # Loggar att en prenumeration skapades
        logger.info(
            "Prenumeration skapad: id=%s, user=%s, plan=%s, method=%s",
            record.get("id"), user_id, plan_id, method,
        )
        return record

    def cancel_subscription(
        self, subscription_id: str, method: str = "card"
    ) -> bool:
        """Avbryt en befintlig prenumeration.

        Args:
            subscription_id: Prenumerationens ID.
            method:          Betalmetod – "card" eller "invoice".

        Returns:
            True om avbruten, False om prenumerationen inte hittades.

        Raises:
            ValueError: Om method inte är "card" eller "invoice".
        """
        # Kontrollerar att method är giltig innan vi försöker avbryta
        self._validate_method(method)

        # Hämtar rätt provider och avbryter prenumerationen
        ok = self._get_provider(method).cancel_subscription(subscription_id)

        # Loggar resultatet
        logger.info(
            "Avbokningsförsök: id=%s, method=%s, resultat=%s",
            subscription_id, method, ok,
        )
        return ok

    def get_subscription(
        self, subscription_id: str, method: str = "card"
    ) -> Optional[dict]:
        """Hämta en prenumeration.

        Args:
            subscription_id: Prenumerationens ID.
            method:          Betalmetod – "card" eller "invoice".

        Returns:
            Dict med prenumerationsdata, eller None om den inte hittas.

        Raises:
            ValueError: Om method inte är "card" eller "invoice".
        """
        # Kontrollerar att method är giltig
        self._validate_method(method)

        # Returnerar prenumerationen från rätt provider
        return self._get_provider(method).get_subscription(subscription_id)

    # ------------------------------------------------------------------
    # Privata hjälpmetoder
    # ------------------------------------------------------------------

    def _validate_method(self, method: str) -> None:
        """Kasta ValueError om betalmetoden inte stöds."""
        # Om method inte finns i SUPPORTED_METHODS kastas ett tydligt felmeddelande
        if method not in SUPPORTED_METHODS:
            raise ValueError(
                f"Betalmetoden '{method}' stöds inte. "
                f"Välj ett av: {', '.join(sorted(SUPPORTED_METHODS))}"
            )

    def _get_provider(self, method: str):
        """Returnera rätt provider baserat på betalmetod."""
        # Faktura-betalningar hanteras av InvoiceProvider
        if method == "invoice":
            return self._invoice_provider

        # Kortbetalningar hanteras av Stripe (eller mock om Stripe ej konfigurerad)
        return self._card_provider


__all__ = ["PaymentService", "SUPPORTED_METHODS"]
