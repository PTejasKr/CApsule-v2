import sys
import os
import pytest
import asyncio

os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_capsule.db"

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    from extension.backend.database import init_db
    asyncio.run(init_db())

