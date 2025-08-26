import asyncio
import edge_tts

# Voces: español latino ("es-PE", "es-MX", "es-ES", etc.)
DEFAULT_VOICE = "es-PE-CamilaNeural"

async def synth_to_file(text: str, out_path: str, voice: str = DEFAULT_VOICE, rate: str = "+0%", volume: str = "+0%"):
    tts = edge_tts.Communicate(text, voice=voice, rate=rate, volume=volume)
    await tts.save(out_path)

async def synth_to_bytes(text: str, voice: str = DEFAULT_VOICE, rate: str = "+0%", volume: str = "+0%") -> bytes:
    tts = edge_tts.Communicate(text, voice=voice, rate=rate, volume=volume)
    chunks: list[bytes] = []

    async for chunk in tts.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)