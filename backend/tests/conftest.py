"""Pytest configuration and fixtures."""
import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="session", autouse=True)
def mock_env_variables():
    """Mock environment variables for all tests."""
    with patch.dict(os.environ, {
        "GEMINI_API_KEY": "test-gemini-key-12345",
        "FIREBASE_SERVICE_ACCOUNT_BASE64": "eyJ0ZXN0IjogImRhdGEifQ==",  # {"test": "data"} base64
        "GEMINI_MODEL": "gemini-2.5-pro",
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "LOG_LEVEL": "INFO",
        "CORS_ORIGINS": "[*]"
    }):
        yield


@pytest.fixture(autouse=True)
def reset_lru_cache():
    """Reset the settings cache between tests."""
    from core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
