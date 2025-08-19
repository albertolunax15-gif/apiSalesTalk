import firebase_admin
from firebase_admin import credentials, db
from .config import settings

def init_firebase():
    if firebase_admin._apps:
        return
    cred = credentials.Certificate(settings.cred_dict())
    firebase_admin.initialize_app(cred, {"databaseURL": settings.FIREBASE_DB_URL})

def rtdb(path="/"):
    return db.reference(path)