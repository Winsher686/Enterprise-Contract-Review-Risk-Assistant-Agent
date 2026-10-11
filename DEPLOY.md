# 服务器部署与测试指南

本文档说明在**一台全新的 Linux 服务器**上，如何零改动地完整部署并测试本项目。按顺序执行即可。

---

## 一、前置条件

| 项目 | 要求 |
|---|---|
| 操作系统 | Ubuntu 20.04+ / CentOS 7+ / Debian 11+ |
| 内存 | ≥ 4G（推荐 8G，跑完整 Docker 架构含 Milvus/Neo4j） |
| 磁盘 | ≥ 20G |
| 软件 | Docker + Docker Compose（本地模式则只需 Python 3.10+） |

---

## 二、获取项目

将本项目完整目录（`contract-review-agent/`）上传到服务器，例如：

```bash
# 假设上传到 /home/user/contract-review-agent
cd /home/user/contract-review-agent
```

---

## 三、选择运行方式

本项目提供两种运行方式，**二者代码零改动即可切换**：

### 方式 A：本地降级模式（最快，零中间件依赖）

适合快速验证，无需 Docker、无需数据库、无需 API Key。

```bash
cd backend

# 1. 安装 Python 依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 配置（默认 USE_DOCKER=false，无需改动）
cp ../.env.example .env

# 3. 启动
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 方式 B：完整 Docker 架构（企业级生产）

```bash
cd /home/user/contract-review-agent

# 配置大模型 API Key（可选，不填则 Mock 模式跑通全流程）
export LLM_API_KEY=sk-xxxx          # 如用 DeepSeek 再 export LLM_BASE_URL=https://api.deepseek.com
export LLM_MODEL=deepseek-chat

# 一键启动全部服务
docker compose up -d
```

启动后，Milvus（向量库）与 Neo4j（知识图谱）为**真实读写**：合同风险分析会自动把「条款→风险→法规」关系写入 Neo4j 图谱，法律知识向量写入 Milvus。若中间件连接失败，代码自动降级为内存实现，不影响核心审查流程。

> 内存不足 8G 时，可注释掉 `docker-compose.yml` 中的 `milvus`、`neo4j` 服务，核心流程仍可运行。

### 数据库迁移（生产环境规范）

Docker 模式使用 PostgreSQL，建表由 Alembic 迁移管理：

```bash
cd backend
# 首次部署：应用初始 schema
alembic upgrade head

# 模型变更后：生成新迁移并应用
alembic revision --autogenerate -m "变更描述"
alembic upgrade head
```

---

## 四、测试验证清单

服务启动后，按以下步骤验证系统是否完整可用。

### 1. 健康检查

```bash
curl http://localhost:8000/health
# 期望返回：{"status":"ok"}
```

### 2. 打开 Web 管理界面（推荐）

浏览器访问 `http://<服务器IP>:8000/ui`，使用默认账号 `admin / admin123` 登录，即可完成：
上传合同 → 启动审查 → 实时进度 → 风险清单（等级过滤）→ 报告总览 → 条款解析 → 知识库检索。

### 3. 查看 API 文档

浏览器访问 `http://<服务器IP>:8000/docs`，应能看到 Swagger 接口文档。

### 4. 登录（默认账号）

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
# 期望返回 token 和 user 信息
```

### 5. 一键端到端测试（推荐）

在**另一台机器**（或服务器本机）执行 demo 脚本，跑通完整审查流程：

```bash
# 在项目根目录（含 examples/ 和 scripts/ 的地方）
pip install httpx   # 若已装则跳过
python scripts/demo.py
```

> 注意：若服务部署在远程服务器，需先将 `scripts/demo.py` 里的
> `BASE_URL = "http://localhost:8000/api"` 改为 `http://<服务器IP>:8000/api`。

**期望输出**：上传合同 → 创建审查任务 → 状态 completed → 输出 7 个风险 → 生成报告。

### 6. 运行自动化测试套件

```bash
cd backend
pytest            # 88 个用例，全绿通过
pytest --cov=app  # 查看覆盖率（约 88%）
```

测试使用内存 SQLite + Mock LLM，不依赖外部服务与 API Key，可在服务器上快速自检代码完整性。

### 7. 手动 API 流程测试（可选，更详细）

```bash
# ① 上传示例合同
curl -X POST http://localhost:8000/api/contracts/upload \
  -F "file=@examples/供应商采购合同.txt"

# 记录返回的 contract_id，然后：

# ② 创建审查任务
curl -X POST http://localhost:8000/api/reviews/create \
  -H "Content-Type: application/json" \
  -d '{"contract_id":"<上一步的contract_id>","review_type":"full"}'

# 记录返回的 task_id，然后：

# ③ 查询审查状态（异步，可多次查询直到 completed）
curl http://localhost:8000/api/reviews/<task_id>/status

# ④ 获取风险结果
curl http://localhost:8000/api/reviews/<task_id>/risks

# ⑤ 获取审查报告
curl http://localhost:8000/api/reviews/<task_id>/report
```

---

## 五、接入真实大模型（可选）

本地 Mock 模式已能跑通全流程（用内置规则引擎 + 启发式逻辑）。如需真实 LLM 分析，编辑 `backend/.env`：

```bash
# OpenAI
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# 或 DeepSeek（国内推荐）
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

配置后重启服务，系统自动从 Mock 切换为真实模式。

---

## 六、常见问题排查

| 问题 | 排查方法 |
|---|---|
| 端口被占用 | `lsof -i:8000` 查看占用进程，或修改端口 |
| 依赖安装失败 | 升级 pip：`pip install --upgrade pip`，或更换镜像源 |
| Docker 启动失败 | `docker compose logs backend` 查看日志 |
| postgres 连接失败 | 等待 postgres 健康检查通过（`docker compose ps` 查看） |
| 中文乱码 | 确认服务器 locale 支持 UTF-8 |

---

## 七、项目结构速览

```
contract-review-agent/
├── backend/              # FastAPI 后端（核心）
│   ├── app/
│   │   ├── api/          # API 层
│   │   ├── agents/       # Multi-Agent（Parser/Clause/Risk/Legal/Report/Orchestrator）
│   │   ├── rag/          # RAG（解析/切分/向量/混合检索/Reranker）
│   │   ├── tools/        # 工具层 + 规则引擎
│   │   ├── models/       # ORM 模型
│   │   ├── services/     # 业务服务层
│   │   └── ...
│   └── requirements.txt
├── knowledge_base/       # 知识库（raw 示例文档 + 构建脚本）
├── examples/             # 示例合同
├── storage/              # 文件存储
├── docker/               # Dockerfile + nginx 配置
├── docker-compose.yml    # Docker 编排（根目录）
├── scripts/demo.py       # 端到端演示脚本
└── README.md
```
