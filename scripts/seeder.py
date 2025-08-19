import sys, os
import bcrypt
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.core.firebase import init_firebase, rtdb


def hash_password(password: str) -> str:
    """Genera un hash seguro para el password"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def run():
    init_firebase()

    uid = "fake-superadmin-uid"  # fijo para que sea predecible
    email = "admin@salestalk.com"

    profile = {
        "email": email,
        "display_name": "Super Admin",
        "role": "superadmin",
        "disabled": False,
        "password": hash_password("admin"),
        "created_at": datetime.utcnow().isoformat(),
    }

    rtdb().update({
        f"/users/{uid}": profile,
        f"/_indexes/email_to_uid/{email.replace('.', ',')}": uid,
    })
    print("Perfil superadmin insertado solo en RTDB.")


if __name__ == "__main__":
    run()