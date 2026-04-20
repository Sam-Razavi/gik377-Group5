# Ansvarig: Nina Bentmosse
# Modul: Betaltjänst

from fastapi import APIRouter, HTTPException
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
    """Skapa en prenumeration.

    Body (JSON):
        user_id : str — användarens ID
        plan_id : str — prenumerationsplanens ID
        method  : str — "card" (Stripe, standard) eller "invoice"
    """
    try:
        record = payment_service.create_subscription(body.user_id, body.plan_id, method=body.method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Betalning kunde inte skapas: {str(e)}")

    return {"subscription_id": record["id"], "record": record}


@router.post("/cancel")
def payment_cancel(body: CancelSubscriptionRequest):
    """Avbryt en prenumeration.

    Body (JSON):
        subscription_id : str
        method          : str — "card" (standard) eller "invoice"
    """
    try:
        ok = payment_service.cancel_subscription(body.subscription_id, method=body.method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"cancelled": ok}


@router.get("/subscription/{subscription_id}")
def payment_get(subscription_id: str, method: str = "card"):
    """Hämta status för en prenumeration.

    Path-param:
        subscription_id : str
    Query-param:
        method : "card" (standard) eller "invoice"
    """
    try:
        rec = payment_service.get_subscription(subscription_id, method=method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not rec:
        raise HTTPException(status_code=404, detail="Prenumerationen hittades inte.")

    return rec
