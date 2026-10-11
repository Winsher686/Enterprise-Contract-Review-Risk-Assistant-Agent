# 企业合同智能审查与风险辅助 Agent

面向企业法务合同审核场景，基于 **RAG + Agent** 的合同智能审查系统。实现合同解析、条款识别、法律依据检索、风险分析以及自动化审查报告生成。

## 项目定位

解决传统合同审查的三大痛点：
- **人工审核效率低**：几十页合同需数小时甚至数天
- **风险识别依赖经验**：不同法务发现的风险数量不一致
- **法律依据查询困难**：风险发现后还需人工检索法规确认

## 核心架构

```
用户上传合同
    ↓
Contract Service（FastAPI）
    ↓
Agent Orchestrator（智能审查核心）
    ↓
┌─────────────────────────────────────┐
│ Parser → Clause → Risk → Legal → Report │  ← Multi-Agent
└─────────────────────────────────────┘
    ↓
Tool Calling Layer（工具层）
    ↓
┌──────────────────────────┐
│ RAG检索 │ 规则引擎 │ 向量库 │
└──────────────────────────┘
    ↓
审查报告生成
```

### 技术栈

| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI（lifespan 生命周期管理） |
| Agent 编排 | 自研 Orchestrator + Multi-Agent |
| 检索 | Hybrid Retrieval（向量 + BM25）+ RRF + Reranker |
| 向量库 | Milvus（Docker，真实读写）/ 内存向量（本地降级） |
| 知识图谱 | Neo4j（Docker，真实读写）/ 内存（本地降级） |
| 业务数据库 | PostgreSQL（Docker）/ SQLite（本地），Alembic 迁移 |
| 缓存/队列 | Redis + Celery（Docker）/ 线程池（本地） |
| 大模型 | OpenAI 协议（兼容 DeepSeek 等）/ Mock |

## 两种运行模式

### 模式一：本地降级模式（推荐快速体验，零外部依赖）

无需 Docker、无需数据库、无需 API Key，clone 即可运行。

```bash
cd contract-review-agent/backend

# 创建虚拟环境并安装依赖
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt

# 复制环境配置（默认 USE_DOCKER=false）
cp ../.env.example .env

# 启动
uvicorn app.main:app --reload
```

访问 http://localhost:8000/ui 打开 **Web 管理界面**（登录、上传合同、审查进度、风险清单、报告总览、知识库检索）。
访问 http://localhost:8000/docs 查看 API 文档。

> 默认 LLM 为 Mock 模式（未配置 API Key），用内置规则引擎 + 启发式逻辑跑通全流程。

### 模式二：完整 Docker 架构（企业级生产）

```bash
cd contract-review-agent

# 配置 API Key（可选，不填则 Mock）
export LLM_API_KEY=your_key

docker compose up -d
```

启动 7 个服务：backend + celery_worker + postgres + redis + milvus + neo4j + nginx。

> **说明**：Milvus（向量库）与 Neo4j（知识图谱）在 Docker 模式下为**真实读写**（数据持久化到对应中间件），风险分析会自动写入「条款→风险→法规」知识图谱关系。若中间件连接失败，代码会自动降级为内存实现，核心审查流程不受影响。若服务器内存不足（< 8G），可注释掉 `docker-compose.yml` 中的 `milvus`、`neo4j` 服务，并将 `backend` 的 `depends_on` 对应项移除。

### 数据库迁移（生产环境）

生产环境使用 Alembic 管理数据库 schema 变更：

```bash
cd backend

# 生成迁移脚本（模型变更后执行）
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head
```

初始 schema 迁移脚本已生成（`alembic/versions/`），首次部署执行 `alembic upgrade head` 即可建表。

### 接入真实大模型（可选）

编辑 `.env`，填入 API Key 后自动切换真实模式：

