from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.firebase import init_firebase
from app.routers import auth, users, products, sales


def create_app() -> FastAPI:
    app = FastAPI(title="SalesTalk API")

    # 🚀 Configuración de CORS (habilitar acceso desde cualquier dispositivo)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 👉 Permitir cualquier origen
        allow_credentials=True,
        allow_methods=["*"],  # 👉 Permitir todos los métodos (GET, POST, PUT, DELETE, etc.)
        allow_headers=["*"],  # 👉 Permitir cualquier header
    )

    @app.on_event("startup")
    def _startup():
        init_firebase()

    # Rutas
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(products.router)
    app.include_router(sales.router)

    return app


app = create_app()