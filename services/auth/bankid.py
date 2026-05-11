import ssl

import httpx
from fastapi import HTTPException

from core.config import settings


def create_ssl_context() -> ssl.SSLContext:
    """
    Creates an SSL context with:
    - trusted BankID test CA
    - client certificate (your .pem file)
    """
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

    return response.json()


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
