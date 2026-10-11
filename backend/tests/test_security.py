"""JWT 认证工具单元测试。"""
import time

from app.utils.security import create_token, verify_token


class TestJWT:
    def test_create_and_verify(self):
        """正常生成与校验 token。"""
        token = create_token("user-123", "admin")
        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "user-123"
        assert payload["role"] == "admin"

    def test_tampered_token_rejected(self):
        """篡改后的 token 应校验失败。"""
        token = create_token("user-123", "admin")
        # 篡改 payload 部分
        parts = token.split(".")
        tampered = parts[0] + ".dGFtcGVyZWQ." + parts[2]
        assert verify_token(tampered) is None

    def test_invalid_token_structure(self):
        """结构非法的 token 返回 None。"""
        assert verify_token("not-a-jwt") is None
        assert verify_token("") is None
        assert verify_token("a.b") is None

    def test_expired_token_rejected(self):
        """过期 token 应校验失败。"""
        token = create_token("user-123", "admin", expires_hours=-1)
        assert verify_token(token) is None

    def test_token_contains_three_parts(self):
        """token 应为三段式。"""
        token = create_token("u", "r")
        assert len(token.split(".")) == 3
