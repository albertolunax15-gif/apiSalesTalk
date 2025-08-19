from typing import Optional, Dict, Any, List
from ..core.firebase import rtdb

USERS_PATH = "/users"
EMAIL_INDEX_PATH = "/_indexes/email_to_uid"

class UserRepo:
    @staticmethod
    def get_by_uid(uid: str) -> Optional[Dict[str, Any]]:
        return rtdb(f"{USERS_PATH}/{uid}").get()

    @staticmethod
    def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        uid = rtdb(f"{EMAIL_INDEX_PATH}/{email.replace('.', ',')}").get()
        if not uid:
            return None
        data = rtdb(f"{USERS_PATH}/{uid}").get()
        return data

    @staticmethod
    def upsert_profile(uid: str, profile: Dict[str, Any]) -> None:
        # upsert atómico + índice de email
        email_key = profile["email"].replace(".", ",")
        rtdb().update({
            f"{USERS_PATH}/{uid}": profile,
            f"{EMAIL_INDEX_PATH}/{email_key}": uid
        })

    @staticmethod
    def list(limit: int = 50) -> List[Dict[str, Any]]:
        data = rtdb(USERS_PATH).order_by_key().limit_to_first(limit).get()

        # Asegurar que sea un dict
        if not isinstance(data, dict):
            return []

        return [{"uid": k, **v} for k, v in data.items() if isinstance(v, dict)]

