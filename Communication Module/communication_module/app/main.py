from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.speaking_endpoint import router as speaking_router
from app.api.v1.endpoints.listening_endpoint import router as listening_router

app = FastAPI(title="Communication Assessment API")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(speaking_router,           prefix="/api/v1",           tags=["Speaking"])
app.include_router(listening_router,          prefix="/api/v1/listening", tags=["Listening"])