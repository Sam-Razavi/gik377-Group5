import ssl
import httpx

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
    url = f"{settings.bankid_base_url}/rp/v6.0/auth"

    payload = {
        "endUserIp": settings.bankid_end_user_ip,
    }

    if personal_number:
        payload["personalNumber"] = personal_number

    ssl_context = create_ssl_context()

    async with httpx.AsyncClient(verify=ssl_context) as client:
        response = await client.post(url, json=payload)

    return response.json()


async def collect_bankid_status(order_ref: str) -> dict:
    url = f"{settings.bankid_base_url}/rp/v6.0/collect"

    payload = {
        "orderRef": order_ref,
    }

    ssl_context = create_ssl_context()

    async with httpx.AsyncClient(verify=ssl_context) as client:
        response = await client.post(url, json=payload)

    return response.json()