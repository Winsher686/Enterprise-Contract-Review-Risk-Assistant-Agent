"""认证 API 集成测试。"""
import pytest


class TestAuth:
    def test_login_success(self, client):
        """正确账号密码登录成功。"""
        resp = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["username"] == "admin"

    def test_login_wrong_password(self, client):
        """错误密码返回 401。"""
        resp = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_login_missing_user(self, client):
        """不存在的用户返回 401。"""
        resp = client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "admin123"},
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        """缺少字段返回 422（pydantic 校验）。"""
        resp = client.post("/api/auth/login", json={"username": "admin"})
        assert resp.status_code == 422

    def test_token_is_valid_jwt(self, auth_token):
        """返回的 token 应为三段式 JWT。"""
        assert len(auth_token.split(".")) == 3
