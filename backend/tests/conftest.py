"""
Pytest global fixtures for backend test suite.
"""

import pytest
from app.core.limiter import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter counters before and after each test to prevent cross-test coupling."""
    limiter.reset()
    yield
    limiter.reset()
