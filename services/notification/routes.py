"""
FastAPI-router med alla endpoints för Notification Service.
Gemensamt API-format så att andra grupper kan använda modulen direkt.
"""

import logging
from typing import List, Optional, Literal

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from services.notification.config import ADMIN_TOKEN
from services.notification.service import (
    send_notification,
    subscribe,
    unsubscribe,
    get_subscribers,
    trigger_for_location,
    VALID_TYPES,
)

logger = logging.getLogger("notification")

router = APIRouter(prefix="/notification", tags=["notification"])


# ---------- Pydantic-modeller (gemensamt API-kontrakt) ----------

class SendNotificationRequest(BaseModel):
    type: Literal["sms", "email"] = Field(..., description="sms eller email")
    to: str = Field(..., description="Telefonnummer (+46...) eller e-postadress")
    message: str = Field(..., description="Meddelandetexten")
    subject: Optional[str] = Field(None, description="Ämnesrad (endast e-post)")
    user_id: Optional[str] = Field(None, description="För anti-spam/cooldown")
    site_id: Optional[str] = Field(None, description="För anti-spam/cooldown")


class SubscribeRequest(BaseModel):
    user_id: str
    phone: Optional[str] = None
    email: Optional[str] = None
    sites: Optional[List[str]] = None


class UnsubscribeRequest(BaseModel):
    user_id: str
    sites: Optional[List[str]] = None


# ---------- Gemensamt API ----------

@router.post("/send-notification")
def send(body: SendNotificationRequest):
    """
    POST /notification/send-notification
    Body:
    {
        "type": "sms" | "email",
        "to": "+4670..." | "user@example.com",
        "message": "...",
        "subject": "...",          (valfritt, för e-post)
        "user_id": "...",          (valfritt, för anti-spam)
        "site_id": "..."           (valfritt, för anti-spam)
    }
    """
    if body.type not in VALID_TYPES:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Ogiltig typ. Använd 'sms' eller 'email'."},
        )

    result = send_notification(
        notification_type=body.type,
        to=body.to,
        message=body.message,
        subject=body.subject,
        user_id=body.user_id,
        site_id=body.site_id,
    )

    if result.get("success"):
        status = 200
    elif result.get("error") == "cooldown":
        status = 429
    elif result.get("error") in ("invalid_type", "invalid_recipient"):
        status = 400
    else:
        status = 500

    return JSONResponse(status_code=status, content=result)


# ---------- Trigger via URL ----------

@router.get("/trigger-notification")
def trigger(
    user_id: str = Query(..., description="Vem som ska få notifieringen"),
    site_id: str = Query(..., description="Vilket världsarv"),
    site_name: str = Query("Okänt världsarv", description="Namn på världsarvet"),
    link: Optional[str] = Query(None, description="Länk till mer info"),
):
    """
    GET /notification/trigger-notification?user_id=...&site_id=...&site_name=...&link=...
    """
    results = trigger_for_location(user_id, site_id, site_name, link)

    if results and all(r.get("error") == "cooldown" for r in results):
        status = 429
    elif results and results[0].get("error") in (
        "Användaren har ingen prenumeration.",
        "Användaren prenumererar inte på denna plats.",
        "Ingen kontaktinfo registrerad.",
    ):
        status = 404
    else:
        status = 200

    return JSONResponse(status_code=status, content={"results": results})


# ---------- Prenumeration ----------

@router.post("/subscribe")
def subscribe_route(body: SubscribeRequest):
    """
    POST /notification/subscribe
    Body:
    {
        "user_id": "abc123",
        "phone": "+46701234567",
        "email": "user@example.com",
        "sites": ["site_1", "site_2"]
    }
    """
    result = subscribe(
        user_id=body.user_id,
        phone=body.phone,
        email=body.email,
        sites=body.sites,
    )
    status = 200 if result.get("success") else 400
    return JSONResponse(status_code=status, content=result)


@router.post("/unsubscribe")
def unsubscribe_route(body: UnsubscribeRequest):
    """
    POST /notification/unsubscribe
    Body: { "user_id": "abc123", "sites": ["site_1"] }
    """
    result = unsubscribe(body.user_id, body.sites)
    status = 200 if result.get("success") else 404
    return JSONResponse(status_code=status, content=result)


# ---------- Intern/skyddad endpoint ----------

@router.get("/subscribers")
def list_subscribers(authorization: Optional[str] = Header(None)):
    """Intern endpoint. Kräver Authorization-header med admin-token."""
    token = (authorization or "").replace("Bearer ", "")
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "Otillåten. Ange giltig admin-token."},
        )

    logger.info("Endpoint /subscribers anropad (autentiserad)")
    return JSONResponse(status_code=200, content=get_subscribers())


# ---------- Healthcheck ----------

@router.get("/health")
def health():
    return {"status": "ok", "service": "notification"}
