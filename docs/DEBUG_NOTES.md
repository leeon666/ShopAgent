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

### 中文界面仍混有英文

现象：切换到简体中文后，设置、初始化、后台管理、知识库、聊天控件和部分隐藏页面
仍直接显示模板中的英文文案。

根因：项目模板最初只把导航和少量页面接入了 `next-intl`，大量组件使用了硬编码英文；
同时语言列表仍保留波兰语。

修复：

1. 语言列表收敛为 `zh` 和 `en`，删除 `messages/pl.json` 及相关波兰语计划文案。
2. 设置页、引导页、后台管理、RAG、聊天、认证、错误页、演示页和公开营销页
   对用户可见文案统一增加中文分支。
3. 日期、相对时间、密码强度、命令面板、Cookie 提示、工具调用状态和常见 Toast
   改为按当前语言显示。
4. 中文模式下保留 RAG、API、CSV、JSON、Stripe 等标准技术名称。
5. 增加语言配置回归测试，防止波兰语再次被加入。

验证命令：

```powershell
cd frontend
npm run lint -- --quiet
npm run type-check
npm run test:run
npm run build
```

构建结果只保留 `zh` 和 `en` 两套静态路由。

### 知识库检索误查 rag_documents 元数据表

现象：Agent 调用 `search_documents` 时 PostgreSQL 报错
`column "content" does not exist`，实际 SQL 为 `FROM rag_documents`。

根因：旧向量表命名规则是 `rag_<collection>`。默认集合 `documents` 被映射为
`rag_documents`，与保存上传文件元数据的业务表同名，检索因此查到了错误表。
集合扫描还会把 `rag_documents` 元数据表误认为向量集合。

修复：

1. 向量表改用独立前缀 `rag_collection_`。
2. 首次访问时自动识别带 `embedding` 字段的旧表，并将它们迁移到新前缀。
3. 集合扫描只识别 `rag_collection_%`，不会再暴露 `rag_documents`。
4. 默认集合不存在时，自动在现有集合中执行跨集合检索。
5. 知识库工具结果和空结果提示改为中文。
6. `rag/status/stream` 的依赖注入改为使用 lifespan 生命周期中的共享 Redis 客户端，
   修复 SSE 请求 500。

迁移后的本地表：

```text
rag_collection_after_sales_policies
rag_documents                  # 仅保存上传文件元数据，不再是向量集合
```

验证：

- `list_collections()` 返回 `['after_sales_policies']`
- 查询“破损商品需要提供什么证据”可命中 3 条政策
- 默认 collection 缺失时会回退到现有集合
- `/api/v1/rag/status/stream` 返回 `200 text/event-stream`
- 聊天页重新执行“总结知识库”成功，没有再出现 SQL 错误
- 工具标题显示“当前日期与时间”“检索文档”，不再显示英文 Running 文案

### Agent 聊天内容撑高整个售后工作台

现象：右侧 Agent 研判台内容变长后，三列网格跟着持续变高，导致左侧订单列和中间
订单详情列下方出现大面积空白。

根因：桌面端网格只有最小高度，没有最大高度；聊天容器虽然支持内部滚动，但父级
`Card` 会被消息内容自然撑开，`flex-1` 没有可用高度约束。

修复：

1. 桌面端三列网格使用 `clamp(560px, calc(100vh - 18rem), 760px)` 固定可用高度。
2. 左侧、中间和右侧卡片统一填满网格行高。
3. 三列内容区改为 `min-h-0 flex-1 overflow-y-auto`，由卡片内部滚动。
4. 手机端三块内容保持纵向排列：订单 580px、详情 580px、Agent 640px。

验证：

```text
桌面：三列高度均为 712px
注入 4000px 长内容后：
  Agent 面板仍为 712px
  聊天滚动区 clientHeight=501px
  聊天内容 scrollHeight=4501px
  页面主区域 scrollHeight 保持 991px，不随聊天内容增长
手机：Agent 面板保持 640px
```

### 管理员能看到待审批数量但看不到提案

现象：管理员账号登录售后工作台后，“待审批提案”统计为 1，但左侧订单为 0，
中间只显示“暂无订单数据”，没有提案审批入口。

根因：

1. 管理员工作台左侧仍只加载管理员自己的订单。
2. 提案列表被嵌套在“当前选中订单”的详情中；没有订单时整个提案区域不会渲染。
3. 管理员提案接口只返回 `ticket_id` 和 `user_id`，缺少工单号、订单号和客户邮箱，
   前端无法展示可核验的审批上下文。

修复：

1. 管理员左侧改为全站“待审批队列”，不再依赖管理员个人订单。
2. 中间改为独立提案审查面板，展示客户、工单、订单、类型、金额和客户描述。
3. 后端批量补充提案关联的 `ticket_no`、`order_no`、`user_email` 等上下文。
4. 批准和拒绝按钮移到提案顶部信息卡下方，进入页面即可看到。
5. 普通客户仍保持“订单 -> 售后单 -> Agent 研判 -> 提案”的原流程。

验证：

```text
管理员登录 -> /shop
待审批提案 = 1
左侧显示 AP-20261115135526-C28C
关联工单 AS-20261115135417-C9F9
客户 demo@shopagent.example.com
退款金额 269.00
批准/拒绝按钮均在首屏可见
不再显示“暂无订单数据”
```

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
