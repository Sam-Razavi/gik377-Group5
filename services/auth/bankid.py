import hashlib
import hmac as _hmac
import ssl
import time

import httpx
from fastapi import HTTPException

from core.config import settings

# In-memory store: orderRef → {qrStartToken, qrStartSecret, started_at}
_qr_sessions: dict[str, dict] = {}


def _store_qr_session(order_ref: str, qr_start_token: str, qr_start_secret: str) -> None:
    _qr_sessions[order_ref] = {
        "qrStartToken": qr_start_token,
        "qrStartSecret": qr_start_secret,
        "started_at": time.monotonic(),
    }


def get_qr_data(order_ref: str) -> str | None:
    session = _qr_sessions.get(order_ref)
    if not session:
        return None
    seconds = int(time.monotonic() - session["started_at"])
    auth_code = _hmac.new(
        key=session["qrStartSecret"].encode("utf-8"),
        msg=str(seconds).encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"bankid.{session['qrStartToken']}.{seconds}.{auth_code}"


def cleanup_qr_session(order_ref: str) -> None:
    _qr_sessions.pop(order_ref, None)


def create_ssl_context() -> ssl.SSLContext:
    import os

    if not settings.bankid_cert_file or not os.path.exists(settings.bankid_cert_file):
        raise RuntimeError(
            "BankID är inte i mock-läge men BANKID_CERT_FILE saknas eller finns inte. "
            "Sätt BANKID_MOCK_MODE=true i .env för demo, eller ange giltiga certifikatfiler."
        )
    if not settings.bankid_ca_file or not os.path.exists(settings.bankid_ca_file):
        raise RuntimeError(
            "BankID CA-fil saknas: BANKID_CA_FILE pekar inte på en befintlig fil."
        )
    context = ssl.create_default_context(cafile=settings.bankid_ca_file)
    context.load_cert_chain(
        certfile=settings.bankid_cert_file,
        password=settings.bankid_cert_password,
    )
    return context


async def initiate_bankid_auth(personal_number: str | None = None) -> dict:
    if settings.bankid_mock_mode:
        return {
            "orderRef": "mock-order-ref-12345",
            "autoStartToken": "mock-autostart-token",
            "qrStartToken": "mock-qr-start-token",
            "qrStartSecret": "mock-qr-start-secret",
        }

    url = f"{settings.bankid_base_url}/rp/v6.0/auth"

    payload = {
        "endUserIp": settings.bankid_end_user_ip,
    }

    if personal_number:
        payload["personalNumber"] = personal_number

    ssl_context = create_ssl_context()

    try:
        async with httpx.AsyncClient(verify=ssl_context, timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="BankID request timed out")
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"BankID returned HTTP error: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"BankID connection error: {str(e)}",
        )
    except ssl.SSLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"BankID SSL error: {str(e)}",
        )

    data = response.json()
    _store_qr_session(data["orderRef"], data["qrStartToken"], data["qrStartSecret"])
    return data


async def collect_bankid_status(order_ref: str) -> dict:
    if settings.bankid_mock_mode:
        return {
            "status": "complete",
            "hintCode": None,
            "orderRef": order_ref,
            "completionData": {
                "user": {
                    "personalNumber": "190000000000",
                    "name": "Test Testsson",
                }
            },
        }

    url = f"{settings.bankid_base_url}/rp/v6.0/collect"

    payload = {
        "orderRef": order_ref,
    }

    ssl_context = create_ssl_context()

    try:
        async with httpx.AsyncClient(verify=ssl_context, timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="BankID request timed out")
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"BankID returned HTTP error: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"BankID connection error: {str(e)}",
        )
    except ssl.SSLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"BankID SSL error: {str(e)}",
        )

    return response.json()
