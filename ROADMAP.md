# 开发路线

本项目基于 `wind5516/ecommerce-shop` 改动，目标是做成“商城后端 + 智能售后 Agent”的完整作品。

目标与完成标准见 [GOALS.md](./GOALS.md)，后续所有开发围绕这份目标展开。

## 当前进度

- [x] 克隆并跑通上游项目
- [x] 建立独立开发分支 `dev`
- [x] 增加售后工单模块：创建、查询、留言、取消、管理员处理
- [x] 增加售后模块的基础测试

## 下一阶段

- [x] 把 SQLite 原始 SQL 迁移到 SQLAlchemy
- [x] 引入 Alembic 数据库迁移（已在 SQLite 验证）
- [x] 增加 DATABASE_URL，支持 PostgreSQL
- [x] 使用 Docker PostgreSQL 验证迁移
- [x] 增加 Redis 缓存与登录限流（无 Redis 时回退 fakeredis）
- [x] 增加 Celery 异步任务，处理订单超时取消（无 Redis 时 eager 模式）
- [x] 增加审计日志与幂等键
- [x] 使用 Docker 真 Redis + Celery worker 验证异步链路
- [ ] 完善 RBAC 角色与权限
- [x] 构建售后政策知识库与检索，返回引用来源
- [x] 增加检索评测脚本与案例集，计算 Hit@1 / Hit@K / MRR
- [x] 增加 PostgreSQL pgvector 向量表、HNSW 索引和向量检索路径
- [x] 使用真实 PostgreSQL 容器验证 pgvector 查询
- [x] 实现 LangGraph 售后 Agent 与 3 个只读业务工具
- [x] 增加结构化输出、停止条件与人工审批标记
- [x] 增加 AgentRun 运行记录与节点步骤
- [x] 增加多轮售后上下文与超长历史压缩
- [x] 接入 DeepSeek `deepseek-flash` 并验证模型驱动工具选择
- [x] 增加 BM25 + 向量 + RRF Hybrid Search
- [x] 增加 Agent 执行提案与管理员确认执行
- [x] 增加 X-Request-ID 全链路与 Agent 节点耗时/Trace 字段
- [x] 建立 30 条售后案例并完成纯基线/RAG/完整 Agent 三方案评测
- [x] 增加工具调用正确率、Token 与可配置成本估算
- [x] 增加 SSE 节点流与 Agent 演示页
- [x] 增加 Dockerfile、API/worker/PostgreSQL/Redis Compose 配置并通过 `docker compose config` 校验
- [x] 补充项目 README、运行方式和架构说明
- [x] 增加 GitHub Actions 测试工作流
- [x] 增加架构图和 2 分钟演示脚本
- [x] 完成 2 分钟实际录屏与自动录制脚本
- [x] 增加启动时数据库 schema 防错检查
- [x] 完成 Docker 实机启动与真实基础设施验收

## 运行

```bash
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
.venv/Scripts/python.exe run.py
```

使用 PostgreSQL：

```bash
docker compose up -d db
alembic upgrade head
$env:DATABASE_URL = "postgresql+psycopg://shopagent:shopagent@127.0.0.1:5432/shopagent"
.venv/Scripts/python.exe run.py
```
