"""知识图谱存储单元测试。

验证 GraphStore 在本地降级模式下的内存实现，以及风险关系写入逻辑。
Neo4j 真实连接路径依赖外部服务，此处验证内存降级与接口契约。
"""
from app.graph.store import GraphStore


class TestGraphStore:
    def test_add_risk_relation_memory(self, monkeypatch):
        """内存模式下添加风险关系应记录节点。"""
        # 确保为内存模式
        monkeypatch.setattr("app.graph.store.settings.USE_DOCKER", False)
        store = GraphStore()
        assert not store._neo4j_available

        store.add_risk_relation(
            clause="付款方式",
            risk_type="付款风险",
            law="企业合同管理制度",
            contract_type="采购合同",
        )

        assert {"name": "付款方式"} in store._memory_nodes["Clause"]
        assert {"name": "付款风险"} in store._memory_nodes["Risk"]
        assert {"name": "企业合同管理制度"} in store._memory_nodes["Law"]

    def test_add_risk_relation_without_law(self):
        """无法律来源时不应写入 Law 节点。"""
        store = GraphStore()
        store.add_risk_relation(clause="保密条款", risk_type="保密风险")
        assert {"name": "保密风险"} in store._memory_nodes["Risk"]
        # 未提供 law，Law 节点数不应增加
        assert store._memory_nodes["Law"] == []

    def test_query_related_risks(self):
        """查询相关风险应返回已记录的风险类型。"""
        store = GraphStore()
        store.add_risk_relation(clause="违约责任", risk_type="违约责任风险")
        store.add_risk_relation(clause="付款方式", risk_type="付款风险")
        risks = store.query_related_risks("违约责任")
        assert "违约责任风险" in risks

    def test_query_supporting_laws(self):
        """查询风险的法律依据。"""
        store = GraphStore()
        store.add_risk_relation(
            clause="付款方式", risk_type="付款风险", law="民法典"
        )
        laws = store.query_supporting_laws("付款风险")
        assert "民法典" in laws

    def test_neo4j_unavailable_falls_back(self, monkeypatch):
        """USE_DOCKER=true 但连接失败时应降级为内存模式。"""
        monkeypatch.setattr("app.graph.store.settings.USE_DOCKER", True)
        store = GraphStore()
        # 无真实 Neo4j 服务，应降级为内存
        assert not store._neo4j_available
        # 降级后 add 仍走内存
        store.add_risk_relation(clause="x", risk_type="y")
        assert {"name": "y"} in store._memory_nodes["Risk"]
        store.close()
