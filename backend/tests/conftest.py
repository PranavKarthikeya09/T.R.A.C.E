"""Test fixtures and setup using FastAPI TestClient."""
import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure backend root and app directory are on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app


@pytest.fixture
def client():
    """Synchronous test client fixture for FastAPI."""
    with TestClient(app) as test_client:
        yield test_client
