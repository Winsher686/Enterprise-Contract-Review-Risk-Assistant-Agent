"""知识图谱模块（Neo4j）。

双模式实现：
- USE_DOCKER=true  -> Neo4j（真实图数据库，需 neo4j 驱动 + Neo4j 服务）
- USE_DOCKER=false -> 内存结构（降级，不影响核心流程）

图模型：
    ContractType -[HAS_CLAUSE]-> Clause -[CAUSES]-> Risk -[SUPPORTED_BY]-> Law

Neo4j 连接失败时自动降级为内存模式，保证核心流程不中断。
"""
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.utils.logger import logger


class GraphStore:
    """知识图谱存储接口。

    Neo4j 模式：真实写入节点与关系。
    内存模式：字典降级。
    """

    def __init__(self) -> None:
        self._use_neo4j = settings.USE_DOCKER
        self._driver = None
        self._neo4j_available = False
        self._memory_nodes: Dict[str, List[Dict]] = {
            "Clause": [],
            "Risk": [],
            "Law": [],
        }

        if self._use_neo4j:
            self._init_neo4j()
        else:
            logger.info("知识图谱：内存模式（降级）")

    # ---------------- Neo4j 初始化 ----------------
    def _init_neo4j(self) -> None:
        """尝试连接 Neo4j；失败则降级为内存模式。"""
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
            # 验证连接
            with self._driver.session() as session:
                session.run("RETURN 1").single()
            self._neo4j_available = True
            self._ensure_constraints()
            logger.info(f"知识图谱：Neo4j 模式（uri={settings.NEO4J_URI}）")
        except Exception as e:  # pragma: no cover - 依赖外部服务
            self._driver = None
            self._neo4j_available = False
            logger.warning(f"Neo4j 连接失败，降级为内存模式：{e}")

    def _ensure_constraints(self) -> None:
        """创建唯一性约束，避免重复节点。"""
        if not self._driver:
            return
        try:
            with self._driver.session() as session:
                session.run(
                    "CREATE CONSTRAINT clause_name IF NOT EXISTS "
                    "FOR (c:Clause) REQUIRE c.name IS UNIQUE"
                )
                session.run(
                    "CREATE CONSTRAINT risk_type IF NOT EXISTS "
                    "FOR (r:Risk) REQUIRE r.type IS UNIQUE"
                )
                session.run(
                    "CREATE CONSTRAINT law_name IF NOT EXISTS "
                    "FOR (l:Law) REQUIRE l.name IS UNIQUE"
                )
        except Exception as e:  # pragma: no cover
            logger.warning(f"创建 Neo4j 约束失败（可能已存在或版本不支持）：{e}")

    # ---------------- 对外接口 ----------------
    def add_risk_relation(
        self,
        clause: str,
        risk_type: str,
        law: Optional[str] = None,
        contract_type: Optional[str] = None,
    ) -> None:
        """添加「条款-产生-风险-依据-法规」关系。

        参数：
            clause: 条款名（如「付款方式」）
            risk_type: 风险类型（如「付款风险」）
            law: 法律/制度依据来源（可选）
            contract_type: 合同类型（可选）
        """
        if self._neo4j_available:
            try:
                self._add_neo4j(clause, risk_type, law, contract_type)
                return
            except Exception as e:  # pragma: no cover
                logger.warning(f"Neo4j 写入失败，降级内存：{e}")
                self._neo4j_available = False

        # 内存降级
        self._memory_nodes["Clause"].append({"name": clause})
        self._memory_nodes["Risk"].append({"name": risk_type})
        if law:
            self._memory_nodes["Law"].append({"name": law})

    def _add_neo4j(self, clause, risk_type, law, contract_type) -> None:
        with self._driver.session() as session:
            session.execute_write(
                self._create_relation_tx,
                clause, risk_type, law, contract_type,
            )

    @staticmethod
    def _create_relation_tx(tx, clause, risk_type, law, contract_type):
        """在事务中创建节点与关系（MERGE 保证幂等）。"""
        # 条款节点
        tx.run(
            "MERGE (c:Clause {name: $clause})",
            clause=clause,
        )
        # 风险节点
        tx.run(
            "MERGE (r:Risk {type: $risk})",
            risk=risk_type,
        )
        # 条款 -> 风险
        tx.run(
            """
            MATCH (c:Clause {name: $clause})
            MATCH (r:Risk {type: $risk})
            MERGE (c)-[:CAUSES]->(r)
            """,
            clause=clause,
            risk=risk_type,
        )
        # 合同类型 -> 条款
        if contract_type:
            tx.run(
                "MERGE (ct:ContractType {name: $ct})",
                ct=contract_type,
            )
            tx.run(
                """
                MATCH (ct:ContractType {name: $ct})
                MATCH (c:Clause {name: $clause})
                MERGE (ct)-[:HAS_CLAUSE]->(c)
                """,
                ct=contract_type,
                clause=clause,
            )
        # 风险 -> 法规
        if law:
            tx.run(
                "MERGE (l:Law {name: $law})",
                law=law,
            )
            tx.run(
                """
                MATCH (r:Risk {type: $risk})
                MATCH (l:Law {name: $law})
                MERGE (r)-[:SUPPORTED_BY]->(l)
                """,
                risk=risk_type,
                law=law,
            )

    def query_related_risks(self, clause: str) -> List[str]:
        """查询条款相关的风险类型。"""
        if self._neo4j_available:
            try:
                with self._driver.session() as session:
                    result = session.run(
                        """
                        MATCH (c:Clause {name: $clause})-[:CAUSES]->(r:Risk)
                        RETURN r.type AS type
                        """,
                        clause=clause,
                    )
                    return [record["type"] for record in result]
            except Exception as e:  # pragma: no cover
                logger.warning(f"Neo4j 查询失败，降级内存：{e}")
                self._neo4j_available = False

        return [n["name"] for n in self._memory_nodes["Risk"]]

    def query_supporting_laws(self, risk_type: str) -> List[str]:
        """查询风险类型的法律依据。"""
        if self._neo4j_available:
            try:
                with self._driver.session() as session:
                    result = session.run(
                        """
                        MATCH (r:Risk {type: $risk})-[:SUPPORTED_BY]->(l:Law)
                        RETURN l.name AS name
                        """,
                        risk=risk_type,
                    )
                    return [record["name"] for record in result]
            except Exception as e:  # pragma: no cover
                logger.warning(f"Neo4j 查询失败，降级内存：{e}")
                self._neo4j_available = False

        return [n["name"] for n in self._memory_nodes["Law"]]

    def close(self) -> None:
        """关闭驱动连接。"""
        if self._driver:
            self._driver.close()


# 全局单例
graph_store = GraphStore()
