# ShopAgent 架构说明

## 1. 总体架构

```mermaid
flowchart TD
    U[顾客 / 客服 / 管理员] --> API[FastAPI API]
    API --> AUTH[JWT 鉴权与 RBAC]
    API --> SHOP[商品 / 购物车 / 订单 / 支付]
    API --> AS[售后工单 / 留言 / 审批]
    API --> AGENT[LangGraph 售后 Agent]

    SHOP --> DB[(PostgreSQL)]
    AS --> DB
    AGENT --> DB
    AGENT --> RAG[知识检索]
    RAG --> PGV[(pgvector)]
    RAG -. SQLite 离线回退 .-> JSON[(JSON Embedding)]

    API --> REDIS[(Redis)]
    API --> CELERY[Celery Worker]
    CELERY --> DB

    API --> OBS[X-Request-ID / AuditLog / AgentRun Trace]
    AGENT --> OBS
```

## 2. Agent 工作流

```mermaid
flowchart LR
    START --> PARSE[parse_intent]
    PARSE --> ORDER[get_order]
    ORDER --> ROUTE{intent}
    ROUTE -->|logistics| LOGISTICS[get_logistics]
    ROUTE -->|refund/return/exchange/damage| POLICY[check_return_policy]
    ROUTE -->|other| GENERATE[generate]
    LOGISTICS --> GENERATE
    POLICY --> GENERATE
    GENERATE --> VERIFY[verify]
    VERIFY --> END[completed / human_approval_required / insufficient_evidence]
    ROUTE -->|max steps or token budget| STOP[stop]
    STOP --> END
```

## 3. 为什么这样设计

### Agent 不是自由聊天

Agent 的输出必须符合固定结构：

- intent
- summary
- evidence
- missing_information
- recommended_action
- requires_human_approval
- confidence

这样前端、审批流程和评测都能消费同一份结果。

### 工具只读

订单、物流和政策检索工具都是只读的。高风险退款、退货、换货和赔付只生成建议，不直接执行。

### 确定性代码优先

权限、订单状态、库存扣减、金额和退款审批条件都放在后端代码中。模型只负责自然语言理解和草稿生成。

### 离线也能运行

- 没有模型 Key 时使用规则引擎兜底。
- 没有 Redis 时使用 fakeredis。
- 没有 Celery broker 时使用 eager 模式。
- SQLite 下使用 JSON Embedding，PostgreSQL 下切换 pgvector。

## 4. 可观测性

```mermaid
sequenceDiagram
    participant C as Client
    participant API as FastAPI
    participant A as Agent
    participant T as Tools
    participant DB as AgentRun

    C->>API: X-Request-ID
    API->>A: request_id + ticket/message
    A->>T: get_order / get_logistics / check_policy
    T-->>A: data / latency / error / attempts
    A->>A: node steps + duration
    A->>DB: output + steps + tokens + stop_reason
    A-->>API: structured result
    API-->>C: X-Request-ID + result
```

可追踪信息：

- 每个 HTTP 请求的 request_id
- 每个 Agent 节点的耗时
- 每次工具调用状态、重试次数和延迟
- 模型名与 Prompt 版本
- Token 和总延迟
- 停止原因和错误

## 5. 评测设计

三套方案：

1. 纯规则基线
2. 规则 + RAG
3. 规则 + RAG + 工具 + 校验

当前 30 条案例用于验证：

- 意图识别
- 人工审批判断
- 政策引用覆盖
- 无证据结论
- 工具成功率
- P50/P95 延迟
- 平均 Token

评测结果写入 `eval/reports/agent_latest.md` 和 `eval/reports/agent_latest.json`。
