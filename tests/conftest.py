import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def enable_simulation():
    original_mode = settings.simulation_mode
    settings.simulation_mode = True
    yield
    settings.simulation_mode = original_mode


@pytest.fixture
def disable_simulation():
    original_mode = settings.simulation_mode
    settings.simulation_mode = False
    yield
    settings.simulation_mode = original_mode
