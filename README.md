# ShopAgent v2

ShopAgent v2 是一个可运行、可评测、可追溯的商城售后系统。它不是独立的聊天 Demo：

> 订单、库存、工单、政策检索、DeepSeek 工具调用、退款提案和人工审批共用同一套 PostgreSQL 业务数据。

项目基于高星开源模板 [vstorm-co/full-stack-ai-agent-template](https://github.com/vstorm-co/full-stack-ai-agent-template) 生成，未从零手写 FastAPI、JWT、LangGraph、RAG、Celery、Next.js 和 Docker 基础设施。上游版本、许可证与基准 commit 记录在 [UPSTREAM.md](UPSTREAM.md)。

## 为什么需要 Agent

普通售后菜单适合“用户已经明确知道自己要选退款、换货还是查物流”的情况。但真实售后请求经常同时包含订单、商品、时间、证据和政策条件，例如：

> “订单里的台灯到货有裂纹，马克杯没问题，我想只退台灯。已经传了照片，运费谁承担？”

这句话需要先查订单明细、确认订单状态、查询物流、检索退款与运费政策、判断是否缺少证据，再决定建议部分退款、退货或转人工。固定表单只能要求用户自己拆解问题；Agent 的价值是把这套多工具、多证据的研判过程自动完成。

Agent 仍然不是最终决策者：

- 只读工具直接查询，但严格绑定当前登录用户。
- 高风险退款、退货、换货和拒绝只创建 `ActionProposal`。
- 提案必须由管理员批准或拒绝。
- 批准后才由确定性业务服务修改订单和工单状态。
- 模型不能直接修改支付渠道，也不能声称退款已经到账。

## 当前能力

| 能力 | 实现 |
|---|---|
| 业务数据 | 商品、订单、订单明细、售后工单、留言、退款提案、审计事件 |
| 状态机 | 订单和工单使用显式合法迁移，拒绝跳状态 |
| 并发一致性 | 下单时按 UUID 顺序锁定商品行，事务内扣库存 |
| 认证授权 | JWT、API Key、管理员权限、用户数据隔离 |
| Agent | DeepSeek + LangGraph ReAct，最多 12 步 |
| Agent 工具 | 查订单、物流、工单、退款资格、政策、创建退款提案 |
| RAG | pgvector + `BAAI/bge-small-zh-v1.5` 512 维本地语义向量 + BM25 + RRF |
| 人工审批 | pending / approved / rejected，审批后工单和订单确定性变更 |
| 异步基础设施 | Redis、Celery worker、Celery beat、Flower |
| 可观测性 | `request_id`、每条 Agent 运行、工具步骤、耗时、Token、状态、停止原因 |
| 评测 | 30 条售后案例，对比纯 LLM、LLM+RAG、完整工具 Agent |
| 前端 | Next.js 15 售后工作台、实时聊天、业务对象、政策和审批 |

## 架构

```text
Browser / Next.js workbench
        |
        | HTTP + WebSocket
        v
FastAPI API + AgentSession
        |
        +--> JWT / RBAC ------------> PostgreSQL
        |                              |-- products / orders / tickets
        |                              |-- proposals / audit / agent traces
        |                              |-- pgvector policy tables
        |
        +--> LangGraph ReAct
               |-- get_order
               |-- get_logistics
               |-- get_after_sales_ticket
               |-- check_refund_eligibility
               |-- search_after_sales_policy
               +-- create_refund_proposal
        |
        +--> Redis / Celery / Flower
```

更详细的设计、关键取舍和面试讲解见 [docs/SHOPAGENT.md](docs/SHOPAGENT.md)。

真实页面录制：[两分钟 ShopAgent 演示](docs/demo/shopagent-demo.mp4)，
关键页面截图：[售后工作台](docs/demo/shopagent-workbench.png)。

## Windows 一键启动

前置条件：Docker Desktop 正常运行。项目不再依赖 `make`。

```powershell
.\bootstrap.ps1
```

脚本会构建并启动全部服务、执行 Alembic、创建演示数据并同步政策知识库。需要手动分步排查时使用：

```powershell
docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml exec -T app alembic upgrade head
docker compose -f docker-compose.dev.yml exec -T app shopagent_v2 cmd seed-shop
docker compose -f docker-compose.dev.yml exec -T app shopagent_v2 cmd rag-ingest /app/data/after_sales_policies --collection after_sales_policies --recursive
```

访问：

- 售后工作台：<http://localhost:3000/shop>
- API 文档：<http://localhost:8000/docs>
- Flower：<http://localhost:5555>
- Prometheus 指标：<http://localhost:8000/metrics>

本地演示账号：

| 角色 | 邮箱 | 密码 |
|---|---|---|
| 管理员 | `admin@shopagent.example.com` | `ShopAgent123!` |
| 客户 | `demo@shopagent.example.com` | `ShopAgent123!` |

这些账号只用于本地演示。`backend/.env`、真实模型 Key、JWT Secret 均被 Git 忽略，不应提交。

## 模型配置

复制 `backend/.env.example` 为 `backend/.env`，至少配置：

```dotenv
OPENAI_API_KEY=your-deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-flash
AI_TEMPERATURE=0.2

EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
RAG_HYBRID_SEARCH=true
```

DeepSeek 用于规划、工具选择和结论生成。Embedding 使用 FastEmbed/ONNX 在本地生成，不依赖 DeepSeek 提供 Embedding 接口。

## 演示流程

1. 使用客户账号登录，进入 `/shop`。
2. 选择带破损工单的订单，点击“让 Agent 研判”。
3. 观察右侧聊天中的工具调用、政策检索和带 `[n]` 引用的结构化答案。
4. 若 Agent 创建退款提案，切换管理员账号，在“待审批提案”中批准或拒绝。
5. 批准后退款工单变为 `approved`，关联订单进入 `refund_pending`。
6. Celery beat 每 15 秒扫描已批准退款；worker 幂等执行后订单变为 `refunded`、工单变为 `resolved`。
7. 在数据库中查看 `shop_agent_runs`、`shop_agent_steps`、`shop_audit_events`。

## 测试

```powershell
cd backend
uv run pytest -q
uv run ruff check app tests

cd ..\frontend
npm install
npm run lint
npm run type-check
npm run build
```

`pytest` 默认不会执行会 `downgrade base` 的迁移测试，避免清空本地演示库。迁移测试必须显式开启，并应指向独立测试数据库：

```powershell
$env:POSTGRES_DB="shopagent_v2_test"
$env:RUN_DESTRUCTIVE_MIGRATION_TESTS="1"
uv run pytest -q tests/test_migrations.py
```

测试基础设施已覆盖模板原有能力，并新增：

- 订单和工单状态机
- 库存不足
- 订单归属隔离
- 未支付订单不能申请售后
- 退款提案证据要求
- 退款金额不能超过订单实付
- 重复 pending 提案
- 管理员批准后的工单/订单变更
- 30 条评测集唯一性和结构化结果解析

## 评测

```powershell
# 只跑完整 Agent
docker compose -f docker-compose.dev.yml exec -T app `
  shopagent_v2 cmd eval-after-sales --mode full_agent

# 三套方案全部运行
docker compose -f docker-compose.dev.yml exec -T app `
  shopagent_v2 cmd eval-after-sales `
  --mode llm_only --mode llm_rag --mode full_agent
```

评测输出写入 `data/evaluation/results/*.json`，包括：

- 结构化输出率
- 意图准确率
- 建议动作准确率
- 政策引用覆盖率
- 无证据结论比例
- 正确转人工率
- 工具选择正确率
- 工具成功率
- P50 / P95 延迟
- 平均输入 / 输出 Token

最近一次 30 条三方案评测（`deepseek-flash`，并发 3）：

| 指标 | 纯 LLM | LLM + RAG | 完整 Agent |
|---|---:|---:|---:|
| 结构化输出率 | 100% | 100% | 100% |
| 意图准确率 | 76.67% | 86.67% | 76.67% |
| 建议动作准确率 | 66.67% | 70.00% | 66.67% |
| 政策引用覆盖率 | 0% | 100% | 100% |
| 无证据结论比例 | 12.00% | 0% | 0% |
| 正确转人工率 | 75.00% | 80.00% | 100% |
| 应选工具命中率 | — | — | 98.21% |
| 工具成功率 | — | 100% | 98.11% |
| P50 延迟 | 4.13s | 8.89s | 11.20s |
| P95 延迟 | 10.05s | 18.29s | 15.30s |

这些结果不是“越高越好”的宣传数字：完整 Agent 的工具更多，P50 延迟高于纯 LLM，但引用覆盖、无证据率和转人工率明显更可信。原始输出保存在 [data/evaluation/results/after_sales_20261115T132926Z.json](data/evaluation/results/after_sales_20261115T132926Z.json)。

## 当前限制

- 支付是模拟支付，不连接真实支付渠道。
- 物流工具使用确定性模拟节点，并在响应中明确标记 `source: simulated`。
- 售后图片只记录为文字证据，没有实现图片内容识别或对象存储审核。
- 批准后的退款由 Celery 完成状态闭环，但资金执行仍为模拟，不连接真实支付渠道。
- 当前评测是离线可复现基线，不等于线上真实客服的成功率。

## 上游与许可

- Upstream: <https://github.com/vstorm-co/full-stack-ai-agent-template>
- Selected commit: `475f799f7df02738f804fa350f2de244d7331a94`
- License: MIT
- 来源说明：[UPSTREAM.md](UPSTREAM.md)

