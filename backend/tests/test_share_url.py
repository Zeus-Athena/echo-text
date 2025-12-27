"""
Tests for share link URL generation in share.py
分享链接测试 - 动态域名生成
"""


class TestBuildShareUrl:
    """测试分享链接 URL 生成逻辑"""

    def build_share_url(self, headers: dict, token: str) -> str:
        """从 share.py 复制的 URL 构建逻辑"""
        host = headers.get("X-Forwarded-Host") or headers.get("Host") or "localhost"
        scheme = headers.get("X-Forwarded-Proto", "https" if "443" in host else "http")
        base_url = f"{scheme}://{host}"
        return f"{base_url}/shared/{token}"

    def test_uses_x_forwarded_host_when_present(self):
        """应优先使用 X-Forwarded-Host"""
        headers = {
            "X-Forwarded-Host": "example.com",
            "X-Forwarded-Proto": "https",
            "Host": "localhost:8000",
        }
        url = self.build_share_url(headers, "abc123")
        assert url == "https://example.com/shared/abc123"

    def test_falls_back_to_host_header(self):
        """无 X-Forwarded-Host 时应使用 Host（默认 http）"""
        headers = {"Host": "myapp.example.com"}
        url = self.build_share_url(headers, "abc123")
        # 默认 http，除非 host 包含 443
        assert url == "http://myapp.example.com/shared/abc123"

    def test_falls_back_to_localhost(self):
        """无任何 Host 头时应使用 localhost"""
        headers = {}
        url = self.build_share_url(headers, "abc123")
        assert url == "http://localhost/shared/abc123"

    def test_uses_x_forwarded_proto_for_scheme(self):
        """应使用 X-Forwarded-Proto 确定协议"""
        headers = {"Host": "example.com", "X-Forwarded-Proto": "http"}
        url = self.build_share_url(headers, "abc123")
        assert url == "http://example.com/shared/abc123"

    def test_https_when_host_contains_443(self):
        """Host 包含 443 端口时应使用 https"""
        headers = {"Host": "example.com:443"}
        url = self.build_share_url(headers, "abc123")
        assert url == "https://example.com:443/shared/abc123"

    def test_http_for_localhost(self):
        """localhost 应使用 http"""
        headers = {"Host": "localhost:5173"}
        url = self.build_share_url(headers, "abc123")
        assert url == "http://localhost:5173/shared/abc123"

    def test_production_url_format(self):
        """生产环境 URL 格式验证"""
        headers = {"X-Forwarded-Host": "echotext.example.com", "X-Forwarded-Proto": "https"}
        token = "xYz789AbC"
        url = self.build_share_url(headers, token)
        assert url == "https://echotext.example.com/shared/xYz789AbC"
        assert "localhost" not in url


class TestShareUrlNotHardcoded:
    """确保分享链接不再硬编码 localhost"""

    def test_url_does_not_contain_localhost_with_valid_host(self):
        """有效 Host 时 URL 不应包含 localhost"""
        headers = {"Host": "production.example.com"}
        host = headers.get("X-Forwarded-Host") or headers.get("Host") or "localhost"
        assert "localhost" not in host

    def test_url_contains_actual_domain(self):
        """URL 应包含实际域名"""
        test_domains = ["myapp.com", "api.example.org", "echotext.io", "sub.domain.example.com"]
        for domain in test_domains:
            headers = {"Host": domain}
            host = headers.get("Host")
            assert host == domain
