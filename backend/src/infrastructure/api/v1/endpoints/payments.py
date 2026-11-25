import os
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from src.domain.entities.payment import PaymentUnavailable
from src.infrastructure.api.v1.dependencies import get_current_user
from src.infrastructure.payments.config import get_payments, payment_store
from src.infrastructure.payments.settings import get_payment_settings
from src.infrastructure.payments.stripe_gateway import receive_webhook, verify_webhook

router = APIRouter(prefix="/pagos", tags=["Pagos"])


class PaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: UUID


def public_payment(payment):
    if payment is None:
        return None
    messages = {
        "queued": "Solicitud guardada. Se procesara cuando Stripe este disponible.",
        "ready": "Continua en Stripe para realizar el pago.",
        "processing": "Stripe esta confirmando el pago.",
        "succeeded": "Pago exitoso. Tu pago fue confirmado por Stripe.",
        "failed": "El pago fallo. Puedes reintentar.",
        "expired": "El intento vencio. Puedes solicitar uno nuevo.",
        "review_required": "El intento requiere revision. No se iniciara otro cobro automaticamente.",
    }
    return {"id": payment.id, "order_id": payment.order_id, "status": payment.status,
            "amount_minor": payment.amount_minor, "currency": payment.currency,
            "checkout_url": payment.checkout_url if payment.status == "ready" else None,
            "error": payment.error if payment.status in ("review_required", "failed") else None,
            "message": messages[payment.status], "attempt": payment.attempt}


@router.post("", status_code=202)
async def request_payment(body: PaymentRequest, user=Depends(get_current_user),
                          idempotency_key: str = Header(min_length=8, max_length=200),
                          service=Depends(get_payments)):
    try:
        return public_payment(await service.request(str(user.id), str(body.order_id), idempotency_key))
    except PaymentUnavailable:
        raise HTTPException(503, "Stripe no esta disponible para conciliar el intento anterior. Reintenta mas tarde.")


@router.get("/pedido/{order_id}")
async def current_payment(order_id: UUID, user=Depends(get_current_user), service=Depends(get_payments)):
    return public_payment(service.current(str(user.id), str(order_id)))


@router.get("/configuracion")
async def payment_configuration(user=Depends(get_current_user), settings=Depends(get_payment_settings)):
    return settings.public()


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(default="")):
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(503, "Webhook no configurado")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 262144:
            raise HTTPException(413, "Evento demasiado grande")
    try:
        event = verify_webhook(bytes(raw), stripe_signature, secret)
        receive_webhook(payment_store(), event, livemode=False)
    except (ValueError, KeyError, TypeError):
        raise HTTPException(400, "Evento de Stripe invalido")
    # The durable inbox, payment transition and outbox are committed before ACK.
    return {"received": True}
