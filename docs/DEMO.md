# 2 分钟演示脚本

## 录制前准备

```powershell
cd work/ecommerce-shop
.venv/Scripts/python.exe run.py
```

打开：

- 商城前台：http://127.0.0.1:8000/static/index.html
- Agent 演示页：http://127.0.0.1:8000/static/agent.html
- Swagger：http://127.0.0.1:8000/docs

## 0:00-0:20 项目定位

口述：

> 这是 ShopAgent，一个商城后端加智能售后 Agent 的项目。它不是单独的聊天框，Agent 会调用真实订单、物流和售后政策工具，并把高风险退款建议交给人工审批。

## 0:20-0:45 一键准备演示数据

操作：

1. 打开 Agent 演示页。
2. 点击“一键准备演示数据”。
3. 展示自动完成：
   - 用户登录
   - 加入商品
   - 创建订单
   - 模拟支付
   - 创建售后工单
   - 导入售后政策

口述：

> 这里不是硬编码答案，背后是真实的订单、支付和售后工单数据。

## 0:45-1:20 运行 Agent

操作：

1. 输入“商品破损，想申请退款”。
2. 点击“运行流式 Agent”。
3. 展示节点流：
   - parse_intent
   - load_order
   - retrieve_policy
   - generate
   - verify

口述：

> Agent 先识别售后意图，再查询订单和政策，最后做证据校验。整个过程通过 SSE 实时显示节点和耗时。

## 1:20-1:45 展示结构化结果

展示：

- intent: damage
- evidence: 政策引用和订单证据
- missing_information
- recommended_action
- requires_human_approval: true
- confidence
- request_id
- 总延迟

口述：

> 高风险退款只生成建议，不会直接执行；每一步都能通过 request_id 和 AgentRun Trace 追踪。

## 1:45-2:00 展示工程与评测

操作：

1. 打开 Swagger，展示售后和 Agent 接口。
2. 打开 `eval/reports/agent_latest.md`。

口述：

> 项目还包括审计、幂等、Redis 限流、Celery 超时任务、Alembic 迁移和 30 条案例评测。当前完整 Agent 的政策引用覆盖率为 1.0，工具成功率为 1.0，无证据政策结论率为 0。

## 录制注意

- 录制前清空浏览器控制台报错。
- 不要展示真实 API Key、密码或 Cookie。
- 如果模型 Key 未配置，明确说当前使用规则引擎离线兜底。
- 如果 Docker 未启动，说明当前用 SQLite 演示，PostgreSQL + pgvector 代码路径已完成。
