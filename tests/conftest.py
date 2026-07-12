"""Pytest 测试配置。"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def app():
    """创建测试用 FastAPI 应用。"""
    return create_app()


@pytest.fixture
async def async_client(app):
    """创建异步 HTTP 测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
