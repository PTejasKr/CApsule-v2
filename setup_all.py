#!/usr/bin/env python3
"""
Capsule v2 — Single-File Setup & Bootstrapper Script
Run this file to set up environment, database, directories, BRD rules, and start the server:
    python setup_all.py [--start-server]
"""

import os
import sys
import shutil
import asyncio
import argparse
import logging

# Ensure root directory is in sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("capsule.setup_all")


def setup_environment_files():
    """Ensure .env file and required data directories exist."""
    logger.info("Step 1/5: Checking environment configuration & directories...")

    # Ensure required directories exist
    dirs_to_create = ["./data", "./database", "./brd", "./logs"]
    for d in dirs_to_create:
        dir_path = os.path.join(ROOT_DIR, d)
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"  ✓ Directory ready: {d}")

    # Check .env file
    env_path = os.path.join(ROOT_DIR, ".env")
    env_example_path = os.path.join(ROOT_DIR, ".env.example")

    if not os.path.exists(env_path):
        if os.path.exists(env_example_path):
            shutil.copy(env_example_path, env_path)
            logger.info("  ✓ Created .env from .env.example")
        else:
            logger.warning("  ! .env.example not found. Please create .env manually.")
    else:
        logger.info("  ✓ Existing .env file found.")

    # Ensure default BRD file exists
    brd_file = os.path.join(ROOT_DIR, "brd", "requirements.md")
    if not os.path.exists(brd_file):
        default_brd_content = """# Business Requirements Document

## Critical Workflows
- **Authentication**: Must use OAuth 2.0 with 2FA enabled
- **Payments**: Must integrate with Stripe (no custom payment logic)
- **Data Storage**: All PII must be encrypted with AES-256

## Code Standards
- Backend: FastAPI only
- Frontend: React or Vanilla JS
- Database: SQLite or PostgreSQL

## Approval Rules
- Changes to auth flow: Require security review
- Database schema changes: Require DBA approval
"""
        with open(brd_file, "w", encoding="utf-8") as f:
            f.write(default_brd_content.strip())
        logger.info("  ✓ Created default BRD file at ./brd/requirements.md")


async def setup_database_and_brd():
    """Initialize database tables and ingest default BRD rules."""
    logger.info("Step 2/5: Initializing Database Schema...")
    from backend.database import init_db
    await init_db()
    logger.info("  ✓ All database tables created/verified.")

    logger.info("Step 3/5: Loading BRD Business Rules into Database...")
    try:
        from backend.services.brd_manager import BRDManager
        brd_manager = BRDManager()
        await brd_manager.load_brd(profile_id=1)
        logger.info("  ✓ BRD requirements successfully ingested.")
    except Exception as e:
        logger.warning(f"  ! BRD Ingestion Notice: {e}")


def verify_configuration():
    """Verify essential settings in backend.config."""
    logger.info("Step 4/5: Running Pre-flight Configuration Verification...")
    try:
        from backend.config import settings
        logger.info(f"  ✓ Database URL: {settings.DATABASE_URL}")
        logger.info(f"  ✓ QStash URL: {settings.QSTASH_URL}")
        logger.info(f"  ✓ API Key: {'Configured' if settings.API_KEY else 'Missing'}")
        logger.info(f"  ✓ GitHub Token: {'Configured' if settings.GITHUB_TOKEN else 'Missing'}")
        logger.info(f"  ✓ NVIDIA NIM Key: {'Configured' if settings.NVIDIA_NIM_API_KEY else 'Missing'}")
    except Exception as e:
        logger.error(f"  ! Configuration error: {e}")


def launch_server(host: str = "0.0.0.0", port: int = 8000):
    """Launch the Uvicorn FastAPI server."""
    logger.info(f"Step 5/5: Launching Capsule API Server on http://{host}:{port}...")
    import uvicorn
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)


def main():
    parser = argparse.ArgumentParser(description="Capsule v2 Single-File Setup & Bootstrapper")
    parser.add_argument("--start-server", action="store_true", help="Automatically start Uvicorn API server after setup")
    parser.add_argument("--port", type=int, default=8000, help="Port to run Uvicorn server on (default: 8000)")
    args = parser.parse_args()

    print("==========================================================")
    print(" 🛡️  Capsule v2 — Single-File Setup & Bootstrapper")
    print("==========================================================")

    # 1. Environment & Files
    setup_environment_files()

    # 2 & 3. Database & BRD Ingestion
    asyncio.run(setup_database_and_brd())

    # 4. Configuration Check
    verify_configuration()

    print("\n==========================================================")
    print(" ✅ Setup Completed Successfully!")
    print(" 👑 Super Admin Dashboard: http://localhost:8000/admin")
    print("==========================================================\n")

    if args.start_server:
        launch_server(port=args.port)
    else:
        choice = input("Would you like to start the API server now? (Y/n): ").strip().lower()
        if choice in ["", "y", "yes"]:
            launch_server(port=args.port)


if __name__ == "__main__":
    main()
