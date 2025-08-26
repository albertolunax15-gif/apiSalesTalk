# app/routers/nlp.py
from fastapi import APIRouter, Depends, HTTPException, Response, status
from ..core.deps import get_current_user, require_role

from ..models.interpreterequest import (
    InterpretRequest,
    InterpretResponse,
    TTSRequest,
)

from ..utils.nlp.intent_engine import interpret_text
from ..utils.nlp.tts import synth_to_bytes

router = APIRouter(prefix="/nlp", tags=["nlp"])

# ------------------------------------------------------------------------------
# Solo usuarios logueados (token válido) pueden interpretar texto
# ------------------------------------------------------------------------------

@router.post(
    "/interpret",
    response_model=InterpretResponse,
    responses={
        401: {"description": "No autorizado"},
        500: {"description": "Error interno al interpretar"},
    },
)
def interpret(
    req: InterpretRequest,
    current_user: dict = Depends(get_current_user),  # 🔒 requiere login
):
    try:
        result = interpret_text(req.text, candidate_products=req.candidate_products)

        command = None
        if result.intent == "crear_venta":
            command = {
                "action": "create_sale",
                "data": {
                    # Si tu API necesita product_id, resuélvelo por nombre en tu capa de servicio
                    "product_name": result.entities.get("product_name"),
                    "quantity": result.entities.get("quantity"),
                    "payment_method": result.entities.get("payment_method", "Efectivo"),
                    "price": result.entities.get("price"),  # si es None, que la capa servicio tome el precio del catálogo
                    "date": result.entities.get("date"),
                },
                "needs_disambiguation": (result.entities.get("product_name") is None),
            }

        return InterpretResponse(
            intent=result.intent,
            confidence=round(result.confidence, 3),
            entities=result.entities,
            notes=result.notes,
            command=command,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Interpret error: {e}",
        )

# ------------------------------------------------------------------------------
# Solo usuarios logueados (token válido) pueden usar TTS
# Si quisieras restringir TTS a un rol (p.ej. 'superadmin'), cambia el Depends
# por: current_user = Depends(require_role("superadmin"))
# ------------------------------------------------------------------------------

@router.post(
    "/tts",
    responses={
        200: {"content": {"audio/mpeg": {}}},
        401: {"description": "No autorizado"},
        500: {"description": "Error interno de TTS"},
    },
)
async def tts(
    req: TTSRequest,
    current_user: dict = Depends(get_current_user),  # 🔒 requiere login
):
    try:
        audio = await synth_to_bytes(
            req.text, voice=req.voice, rate=req.rate, volume=req.volume
        )
        return Response(content=audio, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS error: {e}",
        )
