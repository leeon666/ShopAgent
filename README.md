# ShopAgent

ShopAgent 是一个“商城后端 + 智能售后 Agent”的综合项目。它基于 `wind5516/ecommerce-shop` 改造，目标不是只做一个聊天 Demo，而是让 Agent 在真实订单、物流、售后政策和人工审批流程中工作。

## 当前能力

- FastAPI 商城后端
- SQLAlchemy 数据模型
- Alembic 数据库迁移
- 商品、购物车、订单、支付、售后工单
- 审计日志与订单幂等键
- Redis 缓存与登录限流
- Celery 订单超时任务
- 售后政策知识库与带引用检索
- BM25 + 向量 + RRF Hybrid Search
- LangGraph 售后 Agent
- DeepSeek/OpenAI 兼容模型驱动工具选择
- 订单、物流、售后政策三个只读工具
- 结构化 Agent 输出与人工审批标记
- Agent 执行提案与管理员确认执行
- 多轮售后上下文与超长会话压缩
- X-Request-ID 与 Agent 节点耗时记录
- 30 条案例的三方案评测

## 架构

详细设计见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

```text
顾客 / 管理员
     |
     v
FastAPI API
  |-- 商城业务：商品 / 购物车 / 订单 / 支付 / 售后
  |-- 审计与幂等
  |-- X-Request-ID
  |
  +--> PostgreSQL
  +--> Redis
  +--> Celery Worker

售后工单
  |
  v
LangGraph Agent
  parse_intent
      -> get_order
      -> get_logistics / check_return_policy
      -> generate
      -> verify
      -> human approval when needed
  |
  +--> AgentRun / steps / tool results / citations
```

## 技术栈

- Python 3.12
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Celery
- LangGraph
- pytest

## 本地运行（SQLite，快速演示）

```powershell
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
.venv/Scripts/python.exe run.py
```

访问：

- 商城前台：http://127.0.0.1:8000/static/index.html
- 管理后台：http://127.0.0.1:8000/static/admin.html
- 售后运营工作台：http://127.0.0.1:8000/
- 轻量 Agent 演示页：http://127.0.0.1:8000/static/agent.html
- Swagger：http://127.0.0.1:8000/docs

演示账号：

- 管理员：`admin / admin123`
- 用户：`demo / 123456`

## Docker Compose

```bash
docker compose up --build
```

Compose 会启动 PostgreSQL、Redis、API 和 Celery worker，并在 API 启动前运行 `alembic upgrade head`。

Dockerfile 支持 `PYTHON_IMAGE` build arg，默认使用官方 `python:3.12-slim`。当前 Compose 为受限网络环境配置了可用镜像源，可按需替换。

已完成的实机验证：

- PostgreSQL 16 + pgvector 正常运行
- Alembic 迁移到 `13b62b3fc633`
- pgvector 向量维度为 128
- Redis 缓存与限流正常
- Celery worker 注册并执行 `orders.expire_pending`
- 订单取消后库存恢复
- 审计日志 request_id 可贯穿 API 和异步任务
- DeepSeek `deepseek-flash` 已完成真实规划和摘要调用
- 模型可自主选择订单、物流和政策工具
- 执行提案必须经过管理员批准

## 模型配置

项目使用 OpenAI 兼容 `/chat/completions` 协议。当前配置示例：

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-flash
```

密钥只放在本地 `.env`，该文件已加入 `.gitignore`。没有 Key 时，系统自动退回规则 Agent。

## Agent 使用

1. 登录用户并创建/支付一笔订单。
2. 创建售后工单。
3. 调用：

```http
POST /api/agent-runs/tickets/{ticket_id}
{
  "message": "商品破损，想申请退款"
}
```

4. 查询运行记录：

```http
GET /api/agent-runs/{run_id}
```

流式运行：

```http
POST /api/agent-runs/tickets/{ticket_id}/stream
Content-Type: application/json

{"message": "商品破损，想申请退款"}
```

流式接口使用 SSE，依次推送 `run_started`、每个 LangGraph 节点和最终结构化结果。

输出包含：

- intent
- summary
- evidence
- missing_information
- recommended_action
- requires_human_approval
- confidence
- steps 与 tool_results
- decision_source（llm / rules）

高风险退款、退货、换货和破损诉求只生成处理建议，不直接执行退款。

模型生成结果后，可以创建执行提案：

```http
POST /api/agent-runs/{run_id}/proposals
```

管理员批准后才执行：

```http
POST /api/proposals/{proposal_id}/approve
```

## 评测

检索评测：

```powershell
.venv/Scripts/python.exe eval/run_retrieval_eval.py
```

Agent 三方案评测：

```powershell
.venv/Scripts/python.exe eval/run_agent_eval.py
```

报告位于：

- `eval/reports/retrieval_latest.md`
- `eval/reports/agent_latest.md`
- `eval/reports/agent_latest.json`

当前 30 条案例结果：

- 意图准确率：1.0
- 人工审批准确率：1.0
- 政策引用覆盖率：完整 Agent 1.0
- 无证据政策结论率：完整 Agent 0.0
- 工具调用正确率：完整 Agent 1.0
- 工具成功率：1.0
- 平均成本：当前未配置真实模型价格，报告为 0；可通过 `MODEL_COST_PER_1K_TOKENS` 设置估算单价

这些是离线规则/确定性检索的可复现结果，不代表真实生产模型效果。

## 测试

```powershell
.venv/Scripts/python.exe -m pytest -q
```

当前共 12 条测试，覆盖售后闭环、越权、幂等、审计、订单超时、Hybrid 检索、Agent 审批、执行提案、上下文压缩、SSE、数据库 schema 检查和模型兼容接口。

## 已知限制

- SQLite 使用 JSON/hash Embedding 作为离线回退；PostgreSQL 使用 pgvector + Hybrid RRF。
- 当前 Embedding 仍不是 BGE/e5 语义模型，检索行为依赖向量与 BM25 融合。
- Agent 前端目前是演示页，尚未做成完整的生产级客服工作台。

## 演示材料

2 分钟录屏脚本见 [docs/DEMO.md](docs/DEMO.md)。

成片：[docs/demo/ShopAgent-Demo.mp4](docs/demo/ShopAgent-Demo.mp4)。

自动录制：

```powershell
uv pip install --python .venv/Scripts/python.exe -r requirements-demo.txt
.venv/Scripts/python.exe -m playwright install ffmpeg
.venv/Scripts/python.exe scripts/record_demo.py --full
```

录制脚本使用本机 Chrome，输出 WebM 到 `docs/demo/`。

## 来源说明

底座来自开源项目 `wind5516/ecommerce-shop`，当前仓库已完成大量结构改造和功能新增。使用和发布前请自行核对原项目许可证。
