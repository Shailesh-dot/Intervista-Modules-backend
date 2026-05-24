import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from app.utils.limiter import limiter
from app.routes import admin, question, submission, code, health, assessment
from app.exceptions.handlers import register_handlers
from app.middleware.logging_middleware import LoggingMiddleware
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Coding Assessment API v6 started")
    logger.info("📋 Admin: POST /admin/question  (requires admin token)")
    logger.info("👤 User:  POST /submit/         (requires user token)")
    
    # Initialize Edge Caching
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        logger.info("⚡ Activating Redis Edge Caching")
        redis = aioredis.from_url(redis_url)
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    else:
        logger.info("⚡ Activating In-Memory Edge Caching (No REDIS_URL found)")
        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
        
    yield
    logger.info("🛑 Coding Assessment API v6 shutting down")

app = FastAPI(
    title="Coding Assessment API",
    description=(
        "Role-based coding interview platform. "
        "Admins manage questions using X-Admin-Key header. "
        "Users solve and submit code publicly driven by the envelope."
    ),
    version="6.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ────────────────────────────────────────────────────────
register_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(admin.router)      # /admin/*         admin_required
app.include_router(question.router)   # /question/*      mostly public
app.include_router(code.router)       # /code/run        public (raw)
app.include_router(submission.router) # /submit/*        user_required
app.include_router(assessment.router) # /assessment/*    user_required

