# app/routers/nlp.py
from fastapi import APIRouter, Depends, HTTPException, Response, status
from typing import Dict, Any, List, Optional

from ..core.deps import get_current_user  # o require_role si quieres rol específico

from ..models.interpreterequest import (
    InterpretRequest,
    InterpretResponse,
    ConfirmSaleRequest,
)
from ..models.sale import SaleCreate, SaleResponse

from ..utils.nlp.intent_engine import interpret_text
from ..utils.nlp.tts import synth_to_bytes
from ..services.sale_service import SaleService

router = APIRouter(prefix="/nlp", tags=["nlp"])

# -------------------------------------------------------------------
# Interpretar texto (requiere login)
# -------------------------------------------------------------------
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
    current_user: dict = Depends(get_current_user),
):
    try:
        result = interpret_text(req.text, candidate_products=req.candidate_products)

        entities: Dict[str, Any] = result.entities or {}
        notes: List[str] = list(result.notes or [])

        # Extraer lo que nuestra UI necesita
        payment_method: Optional[str] = entities.get("payment_method")
        product_id: Optional[str] = entities.get("product_id")
        quantity: Optional[int] = entities.get("quantity") or 1
        candidates: List[Dict[str, Any]] = entities.get("_candidates", [])

        # Construir "command" sugerido (no ejecuta nada)
        command = None
        if result.intent == "crear_venta":
            command = {
                "action": "create_sale",
                "data": {
                    "payment_method": payment_method or "Efectivo",
                    "product_id": product_id,  # puede ser None (ambiguo)
                    "quantity": quantity,
                },
            }

        # Regla de confirmación:
        needs_confirmation = (result.intent == "crear_venta") and (not product_id)

        return InterpretResponse(
            intent=result.intent,
            confidence=round(result.confidence or 0.0, 3),
            entities=entities,
            notes=notes,
            command=command,
            needs_confirmation=needs_confirmation,
            candidates=candidates if needs_confirmation else None,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Interpret error: {e}",
        )

# -------------------------------------------------------------------
# Confirmar y crear venta (requiere login)
# POST /nlp/confirm_sale
# Crea la venta con los datos ya confirmados desde la UI.
# -------------------------------------------------------------------
@router.post(
    "/confirm_sale",
    response_model=SaleResponse,  # tu modelo de dominio
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Venta creada"},
        400: {"description": "Datos inválidos"},
        401: {"description": "No autorizado"},
        404: {"description": "Producto no existe"},
        500: {"description": "Error interno"},
    },
)
def confirm_sale(
    req: ConfirmSaleRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        payload = SaleCreate(
            product_id=req.product_id,
            quantity=req.quantity,
            payment_method=req.payment_method,
            date=req.date,  # SaleService rellenará si viene None
        )
        sale = SaleService.create(payload)
        if not sale:
            raise HTTPException(status_code=500, detail="No se pudo crear la venta.")
        return sale
    except ValueError as ve:
        # p.ej. "Product does not exist"
        msg = str(ve)
        if "not exist" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al confirmar venta: {e}",
        )

# -------------------------------------------------------------------
# TTS 
# -------------------------------------------------------------------
@router.post(
    "/tts",
    responses={
        200: {"content": {"audio/mpeg": {}}},
        401: {"description": "No autorizado"},
        500: {"description": "Error interno de TTS"},
    },
)
async def tts(
    req: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
):
    try:
        text = str(req.get("text") or "")
        voice = req.get("voice")
        rate = req.get("rate")
        volume = req.get("volume")
        audio = await synth_to_bytes(text, voice=voice, rate=rate, volume=volume)
        return Response(content=audio, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS error: {e}",
        )