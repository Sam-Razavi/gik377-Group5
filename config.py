"""Konfiguration – Nordic Digital Solutions.

Alla värden läses från .env via python-dotenv.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Betalning ---
# Provider: stripe (standard), mock
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "stripe")

# Stripe testläge (börjar alltid med sk_test_)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")

# Swish (mock — inget riktigt API)
SWISH_NUMBER = os.getenv("SWISH_NUMBER", "0701234567")

# --- Översättning ---
# Provider: libretranslate (standard), google, mock
TRANSLATION_PROVIDER = os.getenv("TRANSLATION_PROVIDER", "libretranslate")

# LibreTranslate (gratis, self-hosted eller https://libretranslate.com)
LIBRETRANSLATE_URL = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.com")
LIBRETRANSLATE_API_KEY = os.getenv("LIBRETRANSLATE_API_KEY", "")

# Google Cloud Translate (valfritt alternativ)
TRANSLATE_API_KEY = os.getenv("TRANSLATE_API_KEY", "")
