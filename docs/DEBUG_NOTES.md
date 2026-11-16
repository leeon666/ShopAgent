# ShopAgent v2 调试备忘

## 环境

- Windows PowerShell，无 `make`。
- 后端依赖通过 `uv` 管理。
- 前端依赖通过 `npm` 管理。
- 数据库镜像必须使用 `pgvector/pgvector:pg16`，`postgres:16-alpine` 不含 `vector` 扩展。
- 项目数据目录通过 `./data:/app/data` 挂载到容器，评测结果和政策文档都在这里。

## 常用命令

```powershell
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml logs app --tail 150
docker compose -f docker-compose.dev.yml exec -T app alembic current
docker compose -f docker-compose.dev.yml exec -T db psql -U postgres -d shopagent_v2
docker compose -f docker-compose.dev.yml exec -T app shopagent_v2 cmd seed-shop
```

## 已修复问题

### Docker Hub 拉取超时

首次构建 `python:3.12-slim` 时 Docker Hub token 请求超时。重新执行 `docker pull python:3.12-slim` 后恢复，不是代码问题。

### RAG 表建成 3072 维

模板 CLI 使用 `RAGSettings()` 重建配置，没有读取应用 settings，导致本地 512 维模型写入 3072 维表。

修复：`get_rag_services()` 改用 `app_settings.rag`。如果已经建错表，需要删除 `rag_after_sales_policies` 后重新 ingest。

### HNSW 2000 维限制

错误表是 3072 维，pgvector HNSW 索引拒绝创建。修正为 512 维后正常。

### 提案响应 Pydantic 校验失败

`ProposalRead` 继承了普通 `TimestampSchema`，没有 `from_attributes=True`，无法直接校验 SQLAlchemy 对象。

修复：改为 `class ProposalRead(BaseSchema, TimestampSchema)`。

### Agent Trace 一直处于 running

原顺序是发送 WebSocket `complete` 后才写 trace。客户端收到 complete 后立即断开，可能中断后续写入。

修复：先 `finish_agent_run`，再发送 `complete`。用户停止时也会写 `cancelled`。

### 登录接口 429

模板对 `/auth/login` 有每 IP 5 次/15 分钟限制。本地反复验证时可用：

```powershell
docker compose -f docker-compose.dev.yml exec -T redis `
  valkey-cli DEL "rl:auth:ip:172.18.0.1"
```

只用于本地开发，不要在生产环境通过清 Redis 绕过限流。

### 全量 pytest 后账号和订单消失

模板的 `tests/test_migrations.py` 会在检测到 live PostgreSQL 时执行
`alembic downgrade base`，从而清空正在使用的开发数据库。

修复：破坏性迁移测试改为显式开关 `RUN_DESTRUCTIVE_MIGRATION_TESTS=1`，
默认跳过。运行迁移测试时必须使用独立的 `shopagent_v2_test` 数据库。

### 客户登录后误入通用聊天页

现象：客户使用 demo 账号登录后进入通用 `/chat`，看不到订单和售后单，
容易误以为客户必须自己编写复杂的售后 Prompt。

根因：

1. 登录成功后，普通用户被统一跳转到 `/chat`。
2. 中文模式下，`ChatEmptyState` 始终使用通用中文提示词，覆盖了售后工作台传入的提示词。
3. 无售后单的订单仍会回退显示其他订单的售后单和提案。
4. 空聊天容器初始化时会自动滚动到底部，导致小屏面板标题被裁掉。

修复：

1. 普通客户登录后进入 `/shop`，管理员进入 `/dashboard`。
2. 顶部导航、移动底栏和工作台文案都增加售后工作台入口及操作说明。
3. 页面级提示词优先于通用默认提示词。
4. 提案严格按当前订单关联的售后单过滤，不再串单。
5. 空聊天时不执行自动滚动。
6. 移动端优先展示订单和工单，再展示统计卡片。

验证：

```text
客户登录 -> http://localhost:3000/shop
可见 3 个 demo 订单
可见订单明细、关联工单、提案和 Agent Trace
无需手写 Prompt，点击“让 Agent 研判”即可自动带入订单与工单上下文
桌面和 390px 手机宽度均可见售后工作台导航
```

前端检查通过：ESLint、TypeScript、34 个 Vitest 测试和 Next.js 生产构建。

## 已实证的闭环

1. DeepSeek `deepseek-flash` 可访问，并返回 Token usage。
2. Agent 通过 WebSocket 调用 `get_order`、`get_logistics`、`check_refund_eligibility`、`search_after_sales_policy`。
3. 政策答案包含 `[n]` 引用。
4. `shop_agent_runs.status=completed`，Token 与延迟有记录。
5. `shop_agent_steps` 记录工具成功状态和耗时。
6. 退款提案创建后为 pending。
7. 管理员批准后提案 approved、工单 approved、订单 refund_pending。
8. Celery beat 每 15 秒扫描已批准退款，worker 将订单变为 refunded、工单变为 resolved。
9. `shop_audit_events` 记录下单、支付、工单、提案、审批和退款完成。

## 安全提醒

- 不要把真实 `OPENAI_API_KEY`、GitHub PAT 或 JWT Secret 写进 README、提交、截图或日志。
- 曾经在聊天中暴露过的 Key 和 PAT 应在对应平台轮换。
- `backend/.env` 与前端 `.env.local` 必须保持未跟踪。

