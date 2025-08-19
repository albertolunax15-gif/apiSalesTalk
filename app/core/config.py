import os, json, base64
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True), override=True)

class Settings(BaseModel):
    FIREBASE_DB_URL: str = os.getenv("FIREBASE_DB_URL", "")
    FIREBASE_CREDENTIALS_JSON_BASE64: str | None = os.getenv("FIREBASE_CREDENTIALS_JSON_BASE64")

    def _b64_to_str(self, s: str) -> str:
        s = (s or "").strip().strip('"').strip("'")
        s = "".join(c for c in s if c not in " \n\r\t")
        s = s.replace("-", "+").replace("_", "/")
        pad = (-len(s)) % 4
        if pad: s += "=" * pad
        return base64.b64decode(s).decode("utf-8")

    def cred_dict(self) -> dict:
        if not self.FIREBASE_DB_URL:
            raise RuntimeError("FIREBASE_DB_URL vacío")
        if not self.FIREBASE_CREDENTIALS_JSON_BASE64:
            raise RuntimeError("FIREBASE_CREDENTIALS_JSON_BASE64 vacío")

        raw = self._b64_to_str(self.FIREBASE_CREDENTIALS_JSON_BASE64)
        data = json.loads(raw)

        # normaliza la private_key
        if "private_key" in data:
            pk = data["private_key"]
            pk = pk.strip().strip('"').strip("'")
            pk = pk.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
            if not pk.endswith("\n"): pk += "\n"
            data["private_key"] = pk

        for k in ("type", "project_id", "client_email", "private_key"):
            if not data.get(k): raise RuntimeError(f"Falta {k}")
        return data

settings = Settings()