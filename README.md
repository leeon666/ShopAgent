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
- LangGraph 售后 Agent
- 订单、物流、售后政策三个只读工具
- 结构化 Agent 输出与人工审批标记
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
- Agent 演示页：http://127.0.0.1:8000/static/agent.html
- Swagger：http://127.0.0.1:8000/docs

演示账号：

- 管理员：`admin / admin123`
- 用户：`demo / 123456`

## Docker Compose

```bash
docker compose up --build
```

Compose 会启动 PostgreSQL、Redis、API 和 Celery worker，并在 API 启动前运行 `alembic upgrade head`。

当前开发机受 WSL/Docker Desktop 限制，Compose 还没有完成实机启动验证。

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

高风险退款、退货、换货和破损诉求只生成处理建议，不直接执行退款。

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
- 工具成功率：1.0

这些是离线规则/确定性检索的可复现结果，不代表真实生产模型效果。

## 测试

```powershell
.venv/Scripts/python.exe -m pytest -q
```

当前共 7 条测试，覆盖售后闭环、越权、幂等、审计、订单超时、知识检索和 Agent 审批。

## 已知限制

- PostgreSQL + pgvector 尚未完成真实容器验证。
- Redis/Celery 尚未完成真实 worker 验证。
- 真实 OpenAI 兼容模型接口需要配置 `OPENAI_API_KEY` 后再验证。
- 当前知识检索有 SQLite/JSON 离线实现，后续切换 pgvector。
- Agent 前端目前是演示页，尚未做成完整的生产级客服工作台。

## 演示材料

2 分钟录屏脚本见 [docs/DEMO.md](docs/DEMO.md)。

## 来源说明

底座来自开源项目 `wind5516/ecommerce-shop`，当前仓库已完成大量结构改造和功能新增。使用和发布前请自行核对原项目许可证。
