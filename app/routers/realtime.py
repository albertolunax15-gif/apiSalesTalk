# app/routers/realtime.py
import os
import json
import httpx
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse

# ==== Vosk (STT offline/servidor) ====
from vosk import Model, KaldiRecognizer

router = APIRouter(prefix="/api/realtime", tags=["realtime"])

# ==========================
#   CONFIG OPENAI (opcional)
# ==========================
REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-mini-realtime-preview-2024-12-17").strip()

def ensure_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno.")
    return api_key

@router.get("/health", include_in_schema=False)
async def health():
    return {"ok": True, "service": "realtime"}

# ✅ Preflight CORS para el endpoint /token
@router.options("/token", include_in_schema=False)
async def options_token():
    return PlainTextResponse("", status_code=204)

@router.post("/token")
async def create_client_secret(api_key: str = Depends(ensure_api_key)):
    """
    (Opcional) Intenta crear un client_secret efímero para OpenAI Realtime (si luego quieres volver).
    USO: POST https://api.openai.com/v1/realtime/client_secrets
    Header obligatorio: OpenAI-Beta: realtime=v1
    """
    url = "https://api.openai.com/v1/realtime/client_secrets"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1",
    }
    payload = {"model": REALTIME_MODEL}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload, headers=headers)

        if r.status_code >= 400:
            # Devolvemos el error del upstream tal cual para debug claro
            try:
                detail = r.json()
            except Exception:
                detail = {"raw": r.text}
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "OpenAI no entregó client_secret",
                    "upstream_status": r.status_code,
                    "upstream_body": detail,
                },
            )

        data = r.json()
        cs = data.get("client_secret", {})
        if not cs or not cs.get("value"):
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "Respuesta sin client_secret desde OpenAI",
                    "upstream_status": r.status_code,
                    "upstream_body": data,
                },
            )

        return JSONResponse({"client_secret": cs, "model": REALTIME_MODEL})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})

# =========================================
#   VOSK: WebSocket de STT en TIEMPO REAL
# =========================================

# Config Vosk
BASE_DIR = Path(__file__).resolve().parent.parent  # = app/
DEFAULT_VOSK_MODEL = BASE_DIR / "models" / "vosk-model-small-es-0.42"
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", str(DEFAULT_VOSK_MODEL)).strip()
VOSK_SAMPLE_RATE = int(os.getenv("VOSK_SAMPLE_RATE", "16000"))

# Carga perezosa del modelo (una sola vez)
_vosk_model: Optional[Model] = None

def _get_vosk_model() -> Model:
    global _vosk_model
    if _vosk_model is None:
        if not os.path.isdir(VOSK_MODEL_PATH):
            raise RuntimeError(
                f"No se encontró el modelo Vosk en '{VOSK_MODEL_PATH}'. "
                "Descárgalo y descomprímelo (por ejemplo: vosk-model-small-es-0.42) "
                "o define VOSK_MODEL_PATH con la ruta correcta."
            )
        _vosk_model = Model(VOSK_MODEL_PATH)
    return _vosk_model

@router.websocket("/ws")
async def ws_stt(websocket: WebSocket):
    """
    WebSocket de STT en tiempo real con Vosk.
    - Espera recibir audio PCM16 little-endian a 16 kHz (ArrayBuffer con Int16) en frames pequeños (20-40ms).
    - Responde JSON con:
        { "type": "partial", "text": "..." }  (hipótesis parcial)
        { "type": "final",   "text": "..." }  (segmento final)
        { "type": "error",   "error": "..." } (errores)
    """
    await websocket.accept()
    try:
        model = _get_vosk_model()
        rec = KaldiRecognizer(model, VOSK_SAMPLE_RATE)
        rec.SetWords(True)

        # Mensaje de bienvenida
        await websocket.send_json({"type": "ready", "sample_rate": VOSK_SAMPLE_RATE})

        while True:
            # Recibe bytes (ArrayBuffer del front). Deben ser PCM16 LE mono a 16kHz.
            message = await websocket.receive()
            if "bytes" in message:
                data: bytes = message["bytes"]
            else:
                # Para cierre o mensajes texto
                typ = message.get("type")
                if typ == "websocket.disconnect":
                    break
                # Ignora texto; puedes manejar controles si los envías
                continue

            # Alimenta al recognizer
            if rec.AcceptWaveform(data):
                # Resultado final de ese bloque
                res = json.loads(rec.Result())
                text = (res.get("text") or "").strip()
                await websocket.send_json({"type": "final", "text": text})
            else:
                # Parcial
                res = json.loads(rec.PartialResult())
                partial = (res.get("partial") or "").strip()
                if partial:
                    await websocket.send_json({"type": "partial", "text": partial})

    except WebSocketDisconnect:
        # Cierre normal del cliente
        try:
            # Último resultado final si queda algo
            final = json.loads(rec.FinalResult()) if 'rec' in locals() else {}
            if final.get("text"):
                await websocket.send_json({"type": "final", "text": final.get("text", "")})
        except Exception:
            pass
        finally:
            return
    except Exception as e:
        # Error inesperado
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass
        finally:
            await websocket.close()