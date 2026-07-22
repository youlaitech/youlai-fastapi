"""认证接口测试。"""

import pytest


@pytest.mark.anyio
async def test_get_captcha(async_client):
    """验证码生成接口 — 应返回 captchaId 和 captchaBase64。"""
    response = await async_client.get("/api/v1/auth/captcha")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "00000"
    assert "captchaId" in data["data"]
    assert "captchaBase64" in data["data"]


@pytest.mark.anyio
async def test_login_missing_params(async_client):
    """缺少参数时登录应返回参数校验错误 HTTP 422。"""
    response = await async_client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "A0400"


@pytest.mark.anyio
async def test_unauthorized_access(async_client):
    """未认证用户访问受保护接口应返回 HTTP 401。"""
    response = await async_client.get("/api/v1/auth/users/me")
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "A0230"


@pytest.mark.anyio
async def test_health_check(async_client):
    """健康检查端点应返回 200。"""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.anyio
async def test_swagger_accessible(async_client):
    """OpenAPI 文档应可访问。"""
    response = await async_client.get("/api/v1/swagger-ui.html")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_openapi_json(async_client):
    """OpenAPI JSON schema 应包含路由信息。"""
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    # 确认关键路由已注册
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/users" in schema["paths"]
    assert "/health" in schema["paths"]
