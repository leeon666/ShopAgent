# ShopAgent v2 设计说明

## 1. 项目定位

ShopAgent 是“商城订单与售后系统 + 售后 Agent”。两部分运行在同一套业务数据上，避免聊天 Demo 与真实业务脱节。

一个可信的售后 Agent 必须回答五个问题：

1. 背景：用户在什么订单、什么商品、什么时间提出什么诉求？
2. 证据：订单、物流、工单和政策分别说明了什么？
3. 取舍：为什么建议退款、退货、换货、拒绝或转人工？
4. 异常：工具超时、证据缺失、数据冲突时如何降级？
5. 结果：是否创建提案？是否通过人工审批？是否有可追溯记录？

README 的演示流程就是围绕这条证据链设计。

## 2. Agent 与普通 Workflow 的区别

普通工作流适合步骤固定、输入结构固定的业务。售后对话则存在：

- 用户可能只给订单号，也可能只描述商品；
- 有些人先问政策，再提供订单；
- 同一句话可能包含物流、破损和退款多个诉求；
- 需要根据工具结果决定下一步调用什么；
- 需要判断什么时候停止、什么时候转人工。

LangGraph ReAct 循环让模型依次决定：直接回答、调用哪个工具、拿到结果后是否继续。固定表单仍然保留给确定性操作，例如支付；自然语言 Agent 负责难以预先枚举的研判过程。

## 3. 数据模型

| 表 | 作用 |
|---|---|
| `shop_products` | 商品、价格、库存 |
| `shop_orders` | 订单主体、状态、实付金额 |
| `shop_order_items` | 商品快照与数量 |
| `shop_after_sales_tickets` | 售后类型、原因、状态、处理结果 |
| `shop_after_sales_messages` | 工单多轮留言 |
| `shop_action_proposals` | Agent 建议的高风险动作与证据 |
| `shop_agent_runs` | 每次 Agent 运行的模型、Token、延迟、停止原因 |
| `shop_agent_steps` | 工具调用、状态、参数、结果和耗时 |
| `shop_audit_events` | 下单、支付、工单、消息、提案和审批审计 |

订单状态和工单状态在白名单中迁移。例如：

```text
order: pending -> paid -> shipped -> completed -> refund_pending -> refunded
ticket: pending -> waiting_approval -> approved -> resolved
```

`pending` 不能直接跳到 `approved`，`refunded` 和 `cancelled` 也不能再次修改。

## 4. 权限隔离

工具不信任模型给出的 `user_id`。运行上下文由已认证 WebSocket 会话注入：

```text
AgentSession(user.id)
  -> configurable.user_id
  -> tool reads this value
  -> SQL query always includes user_id
```

因此即使模型被提示“查询另一个用户的订单”，SQL 仍只能命中当前用户的数据。API 也使用同样的归属条件。

## 5. RAG

政策文档位于 `data/after_sales_policies/`，包含退款、退换货、物流、证据、Agent 操作边界和工单状态机。

入库链路：

```text
Markdown
  -> parser
  -> recursive chunks
  -> bge-small-zh 512-d embeddings
  -> PostgreSQL pgvector
```

检索链路：

```text
query
  -> pgvector top-k
  -> BM25 top-k
  -> RRF fusion
  -> source filename + chunk metadata
  -> Agent citation [1], [2]
```

`RAG_HYBRID_SEARCH=true` 控制 BM25 + 向量融合。单个 collection 使用 `after_sales_policies`，避免和通用文档混在一起。

## 6. 高风险动作

Agent 的写工具只有 `create_refund_proposal`，没有直接退款工具。

```text
Agent
  -> create proposal: pending
  -> admin approve/reject
  -> deterministic service updates ticket/order
  -> audit event
```

提案金额不能超过订单实付，高风险动作必须带证据，同一工单不能同时存在两个 pending 提案。

## 7. 失败与停止条件

- LangGraph `recursion_limit=12`，避免无限工具循环。
- 每个业务工具设置 12 秒超时。
- 工具返回结构化错误而不是让模型猜数据。
- 工具结果截断到 12,000 字符。
- 用户取消时 Agent run 标记为 `cancelled`。
- 模型异常时 Agent run 标记为 `failed`，保留错误与工具步骤。
- 证据不足时建议补充材料或人工复核。

## 8. 面试讲解模板

可以先讲问题，不要先背名词：

> 售后请求不是简单文本分类。一个订单可能同时涉及商品明细、物流、退款资格、政策引用和人工审批。我基于高星模板保留认证、LangGraph、RAG、Celery 和前端基础设施，把售后领域模型接进去。Agent 只能调用用户权限范围内的只读工具去收集证据；退款等高风险动作只能生成提案，管理员批准后由确定性服务修改订单和工单。每次运行会记录 request_id、工具耗时、Token、错误和停止原因，30 条案例可以重复比较纯 LLM、LLM+RAG 和完整 Agent。

常见追问：

- 为什么不用下拉框？固定选项适合确定性操作，但无法覆盖自然语言中的多意图、缺信息和证据判断。
- 为什么不让 Agent 直接退款？模型输出不是资金指令，必须经过提案和审批。
- 为什么需要 RAG？退款期限、运费责任和升级规则需要版本化来源，不能依赖模型记忆。
- 多 Agent 在哪里？当前没有为了简历硬凑 Multi-Agent。单 Agent 工具循环足以完成当前闭环；未来只有在任务专业化和并行收益可测时才拆分。
- 如何证明有效？运行 `eval-after-sales`，比较三套方案的结构化率、动作准确率、引用覆盖、转人工率、工具成功率和 P95 延迟。

## 9. 后续路线

- 将物流模拟替换为真实承运商适配器。
- 售后图片接入对象存储和视觉证据审核。
- 将批准后的 `refund_pending` 交给 Celery worker 执行并写入最终结果。
- 加入用户 30 天退款次数查询，完成全部高风险规则。
- 增加前端 Agent Trace 瀑布图。
- 扩充到 100+ 案例并建立版本化回归门禁。

