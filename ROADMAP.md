# 开发路线

本项目基于 `wind5516/ecommerce-shop` 改动，目标是做成“商城后端 + 智能售后 Agent”的完整作品。

目标与完成标准见 [GOALS.md](./GOALS.md)，后续所有开发围绕这份目标展开。

## 当前进度

- [x] 克隆并跑通上游项目
- [x] 建立独立开发分支 `dev`
- [x] 增加售后工单模块：创建、查询、留言、取消、管理员处理
- [x] 增加售后模块的基础测试

## 下一阶段

- [ ] 把 SQLite 原始 SQL 迁移到 SQLAlchemy + PostgreSQL
- [ ] 引入 Alembic 数据库迁移
- [ ] 增加 Redis 缓存与会话存储
- [ ] 增加消息队列和异步任务，处理订单超时、退款等场景
- [ ] 完善 RBAC 与审计日志
- [ ] 构建售后政策 RAG 知识库
- [ ] 实现 LangGraph 售后 Agent 与业务工具调用
- [ ] 增加人工审批、流式响应、评测与 Trace
- [ ] 补充 Docker、CI 和演示文档

## 运行

```bash
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
.venv/Scripts/python.exe run.py
```
