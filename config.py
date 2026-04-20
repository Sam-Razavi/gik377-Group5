import os
from dotenv import load_dotenv

load_dotenv()

# --- Payment ---
# Provider: stripe (standard), mock
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "stripe")

# Stripe testläge (börjar alltid med sk_test_)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")

# --- Translation ---
# Google Cloud Translate används alltid som primär provider.
# Mock används automatiskt som fallback om credentials saknas.
# TRANSLATION_PROVIDER används inte — Google provas alltid, ingen variabel styr det.
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
