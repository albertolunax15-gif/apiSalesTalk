from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.firebase import init_firebase
from app.routers import auth, users, products, sales, nlp

def create_app() -> FastAPI:
    app = FastAPI(
        title="SalesTalk API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup():
        init_firebase()
        try:
            print("=== ROUTES ===")
            for r in app.routes:
                print(getattr(r, "path", r))
        except Exception:
            pass

    # ✅ Acepta GET y HEAD en raíz
    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def root():
        return {"status": "ok", "service": "apisalestalk", "docs": "/docs"}

    # ✅ (Opcional) Acepta GET y HEAD en health
    @app.api_route("/healthz", methods=["GET", "HEAD"], include_in_schema=False)
    async def healthz():
        return {"ok": True}

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(products.router)
    app.include_router(sales.router)
    app.include_router(nlp.router)

    return app

app = create_app()