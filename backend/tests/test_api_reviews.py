"""合同审查流程集成测试（端到端）。

覆盖：上传合同 -> 创建审查任务 -> 轮询状态 -> 获取风险 -> 获取报告。
这是系统核心链路，Mock LLM + 测试数据库环境下应完整跑通。
"""
import io
import time


SAMPLE_CONTRACT = """采购合同

合同编号：CG-2026-001

甲方：示例有限公司
乙方：示例科技有限公司

第一条 合同目的
甲乙双方本着平等互利的原则，就货物采购事宜达成如下协议。

第二条 付款方式
甲方应在收到货物后支付合同款项。

第三条 违约责任
乙方逾期交付，无需承担任何责任。

第四条 保密条款
双方应对合作内容保密。
"""


def _upload_contract(client):
    resp = client.post(
        "/api/contracts/upload",
        files={"file": ("采购合同.txt", io.BytesIO(SAMPLE_CONTRACT.encode("utf-8")), "text/plain")},
    )
    assert resp.status_code == 200
    return resp.json()["contract_id"]


def _wait_for_completion(client, task_id, timeout=15.0):
    """轮询任务状态直到完成/失败，返回最终状态。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/reviews/{task_id}/status")
        assert resp.status_code == 200
        status = resp.json()
        if status["status"] in ("completed", "failed"):
            return status
        time.sleep(0.2)
    raise TimeoutError(f"审查任务超时未完成：{task_id}")


class TestReviewFlow:
    def test_create_review_nonexistent_contract(self, client):
        """对不存在的合同创建审查返回 404。"""
        resp = client.post(
            "/api/reviews/create",
            json={"contract_id": "nonexistent", "review_type": "full"},
        )
        assert resp.status_code == 404

    def test_get_status_nonexistent_task(self, client):
        """查询不存在的任务返回 404。"""
        resp = client.get("/api/reviews/nonexistent/status")
        assert resp.status_code == 404

    def test_full_review_flow(self, client):
        """完整审查流程端到端跑通。"""
        # 1. 上传合同
        contract_id = _upload_contract(client)

        # 2. 创建审查任务
        resp = client.post(
            "/api/reviews/create",
            json={"contract_id": contract_id, "review_type": "full"},
        )
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]
        assert resp.json()["status"] == "pending"

        # 3. 等待完成
        final = _wait_for_completion(client, task_id)
        assert final["status"] == "completed", f"审查失败：{final}"
        assert final["progress"] == 100

        # 4. 获取风险
        risks = client.get(f"/api/reviews/{task_id}/risks").json()
        assert isinstance(risks, list)
        assert len(risks) >= 1, "应至少识别出一个风险"
        # 风险结构完整
        for r in risks:
            assert "risk_type" in r
            assert "risk_level" in r

        # 5. 获取报告
        report = client.get(f"/api/reviews/{task_id}/report").json()
        assert "overall_level" in report
        assert "risk_statistics" in report
        stats = report["risk_statistics"]
        assert stats["total"] == len(risks)

    def test_review_detects_liability_risk(self, client):
        """应识别出违约责任风险（免责条款）。"""
        contract_id = _upload_contract(client)
        resp = client.post(
            "/api/reviews/create",
            json={"contract_id": contract_id, "review_type": "full"},
        )
        task_id = resp.json()["task_id"]
        final = _wait_for_completion(client, task_id)
        assert final["status"] == "completed"

        risks = client.get(f"/api/reviews/{task_id}/risks").json()
        risk_types = [r["risk_type"] for r in risks]
        assert "违约责任风险" in risk_types, f"未识别违约责任，风险类型：{risk_types}"

    def test_amount_risk_only_once(self, client):
        """大额合同风险只应出现一次（不重复）。"""
        contract_id = _upload_contract(client)
        resp = client.post(
            "/api/reviews/create",
            json={"contract_id": contract_id, "review_type": "full"},
        )
        task_id = resp.json()["task_id"]
        _wait_for_completion(client, task_id)

        risks = client.get(f"/api/reviews/{task_id}/risks").json()
        contract_level = [r for r in risks if r["clause_name"] == "合同整体"]
        # 无金额时（Mock parse 默认 500万），合同级规则可能触发，但最多一次
        assert len(contract_level) <= 1


class TestReports:
    def test_report_not_found(self, client):
        """未审查的合同报告返回 404。"""
        contract_id = _upload_contract(client)
        resp = client.get(f"/api/reports/{contract_id}")
        assert resp.status_code == 404