```bash
# 使用 OpenAI
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# 或使用 DeepSeek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

## 快速体验流程

1. **上传合同**：POST `/api/contracts/upload` 上传 `examples/供应商采购合同.txt`
2. **创建审查任务**：POST `/api/reviews/create`，body `{"contract_id": "xxx"}`
3. **查询状态**：GET `/api/reviews/{task_id}/status`（异步执行）
4. **获取风险**：GET `/api/reviews/{task_id}/risks`
5. **获取报告**：GET `/api/reviews/{task_id}/report`

也可使用示例脚本一键跑通：

```bash
python scripts/demo.py
```

## 运行测试

项目内置完整测试套件（单元测试 + API 集成测试），覆盖核心业务逻辑与端到端审查流程：

```bash
cd backend
# 安装测试依赖（已包含在 requirements.txt 中）
pip install -r requirements.txt

# 运行全部测试
pytest

# 运行并查看覆盖率
pytest --cov=app --cov-report=term-missing
```

测试覆盖：规则引擎、文本切分、JWT 认证、Mock LLM 逻辑、RAG 检索、知识图谱存储、RiskAgent 三层检测模型（含图谱写入）、以及认证/合同/审查/报告/知识库/前端等 API 端到端流程（88 个用例，整体覆盖率约 88%）。测试使用内存 SQLite 与 Mock LLM，不依赖外部服务与 API Key，可重复执行。

## 核心 API

| 模块 | 接口 | 说明 |
|---|---|---|
| 认证 | POST /api/auth/login | 登录（默认 admin/admin123） |
| 合同 | POST /api/contracts/upload | 上传合同 |
| 合同 | GET /api/contracts | 合同列表 |
| 审查 | POST /api/reviews/create | 创建审查任务 |
| 审查 | GET /api/reviews/{id}/status | 查询状态 |
| 审查 | GET /api/reviews/{id}/risks | 获取风险 |
| 报告 | GET /api/reviews/{id}/report | 获取报告 |
| 知识库 | POST /api/knowledge/add | 添加知识 |
| 知识库 | POST /api/knowledge/search | 检索知识 |

## 项目结构

```
contract-review-agent/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── api/             # API 层（auth/contracts/reviews/reports/knowledge）
│   │   ├── core/            # 配置、LLM 客户端、知识库加载器
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   ├── schemas/         # Pydantic Schema
│   │   ├── services/        # 业务服务层
│   │   ├── agents/          # Multi-Agent（Parser/Clause/Risk/Legal/Report/Orchestrator）
│   │   ├── rag/             # RAG（解析/切分/向量/混合检索/Reranker）
│   │   ├── tools/           # Tool 层 + 规则引擎
│   │   ├── graph/           # 知识图谱（Neo4j/内存）
│   │   ├── database/        # 数据库连接
│   │   ├── tasks/           # 异步任务（Celery/线程池）
│   │   ├── prompts/         # Prompt 集中管理
│   │   └── utils/           # 工具（日志/文件/安全/响应）
│   ├── tests/               # 测试套件（单元测试 + API 集成测试）
│   ├── pytest.ini           # pytest 配置
│   ├── alembic/             # 数据库迁移（env.py + versions/）
│   ├── alembic.ini          # alembic 配置
│   └── requirements.txt
├── knowledge_base/          # 知识库（raw/cleaned/chunks/embeddings/scripts）
├── storage/                 # 文件存储（contracts/reports）
├── examples/                # 示例合同
├── docker/                  # Docker 配置
├── docker-compose.yml
└── README.md
```

## 设计亮点

1. **三层风险检测模型**：规则引擎（确定性）→ RAG 知识增强（可追溯）→ LLM 语义推理（理解语义）
2. **Agent 编排**：固定 Workflow + LLM 决策，兼顾稳定性与灵活性
3. **混合检索**：向量 + BM25 + RRF 融合 + Reranker，兼顾语义与精确匹配
4. **引用溯源**：每个风险绑定法律依据来源，支持企业级可信要求
5. **Human-in-the-loop**：风险需人工确认，符合企业法务场景

## 参考项目规划

完整 11 阶段设计文档见 `项目A：企业合同智能审查与风险辅助 Agent.md`（尚硅谷大模型项目规划）。
