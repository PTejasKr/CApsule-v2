import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from extension.backend.config import settings
from extension.backend.database import init_db
from extension.backend.middleware.security import verify_github_signature
from extension.backend.services.brd_manager import BRDManager
from extension.backend.routers import webhooks, api, profiles, auth, admin, teams, analytics
from prometheus_fastapi_instrumentator import Instrumentator
from extension.backend.tasks_scheduler import get_scheduler

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("capsule.main")

_IS_PRODUCTION = os.environ.get("ENV", "development").lower() == "production"
_docs_url = None if _IS_PRODUCTION else "/docs"
_redoc_url = None if _IS_PRODUCTION else "/redoc"
_openapi_url = None if _IS_PRODUCTION else "/openapi.json"

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Capsule API Service...")
    
    await init_db()
    
    brd_manager = BRDManager()
    await brd_manager.load_brd(profile_id=1)
    
    scheduler = get_scheduler()
    scheduler.start()
    
    logger.info("Capsule API Service successfully started and ready to handle requests.")
    yield
    scheduler.shutdown()

app = FastAPI(
    title="Capsule — PR Analyzer API",
    description="Backend service for AI-powered PR analysis, workflow impact detection, and changelog generation.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

Instrumentator().instrument(app).expose(app)

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

app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(webhooks.router)
app.include_router(webhooks.router, prefix="/api")
app.include_router(api.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(teams.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "website", "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "website", "templates"))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    response = templates.TemplateResponse("dashboard.html", {"request": request})
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
@app.get("/sw.js")
async def get_service_worker():
    return FileResponse(os.path.join(os.path.dirname(__file__), "website", "static", "service-worker.js"))
