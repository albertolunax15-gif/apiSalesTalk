# app/routers/transcribe.py
import os
import json
import tempfile
import subprocess
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["stt"])

# =========================
#   Configuración general
# =========================
STT_ENGINE = os.getenv("STT_ENGINE", "faster").strip().lower()   # "faster" | "vosk"
LANG_DEFAULT = os.getenv("STT_LANG", "es").strip()

# -------------------------
#   faster-whisper (batch)
# -------------------------
_fw_model = None
FW_MODEL_SIZE = os.getenv("FW_MODEL", "base").strip()  # tiny/base/small/medium/large-v3

def _fw_load():
    global _fw_model
    if _fw_model is None:
        try:
            from faster_whisper import WhisperModel
        except Exception as e:
            raise RuntimeError(
                "No se pudo importar faster-whisper. "
                "Instala con: pip install faster-whisper"
            ) from e
        # device="auto" elige GPU si está disponible
        _fw_model = WhisperModel(FW_MODEL_SIZE, device="auto", compute_type="auto")
    return _fw_model

def _fw_transcribe(path: str, language: Optional[str]):
    model = _fw_load()
    segs, info = model.transcribe(
        path,
        language=language or None,
        vad_filter=True
    )
    text = "".join(s.text for s in segs).strip()
    return {
        "engine": "faster-whisper",
        "text": text,
        "language": info.language,
        "duration": info.duration,
    }

# -------------
#   Vosk (batch)
# -------------
_vosk_model = None

BASE_DIR = Path(__file__).resolve().parent.parent  # = app/
DEFAULT_VOSK_MODEL = BASE_DIR / "models" / "vosk-model-small-es-0.42"
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", str(DEFAULT_VOSK_MODEL)).strip()

VOSK_SAMPLE_RATE = int(os.getenv("VOSK_SAMPLE_RATE", "16000"))

def _vosk_load():
    global _vosk_model
    if _vosk_model is None:
        try:
            from vosk import Model
        except Exception as e:
            raise RuntimeError(
                "No se pudo importar vosk. "
                "Instala con: pip install vosk"
            ) from e
        if not os.path.isdir(VOSK_MODEL_PATH):
            raise RuntimeError(
                f"No se encontró el modelo Vosk en '{VOSK_MODEL_PATH}'. "
                "Descárgalo de https://alphacephei.com/vosk/models y descomprímelo."
            )
        _vosk_model = Model(VOSK_MODEL_PATH)
    return _vosk_model

def _ensure_wav_16k_mono(input_bytes: bytes, in_name: str) -> str:
    """
    Asegura un WAV PCM s16le mono a 16k usando ffmpeg.
    Requiere que ffmpeg esté instalado en el servidor/imagen Docker.
    Devuelve la ruta al wav temporal.
    """
    # Guardamos input a archivo temporal
    suffix = os.path.splitext(in_name or "audio.bin")[1] or ".bin"
    tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_in.write(input_bytes)
    tmp_in.flush()
    tmp_in.close()

    tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp_out.close()

    # ffmpeg: cualquier formato -> wav PCM 16k mono
    # -y: overwrite, -vn: no video, -ar 16000: resample, -ac 1: mono, -f wav
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", tmp_in.name, "-vn",
        "-ar", str(VOSK_SAMPLE_RATE), "-ac", "1",
        "-f", "wav", tmp_out.name
    ]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        # Limpieza y error claro
        try: os.unlink(tmp_in.name)
        except: pass
        try: os.unlink(tmp_out.name)
        except: pass
        raise HTTPException(status_code=415, detail=f"ffmpeg no pudo convertir el audio: {e}")

    # Borramos el input, devolvemos el WAV convertido
    try: os.unlink(tmp_in.name)
    except: pass
    return tmp_out.name

def _vosk_transcribe_bytes(input_bytes: bytes, filename: str):
    from vosk import KaldiRecognizer
    wav_path = _ensure_wav_16k_mono(input_bytes, filename)
    try:
        rec = KaldiRecognizer(_vosk_load(), VOSK_SAMPLE_RATE)
        rec.SetWords(True)

        # Leemos el wav en chunks para simular streaming (batch)
        with open(wav_path, "rb") as f:
            # Saltar cabecera WAV (44 bytes típicamente) – Vosk lo acepta igual,
            # pero leeremos todo.
            while True:
                data = f.read(4000)
                if not data:
                    break
                if rec.AcceptWaveform(data):
                    pass  # vamos acumulando internamente

        # Final
        final = json.loads(rec.FinalResult() or "{}")
        text = (final.get("text") or "").strip()
        return {
            "engine": "vosk",
            "text": text,
            "language": "es",  # Vosk model específico; si usas multi-lang, ajústalo
        }
    finally:
        try: os.unlink(wav_path)
        except: pass

# =========================
#   ENDPOINTS PÚBLICOS
# =========================

@router.get("/transcribe/health")
def transcribe_health():
    """
    Devuelve info del engine activo y si carga el modelo.
    """
    info = {"engine": STT_ENGINE}
    try:
        if STT_ENGINE == "vosk":
            _ = _vosk_load()
            info["vosk_model"] = VOSK_MODEL_PATH
            info["sample_rate"] = VOSK_SAMPLE_RATE
        else:
            _ = _fw_load()
            info["fw_model_size"] = FW_MODEL_SIZE
    except Exception as e:
        info["error"] = str(e)
    return info

@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = Form(LANG_DEFAULT)):
    """
    Transcribe un archivo (webm/wav/mp3/m4a, etc):
      - Por defecto usa faster-whisper (FW_MODEL), con VAD.
      - Si STT_ENGINE=vosk -> usa Vosk (requiere ffmpeg para convertir a wav 16k mono).
    Nota: Este endpoint es útil para pruebas o batch; para *tiempo real* usa tu WS.
    """
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Archivo vacío.")

        if STT_ENGINE == "vosk":
            # Vosk necesita WAV 16k mono -> convertimos con ffmpeg
            result = _vosk_transcribe_bytes(content, file.filename or "audio.bin")
        else:
            # faster-whisper acepta varios formatos (ffmpeg interno vía decode)
            # pero por simplicidad guardamos a un archivo temporal
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename or "audio.bin")[1])
            tmp.write(content); tmp.flush(); tmp.close()

            try:
                result = _fw_transcribe(tmp.name, language)
            finally:
                try: os.unlink(tmp.name)
                except: pass

        return JSONResponse(result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})
