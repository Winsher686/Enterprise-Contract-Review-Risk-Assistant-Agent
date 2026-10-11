"""前端静态资源集成测试。

验证 /ui 和 /static 挂载正确（前端 Web 界面可访问）。
"""
import os


class TestFrontend:
    def test_ui_page_served(self, client):
        """/ui 返回前端页面。"""
        resp = client.get("/ui")
        assert resp.status_code == 200
        assert "企业合同智能审查" in resp.text

    def test_static_css(self, client):
        """/static/style.css 可访问。"""
        resp = client.get("/static/style.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers.get("content-type", "")

    def test_static_js(self, client):
        """/static/app.js 可访问。"""
        resp = client.get("/static/app.js")
        assert resp.status_code == 200

    def test_root_has_ui_field(self, client):
        """根接口包含 ui 字段。"""
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["ui"] == "/ui"

    def test_health(self, client):
        """健康检查。"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
