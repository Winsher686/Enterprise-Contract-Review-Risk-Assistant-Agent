"""知识库 API 集成测试。"""
import io


class TestKnowledge:
    def test_stats(self, client):
        """知识库统计接口可用。"""
        resp = client.get("/api/knowledge/stats")
        assert resp.status_code == 200
        assert "total_chunks" in resp.json()

    def test_add_knowledge(self, client):
        """添加知识条目成功。"""
        resp = client.post(
            "/api/knowledge/add",
            json=[
                {"text": "测试知识条目", "source": "test", "category": "law"}
            ],
        )
        assert resp.status_code == 200
        assert resp.json()["added"] == 1

    def test_search_knowledge(self, client):
        """检索知识库返回结果。"""
        # 先添加知识
        client.post(
            "/api/knowledge/add",
            json=[{"text": "违约责任相关法律规定", "source": "民法典", "category": "law"}],
        )
        resp = client.post(
            "/api/knowledge/search",
            json={"query": "违约责任", "top_k": 3},
        )
        assert resp.status_code == 200
        results = resp.json()
        assert isinstance(results, list)

    def test_search_empty_query(self, client):
        """空查询应仍能返回（不报错）。"""
        resp = client.post(
            "/api/knowledge/search",
            json={"query": "", "top_k": 3},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
