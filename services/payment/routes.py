# Ansvarig: Nina Bentmosse
# Modul: Betaltjänst

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from services.payment.service import PaymentService

router = APIRouter(prefix="/payment", tags=["payment"])

payment_service = PaymentService()


class CreateSubscriptionRequest(BaseModel):
    user_id: str
    plan_id: str
    method: str = "card"


class CancelSubscriptionRequest(BaseModel):
    subscription_id: str
    method: str = "card"


@router.post("/create")
def payment_create(body: CreateSubscriptionRequest):
    """Skapa en prenumeration och returnera Stripe-checkout-URL."""
    try:
        record = payment_service.create_subscription(body.user_id, body.plan_id, method=body.method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Betalning kunde inte skapas: {str(e)}")

    return {"subscription_id": record["id"], "url": record.get("url"), "record": record}


@router.post("/cancel")
def payment_cancel(body: CancelSubscriptionRequest):
    """Avbryt en prenumeration."""
    try:
        ok = payment_service.cancel_subscription(body.subscription_id, method=body.method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"cancelled": ok}


@router.get("/subscription/{subscription_id}")
def payment_get(subscription_id: str, method: str = "card"):
    """Hämta status för en prenumeration."""
    try:
        rec = payment_service.get_subscription(subscription_id, method=method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not rec:
        raise HTTPException(status_code=404, detail="Prenumerationen hittades inte.")

    return rec


@router.get("/lyckades", response_class=HTMLResponse)
def payment_success():
    return """<!DOCTYPE html>
<html lang="sv"><head><meta charset="utf-8"><title>Betalning klar</title>
<style>
  body{font-family:'Segoe UI',sans-serif;background:#f0f4f8;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
  .box{background:#fff;border-radius:16px;padding:48px 40px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,0.08);max-width:400px}
  .icon{font-size:52px;margin-bottom:16px}
  h1{color:#276749;font-size:1.5rem;margin-bottom:8px}
  p{color:#718096;font-size:14px;margin-bottom:24px}
  a{display:inline-block;padding:12px 28px;background:#1d3571;color:#fff;border-radius:8px;text-decoration:none;font-weight:600}
</style></head><body>
<div class="box">
  <div class="icon">✅</div>
  <h1>Betalningen lyckades!</h1>
  <p>Ditt konto är nu uppdaterat.</p>
  <a href="http://localhost:8000">Tillbaka till tjänsten</a>
</div>
</body></html>"""


@router.get("/avbruten", response_class=HTMLResponse)
def payment_cancel_page():
    return """<!DOCTYPE html>
<html lang="sv"><head><meta charset="utf-8"><title>Betalning avbruten</title>
<style>
  body{font-family:'Segoe UI',sans-serif;background:#f0f4f8;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
  .box{background:#fff;border-radius:16px;padding:48px 40px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,0.08);max-width:400px}
  .icon{font-size:52px;margin-bottom:16px}
  h1{color:#744210;font-size:1.5rem;margin-bottom:8px}
  p{color:#718096;font-size:14px;margin-bottom:24px}
  a{display:inline-block;padding:12px 28px;background:#1d3571;color:#fff;border-radius:8px;text-decoration:none;font-weight:600}
</style></head><body>
<div class="box">
  <div class="icon">↩️</div>
  <h1>Betalningen avbröts.</h1>
  <p>Inga pengar har dragits.</p>
  <a href="http://localhost:8000">Försök igen</a>
</div>
</body></html>"""
