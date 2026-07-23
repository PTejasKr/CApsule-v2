import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database import init_db
from backend.services.brd_manager import BRDManager
from backend.routers import webhooks, api, profiles, auth

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("capsule.main")

_IS_PRODUCTION = os.environ.get("ENV", "production").lower() == "production"
_docs_url = None if _IS_PRODUCTION else "/docs"
_redoc_url = None if _IS_PRODUCTION else "/redoc"
_openapi_url = None if _IS_PRODUCTION else "/openapi.json"

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Capsule API Service...")
    
    await init_db()
    
    brd_manager = BRDManager()
    await brd_manager.load_brd(profile_id=1)
    
    logger.info("Capsule API Service successfully started and ready to handle requests.")
    yield

app = FastAPI(
    title="Capsule — PR Analyzer API",
    description="Backend service for AI-powered PR analysis, workflow impact detection, and changelog generation.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request
from backend.middleware.rate_limiter import RateLimiterMiddleware

ALLOWED_ORIGINS = [
    "https://capsule-opal-nine.vercel.app",
    "chrome-extension://",  # Chrome extension origins are validated by API key
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Chrome extensions need wildcard; security is enforced by X-API-Key
    allow_credentials=False,      # Credentials=False with wildcard is safe and valid
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "Authorization", "x-hub-signature-256"],
)

# Enterprise Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimiterMiddleware, requests_per_minute=120)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "status": "error"}
    )

from backend.middleware.security import verify_github_signature
from fastapi import Depends

app.include_router(auth.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(webhooks.router)
app.include_router(api.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")

app.post("/api/webhook/github", status_code=200, dependencies=[Depends(verify_github_signature)])(webhooks.github_webhook)

@app.get("/")
def read_root():
    return {
        "project": "Capsule",
        "status": "operational",
        "version": "1.0.0",
    }




