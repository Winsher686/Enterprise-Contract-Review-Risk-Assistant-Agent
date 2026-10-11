"""合同管理 API 集成测试。"""
import io


class TestContractUpload:
    def test_upload_txt(self, client):
        """上传 txt 合同成功。"""
        resp = client.post(
            "/api/contracts/upload",
            files={"file": ("test.txt", io.BytesIO("合同内容".encode("utf-8")), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "contract_id" in data
        assert data["file_type"] == "txt"

    def test_upload_with_custom_name(self, client):
        """上传时可指定合同名称。"""
        resp = client.post(
            "/api/contracts/upload",
            data={"name": "自定义合同名"},
            files={"file": ("a.txt", io.BytesIO("内容".encode("utf-8")), "text/plain")},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "自定义合同名"

    def test_list_contracts_empty(self, client):
        """初始合同列表应为空。"""
        resp = client.get("/api/contracts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_nonexistent_contract(self, client):
        """查询不存在的合同返回 404。"""
        resp = client.get("/api/contracts/nonexistent-id")
        assert resp.status_code == 404

    def test_upload_and_get(self, client):
        """上传后能查到合同详情（含条款）。"""
        up = client.post(
            "/api/contracts/upload",
            files={"file": ("c.txt", io.BytesIO("第一条 目的\n内容".encode()), "text/plain")},
        )
        cid = up.json()["contract_id"]
        resp = client.get(f"/api/contracts/{cid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == cid
        assert "clauses" in data
