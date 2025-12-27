"""
Tests for core/security.py
安全工具测试 (密码哈希和 JWT)
"""

from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    """密码哈希测试"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """测试正确密码验证"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password("wrongpassword", hashed) is False

    def test_different_passwords_different_hashes(self):
        """测试不同密码产生不同哈希"""
        hash1 = get_password_hash("password1")
        hash2 = get_password_hash("password2")

        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """测试相同密码产生不同哈希（salted）"""
        password = "samepassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # bcrypt uses random salt, so hashes should differ
        assert hash1 != hash2

    def test_empty_password(self):
        """测试空密码"""
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True

    def test_unicode_password(self):
        """测试 Unicode 密码"""
        password = "密码测试123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_long_password(self):
        """测试长密码"""
        password = "a" * 100
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


class TestJWTTokens:
    """JWT Token 测试"""

    def test_create_access_token(self):
        """测试创建 access token"""
        token = create_access_token(subject="user123")

        assert isinstance(token, str)
        assert len(token) > 0
        # JWT format: header.payload.signature
        assert token.count(".") == 2

    def test_decode_access_token(self):
        """测试解码 access token"""
        user_id = "user456"
        token = create_access_token(subject=user_id)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id

    def test_create_access_token_with_expiry(self):
        """测试自定义过期时间"""
        token = create_access_token(subject="user123", expires_delta=timedelta(hours=1))

        payload = decode_token(token)
        assert payload is not None
        assert "exp" in payload

    def test_create_access_token_with_extra_data(self):
        """测试附加数据"""
        token = create_access_token(
            subject="user123", extra_data={"role": "admin", "name": "Test User"}
        )

        payload = decode_token(token)
        assert payload is not None
        assert payload["role"] == "admin"
        assert payload["name"] == "Test User"

    def test_create_refresh_token(self):
        """测试创建 refresh token"""
        token = create_refresh_token(subject="user789")

        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_refresh_token(self):
        """测试解码 refresh token"""
        user_id = "user789"
        token = create_refresh_token(subject=user_id)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        """测试解码无效 token"""
        payload = decode_token("invalid.token.here")

        assert payload is None

    def test_decode_expired_token(self):
        """测试解码过期 token"""
        token = create_access_token(
            subject="user123",
            expires_delta=timedelta(seconds=-1),  # 已过期
        )

        payload = decode_token(token)
        assert payload is None

    def test_decode_tampered_token(self):
        """测试解码篡改 token"""
        token = create_access_token(subject="user123")
        # 篡改签名
        tampered = token[:-10] + "tamperedxx"

        payload = decode_token(tampered)
        assert payload is None

    def test_decode_empty_token(self):
        """测试解码空 token"""
        payload = decode_token("")
        assert payload is None

    def test_token_subject_types(self):
        """测试不同类型的 subject"""
        # String subject
        token1 = create_access_token(subject="user123")
        payload1 = decode_token(token1)
        assert payload1["sub"] == "user123"

        # UUID-like subject
        token2 = create_access_token(subject="550e8400-e29b-41d4-a716-446655440000")
        payload2 = decode_token(token2)
        assert payload2["sub"] == "550e8400-e29b-41d4-a716-446655440000"

        # Integer subject (converted to string)
        token3 = create_access_token(subject=12345)
        payload3 = decode_token(token3)
        assert payload3["sub"] == "12345"
